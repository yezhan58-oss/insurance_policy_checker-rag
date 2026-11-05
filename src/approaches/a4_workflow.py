"""A4: claims-workflow agent. A fixed LangGraph graph that reads the policy the way a claims assessor does:

    benefits     the LLM picks the benefit section(s) the claim falls under from the list of all benefit titles
                 (the policy's table of contents: embedding search alone missed e.g. FWD overseas medical
                 expenses for plain medical claims on dev)
    definitions  fetch the definitions of defined terms used in those sections and in the claim
    exclusions   fetch the exclusions that apply to those sections; the LLM keeps the ones relevant to the claim
                 (A4D, exploratory, tuned on dev only: the LLM also picks definitions from the list of defined
                 terms, since name matching misses terms the claim implies but never names, e.g. an earthquake is
                 a "serious public event")
    decide       the shared answer call (same base prompt as every setup) over everything gathered

Each node appends to `steps`. If a pick call returns unusable output, the node falls back to a fixed rule
(top benefit search hit / all exclusions) and logs that, so one bad call never stops the run.
"""
import time
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from openai import LengthFinishReasonError
from pydantic import BaseModel, ValidationError

from src import tools
from src.approaches._common import POLICY_NAMES, answer, approach_config, call_llm, format_chunks, new_usage
from src.schema import Chunk, Scenario, VerdictOutput

APPROACH_ID = "A4"


class Pick(BaseModel):
    section_ids: list[str]


PICK_FORMAT = {"type": "json_schema", "json_schema": {"name": "pick", "schema": Pick.model_json_schema()}}

BENEFIT_PROMPT = """You help a travel insurance claims assessor. Below is a claim and a list of benefit sections \
from the policy. Pick the benefit section(s) the claim would be made under: usually 1, at most {n}. \
Answer in JSON as {{"section_ids": [...]}}, copying IDs exactly from the list."""

DEFINITION_PROMPT = """You help a travel insurance claims assessor. Below is a claim and the list of defined terms in the policy. Pick every defined term whose definition could decide this claim, including terms the claim describes without naming (e.g. an event, a person or a place that a definition covers). Usually 0 to 3. Answer in JSON as {"section_ids": [...]}, copying IDs exactly from the list."""

EXCLUSION_PROMPT = """You help a travel insurance claims assessor. Below is a claim and the exclusions that apply to \
the benefit it falls under. Pick every exclusion that could affect this claim, given the facts stated. If none \
could, return an empty list. Answer in JSON as {"section_ids": [...]}, copying IDs exactly from the list."""


class State(TypedDict):
    scenario: Scenario
    benefits: list[Chunk]
    definitions: list[Chunk]
    exclusions: list[Chunk]
    steps: list
    usage: dict
    start: float
    output: VerdictOutput | None


def _pick(llm, system: str, scenario: Scenario, options: list[Chunk], usage: dict,
          titles_only: bool = False) -> list[str] | None:
    """LLM picks section IDs from `options`. None if the reply is unusable; IDs not in `options` are dropped."""
    if titles_only:
        listing = "\n".join(f"[{c.section_id}] {c.title}" for c in options)
    else:
        listing = "\n\n".join(f"[{c.section_id}] {c.title}\n{c.text.split(chr(10), 1)[-1]}" for c in options)
    user = (f"Policy: {POLICY_NAMES.get(scenario.policy, scenario.policy)}\n\nClaim: {scenario.scenario}\n\n"
            f"Sections:\n\n{listing}")
    try:
        msg = call_llm(llm, [SystemMessage(system), HumanMessage(user)], usage, response_format=PICK_FORMAT)
        ids = Pick.model_validate_json(msg.content).section_ids
    except (ValidationError, ValueError, TypeError, LengthFinishReasonError):   # length: reply ran into max_tokens
        return None
    valid = {c.section_id for c in options}
    return [i for i in dict.fromkeys(ids) if i in valid]


def build_graph(llm, store, approach_id: str = APPROACH_ID):
    cfg = approach_config(approach_id)

    def benefits(state: State) -> dict:
        s = state["scenario"]
        options = store.list_sections(s.policy, "benefit")
        picked = _pick(llm, BENEFIT_PROMPT.format(n=cfg["max_benefits"]), s, options, state["usage"], titles_only=True)
        fallback = not picked
        if fallback:
            hits = store.search(s.scenario, s.policy, k=cfg["fallback_k"])
            picked = [h.section_id for h in hits if h.type == "benefit"][:1]
        ids = picked[:cfg["max_benefits"]]
        state["steps"].append({"step": "benefits", "picked": ids, "fallback": fallback})
        return {"benefits": [c for c in options if c.section_id in ids]}

    def definitions(state: State) -> dict:
        s = state["scenario"]
        text = "\n".join([s.scenario, *(c.text for c in state["benefits"])])
        matched = tools.find_defined_terms(text, s.policy)
        step = {"step": "definitions"}
        if cfg.get("pick_definitions"):
            options = [c for c in store.list_sections(s.policy, "definition")
                       if c.title.lower() not in tools.GENERIC_TERMS]
            picked = _pick(llm, DEFINITION_PROMPT, s, options, state["usage"], titles_only=True)
            step |= {"picked": picked or [], "matched": matched, "fallback": picked is None}
            matched = list(dict.fromkeys((picked or []) + matched))   # picks first so the cap keeps them
        ids = matched[:cfg["max_definitions"]]
        state["steps"].append(step | {"fetched": ids})
        return {"definitions": [c for c in map(store.get_section, ids) if c]}

    def exclusions(state: State) -> dict:
        s = state["scenario"]
        options = list({c.section_id: c for b in state["benefits"] for c in tools.get_exclusions(b.section_id)}.values())
        picked = _pick(llm, EXCLUSION_PROMPT, s, options, state["usage"]) if options else []
        fallback = picked is None
        ids = [c.section_id for c in options] if fallback else picked
        state["steps"].append({"step": "exclusions", "candidates": [c.section_id for c in options], "picked": ids,
                               "fallback": fallback})
        return {"exclusions": [c for c in options if c.section_id in ids]}

    def decide(state: State) -> dict:
        chunks = state["benefits"] + state["definitions"] + state["exclusions"]
        return {"output": answer(llm, state["scenario"], format_chunks(chunks), steps=state["steps"],
                                 usage=state["usage"], start=state["start"])}

    g = StateGraph(State)
    nodes = (("benefits", benefits), ("definitions", definitions), ("exclusions", exclusions), ("decide", decide))
    for name, fn in nodes:
        g.add_node(name, fn)
    g.add_edge(START, "benefits")
    g.add_edge("benefits", "definitions")
    g.add_edge("definitions", "exclusions")
    g.add_edge("exclusions", "decide")
    g.add_edge("decide", END)
    return g.compile()


def run(scenario: Scenario, llm, store, approach_id: str = APPROACH_ID) -> VerdictOutput:
    state = build_graph(llm, store, approach_id).invoke({"scenario": scenario, "benefits": [], "definitions": [], "exclusions": [],
                                            "steps": [], "usage": new_usage(), "start": time.perf_counter(),
                                            "output": None})
    return state["output"]
