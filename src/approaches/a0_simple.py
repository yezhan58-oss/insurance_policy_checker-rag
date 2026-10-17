"""A0: simple RAG. One search with the scenario text (top_k chunks from that policy), then answer."""
import time

from src.approaches._common import answer, approach_config, format_chunks, new_usage
from src.schema import Scenario, VerdictOutput

APPROACH_ID = "A0"


def run(scenario: Scenario, llm, store) -> VerdictOutput:
    start = time.perf_counter()
    top_k = approach_config(APPROACH_ID)["top_k"]
    hits = store.search(scenario.scenario, scenario.policy, k=top_k)
    steps = [{"step": "search", "query": scenario.scenario, "top_k": top_k,
              "hits": [{"chunk_id": h.chunk_id, "section_id": h.section_id, "score": h.score} for h in hits]}]
    return answer(llm, scenario, format_chunks(hits), steps=steps, usage=new_usage(), start=start)
