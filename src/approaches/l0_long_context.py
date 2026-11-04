"""L0: long-context baseline, no retrieval. The whole policy (every section, in document order, each with its section
ID) goes into the prompt with the same base prompt and answer call as every setup, so the model reads all of it.

Topic 8 of the course: long-context prompting can beat RAG on a small, static corpus, so measure it before building
retrieval. Exploratory: added on 30 Oct after the comparisons were pre-registered, so src/eval/score.py reports it
next to the core setups but never lets it decide the winner.

Needs a server with a longer context than the core runs: about 28k tokens for FWD and 45k for MSIG (measured on test)
(MAX_LEN=131072 in scripts/run_eval.sbatch).
"""
import time

from src.approaches._common import answer, format_chunks, new_usage
from src.schema import Scenario, VerdictOutput

APPROACH_ID = "L0"


def run(scenario: Scenario, llm, store) -> VerdictOutput:
    start = time.perf_counter()
    sections = store.list_sections(scenario.policy)
    steps = [{"step": "long_context", "context": [s.section_id for s in sections]}]
    return answer(llm, scenario, format_chunks(sections), steps=steps, usage=new_usage(), start=start)
