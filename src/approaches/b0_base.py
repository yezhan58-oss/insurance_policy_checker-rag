"""B0: base LLM, no retrieval. Same prompt as every setup but no policy text: the floor."""
import time

from src.approaches._common import answer, new_usage
from src.schema import Scenario, VerdictOutput

APPROACH_ID = "B0"


def run(scenario: Scenario, llm, store) -> VerdictOutput:
    start = time.perf_counter()
    return answer(llm, scenario, None, steps=[], usage=new_usage(), start=start)
