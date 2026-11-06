"""A3: ReAct tool agent (Yao et al. 2023). Exploratory: added 4 Nov, after the test results, so it is outside the
Holm family and the decision rule (src/eval/score.py EXPLORATORY).

The model chooses its own lookups. At each step it writes one JSON action, {"thought", "action", "input"}:

    search          top_k chunks of the policy for a query
    get_definition  the definition section of one defined term (an unknown term returns the list of defined terms)
    get_exclusions  the exclusion sections that apply to one benefit section ID
    answer          stop looking

The tools are the ones A4 uses (src/tools.py), so A3 and A4 can reach the same evidence; the difference is that A4
runs them in a fixed order and A3 decides for itself. Actions are plain JSON rather than native tool calls, so both
models run it the same way with no server change. After at most max_tool_calls lookups, or on an unusable reply,
the agent stops. The answer is the shared answer call (same base prompt as every setup) over every section the
agent looked at; the decide step lists them under "context" (src/eval/traces.py reads it).

Steps are named after A4's (search / definitions / exclusions) so the trace evaluation scores them the same way.
"""
import time
from typing import Literal, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from openai import LengthFinishReasonError
from pydantic import BaseModel, ValidationError

from src import tools
from src.approaches._common import POLICY_NAMES, answer, approach_config, call_llm, format_chunks, new_usage
from src.schema import Chunk, Scenario, VerdictOutput

APPROACH_ID = "A3"

# The prompt lists the tools, not an order to use them in: whether the agent thinks of definitions and exclusions
# on its own is what A3 tests (A4 hard-codes that order).
REACT_PROMPT = """You help a travel insurance claims assessor find the policy text that decides a claim. Work in \
steps. At each step think briefly, then choose one action:
- search: search the policy wording. Input: a query, best in the policy's own words. Returns the {top_k} best \
matching extracts with their section IDs.
- get_definition: the policy's definition of a defined term. Input: the term, e.g. "period of insurance".
- get_exclusions: the exclusions that apply to a benefit section. Input: the benefit's section ID as shown in an \
extract, e.g. "fwd:travel_delay".
- answer: stop looking. Input: "". Another step will then decide the claim from everything you have looked at.
You can make at most {max_calls} lookups. Answer in JSON as {{"thought": "...", "action": "...", "input": "..."}}."""


class Action(BaseModel):
    thought: str
    action: Literal["search", "get_definition", "get_exclusions", "answer"]
    input: str


ACTION_FORMAT = {"type": "json_schema", "json_schema": {"name": "action", "schema": Action.model_json_schema()}}
STEP_NAME = {"search": "search", "get_definition": "definitions", "get_exclusions": "exclusions"}


class State(TypedDict):
    scenario: Scenario
    messages: list             # the conversation so far: prompt, claim, then action / observation pairs
    seen: list[Chunk]          # every chunk the agent looked at, in order, no repeats
    calls: int                 # lookups done so far
    stop: str | None           # why the loop ended: "answer", "limit" or "unusable"
    steps: list                # the trace
    usage: dict                # model calls, tokens, latency (filled by call_llm / answer)
    start: float
    output: VerdictOutput | None


def build_graph(llm, store):
    cfg = approach_config(APPROACH_ID)        # {"max_tool_calls": 8, "top_k": 5}

    def lookup(action: Action, policy: str) -> tuple[list[Chunk], str, dict]:
        """Run one tool: the chunks it returned, the observation text the agent sees, and the step's trace fields."""
        query = action.input.strip()
        if action.action == "search":
            hits = store.search(query, policy, k=cfg["top_k"])
            return hits, format_chunks(hits) or "No results.", {
                "query": query, "hits": [{"chunk_id": h.chunk_id, "section_id": h.section_id, "score": h.score}
                                         for h in hits]}
        if action.action == "get_definition":
            sec = tools.get_definition(query, policy)
            if sec:
                return [sec], format_chunks([sec]), {"term": query, "fetched": [sec.section_id]}
            terms = ", ".join(sorted(t for t in store.definitions(policy) if t not in tools.GENERIC_TERMS))
            return [], f'"{query}" is not a defined term. Defined terms in this policy: {terms}.', {
                "term": query, "fetched": []}
        if store.get_section(query) is None or query.split(":", 1)[0] != policy:
            return [], f'"{query}" is not a section ID of this policy. Use an ID shown in an extract.', {
                "benefit": query, "picked": []}
        found = tools.get_exclusions(query)
        return found, format_chunks(found) or "No exclusions apply to this section.", {
            "benefit": query, "picked": [c.section_id for c in found]}

    def act(state: State) -> dict:
        if state["calls"] >= cfg["max_tool_calls"]:
            state["steps"].append({"step": "stop", "reason": "limit"})
            return {"stop": "limit"}
        try:
            msg = call_llm(llm, state["messages"], state["usage"], response_format=ACTION_FORMAT)
            action = Action.model_validate_json(msg.content)
        except (ValidationError, ValueError, TypeError, LengthFinishReasonError):   # unusable reply: answer now
            state["steps"].append({"step": "stop", "reason": "unusable"})
            return {"stop": "unusable"}
        if action.action == "answer":
            state["steps"].append({"step": "stop", "reason": "answer", "thought": action.thought})
            return {"stop": "answer"}
        chunks, observation, fields = lookup(action, state["scenario"].policy)
        state["steps"].append({"step": STEP_NAME[action.action], "thought": action.thought, **fields})
        seen_ids = {c.chunk_id for c in state["seen"]}
        return {"messages": state["messages"] + [AIMessage(action.model_dump_json()),
                                                 HumanMessage(f"Observation:\n\n{observation}")],
                "seen": state["seen"] + [c for c in chunks if c.chunk_id not in seen_ids],
                "calls": state["calls"] + 1}

    def route(state: State) -> str:
        return "decide" if state["stop"] else "act"

    def decide(state: State) -> dict:
        chunks = state["seen"]                      # may be empty: then the answer sees no policy text, like B0
        state["steps"].append({"step": "decide", "context": list(dict.fromkeys(c.section_id for c in chunks))})
        return {"output": answer(llm, state["scenario"], format_chunks(chunks), steps=state["steps"],
                                 usage=state["usage"], start=state["start"])}

    g = StateGraph(State)
    g.add_node("act", act)
    g.add_node("decide", decide)
    g.add_edge(START, "act")
    g.add_conditional_edges("act", route, {"act": "act", "decide": "decide"})
    g.add_edge("decide", END)
    return g.compile()


def run(scenario: Scenario, llm, store) -> VerdictOutput:
    cfg = approach_config(APPROACH_ID)
    system = REACT_PROMPT.format(top_k=cfg["top_k"], max_calls=cfg["max_tool_calls"])
    claim = f"Policy: {POLICY_NAMES.get(scenario.policy, scenario.policy)}\n\nClaim: {scenario.scenario}"
    state = build_graph(llm, store).invoke(
        {"scenario": scenario, "messages": [SystemMessage(system), HumanMessage(claim)], "seen": [], "calls": 0,
         "stop": None, "steps": [], "usage": new_usage(), "start": time.perf_counter(), "output": None},
        {"recursion_limit": 2 * cfg["max_tool_calls"] + 10})
    return state["output"]
