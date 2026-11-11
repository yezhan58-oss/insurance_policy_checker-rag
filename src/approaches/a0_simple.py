"""A0: simple RAG. One search with the scenario text (top_k chunks from that policy), then answer."""
import time

from src.approaches._common import answer, approach_config, format_chunks, new_usage
from src.schema import Scenario, VerdictOutput

APPROACH_ID = "A0"


def run(scenario: Scenario, llm, store, approach_id: str = APPROACH_ID) -> VerdictOutput:
    start = time.perf_counter()
    top_k = approach_config(approach_id)["top_k"]   # A0K10 reuses this code with its own top_k
    hits = store.search(scenario.scenario, scenario.policy, k=top_k)
    steps = [{"step": "search", "query": scenario.scenario, "top_k": top_k,
              "hits": [{"chunk_id": h.chunk_id, "section_id": h.section_id, "score": h.score} for h in hits]}]
    return answer(llm, scenario, format_chunks(hits), steps=steps, usage=new_usage(), start=start)
