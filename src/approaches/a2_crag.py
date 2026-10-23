"""A2: Corrective RAG (CRAG-style). Adapted from Yan et al. 2024: an LLM grades the retrieved chunks instead of
their fine-tuned T5 evaluator, and a rewritten query searches the policy again instead of a web search (the policy
is a closed corpus). A LangGraph graph with one loop:

    search   top_k chunks for the current query
    grade    the LLM grades each chunk relevant / irrelevant to the claim
    rewrite  fewer than min_relevant relevant chunks and rewrites left: the LLM rewrites the query, back to search
             (unless it repeats an earlier query, which would return the same chunks: then decide)
    decide   the shared answer call (same base prompt as every setup) over the relevant chunks only

Each node appends to `steps`; the decide step lists the section IDs the answer saw under "context"
(src/eval/traces.py reads it).
"""
import time
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from openai import LengthFinishReasonError
from pydantic import BaseModel, ValidationError

from src.approaches._common import POLICY_NAMES, answer, approach_config, call_llm, format_chunks, new_usage
from src.schema import Chunk, Scenario, VerdictOutput

APPROACH_ID = "A2"

# One call grades all chunks of a search (the paper grades each chunk separately): faster for the user.
GRADE_PROMPT = """You help a travel insurance claims assessor. Below is a claim and numbered extracts from the \
policy. An extract is relevant if it could help decide whether this claim is paid: the benefit the claim falls \
under, or a condition, limit, definition or exclusion that applies to it. An extract that would stop the claim from \
being paid is relevant too. Answer in JSON as {"relevant": [...]}, listing the numbers of the relevant extracts \
(an empty list if none are)."""


class Grades(BaseModel):
    relevant: list[int]


GRADE_FORMAT = {"type": "json_schema", "json_schema": {"name": "grades", "schema": Grades.model_json_schema()}}

REWRITE_PROMPT = """You help a travel insurance claims assessor search a policy wording. The searches below did not \
find enough relevant policy text for the claim. Write one new search query in the policy's own wording: name the \
kind of cover or event (for example "baggage theft" or "trip cancellation due to illness"), not the claimant's \
story. Do not repeat an earlier query. Answer in JSON as {"query": "..."}."""


class Rewrite(BaseModel):
    query: str


REWRITE_FORMAT = {"type": "json_schema", "json_schema": {"name": "rewrite", "schema": Rewrite.model_json_schema()}}


class State(TypedDict):
    scenario: Scenario
    query: str                 # starts as the claim text; replaced by each rewrite
    hits: list[Chunk]          # results of the latest search
    relevant: list[Chunk]      # chunks graded relevant so far, across all searches
    rewrites: int              # rewrites done so far
    steps: list                # the trace
    usage: dict                # model calls, tokens, latency (filled by call_llm / answer)
    start: float
    output: VerdictOutput | None


def build_graph(llm, store):
    cfg = approach_config(APPROACH_ID)        # {"top_k": 5, "min_relevant": 2, "max_rewrites": 2}

    def search(state: State) -> dict:
        query, policy = state["query"], state["scenario"].policy
        hits = store.search(query, policy, k=cfg["top_k"])
        state["steps"].append({"step": "search", "query": query,
                               "hits": [{"chunk_id": h.chunk_id, "section_id": h.section_id, "score": h.score}
                                        for h in hits]})
        return {"hits": hits}

    def grade(state: State) -> dict:
        s, hits = state["scenario"], state["hits"]
        extracts = "\n\n".join(f"[{i}] {h.text}" for i, h in enumerate(hits, 1))
        user = f"Policy: {POLICY_NAMES.get(s.policy, s.policy)}\n\nClaim: {s.scenario}\n\nExtracts:\n\n{extracts}"
        try:
            msg = call_llm(llm, [SystemMessage(GRADE_PROMPT), HumanMessage(user)], state["usage"],
                           response_format=GRADE_FORMAT)
            numbers = set(Grades.model_validate_json(msg.content).relevant)
            kept, fallback = [h for i, h in enumerate(hits, 1) if i in numbers], False
        except (ValidationError, ValueError, TypeError, LengthFinishReasonError):   # unusable reply: keep every hit
            kept, fallback = hits, True
        kept_ids, seen = {h.chunk_id for h in kept}, {c.chunk_id for c in state["relevant"]}
        state["steps"].append({"step": "grade", "picked": [h.section_id for h in kept],
                               "dropped": [h.section_id for h in hits if h.chunk_id not in kept_ids],
                               "fallback": fallback})
        return {"relevant": state["relevant"] + [h for h in kept if h.chunk_id not in seen]}

    def route(state: State) -> str:
        """The loop decision: search again with a rewritten query, or answer from what we have."""
        if len(state["relevant"]) >= cfg["min_relevant"] or state["rewrites"] >= cfg["max_rewrites"]:
            return "decide"
        return "rewrite"

    def rewrite(state: State) -> dict:
        s = state["scenario"]
        tried = [st["query"] for st in state["steps"] if st["step"] == "search"]
        user = (f"Policy: {POLICY_NAMES.get(s.policy, s.policy)}\n\nClaim: {s.scenario}\n\nEarlier queries:\n"
                + "\n".join(f"- {q}" for q in tried))
        try:
            msg = call_llm(llm, [SystemMessage(REWRITE_PROMPT), HumanMessage(user)], state["usage"],
                           response_format=REWRITE_FORMAT)
            query, fallback = Rewrite.model_validate_json(msg.content).query.strip() or state["query"], False
        except (ValidationError, ValueError, TypeError, LengthFinishReasonError):   # unusable reply: same query
            query, fallback = state["query"], True
        repeated = query.casefold() in {q.casefold() for q in tried}   # same query = same hits: stop looping
        state["steps"].append({"step": "rewrite", "query": query, "fallback": fallback, "repeated": repeated})
        return {"query": query, "rewrites": state["rewrites"] + 1}

    def after_rewrite(state: State) -> str:
        return "decide" if state["steps"][-1]["repeated"] else "search"

    def decide(state: State) -> dict:
        chunks = state["relevant"]                  # may be empty: then the answer sees no policy text, like B0
        state["steps"].append({"step": "decide", "context": list(dict.fromkeys(c.section_id for c in chunks))})
        return {"output": answer(llm, state["scenario"], format_chunks(chunks), steps=state["steps"],
                                 usage=state["usage"], start=state["start"])}

    g = StateGraph(State)
    for name, fn in (("search", search), ("grade", grade), ("rewrite", rewrite), ("decide", decide)):
        g.add_node(name, fn)
    g.add_edge(START, "search")
    g.add_edge("search", "grade")
    g.add_conditional_edges("grade", route, {"rewrite": "rewrite", "decide": "decide"})
    g.add_conditional_edges("rewrite", after_rewrite, {"search": "search", "decide": "decide"})
    g.add_edge("decide", END)
    return g.compile()


def run(scenario: Scenario, llm, store) -> VerdictOutput:
    state = build_graph(llm, store).invoke({"scenario": scenario, "query": scenario.scenario, "hits": [],
                                            "relevant": [], "rewrites": 0, "steps": [], "usage": new_usage(),
                                            "start": time.perf_counter(), "output": None})
    return state["output"]
