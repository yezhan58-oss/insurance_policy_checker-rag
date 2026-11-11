"""A0K10: A0 with top_k=10 instead of 5 (exploratory, added 11 Nov after the test results; not in run.yaml's list,
so it never enters the decision rule). Answers "would simple RAG do better with more passages?". See a0_simple.py."""
from src.approaches import a0_simple
from src.schema import Scenario, VerdictOutput

APPROACH_ID = "A0K10"


def run(scenario: Scenario, llm, store) -> VerdictOutput:
    return a0_simple.run(scenario, llm, store, APPROACH_ID)
