"""A4D: A4 with an LLM pick of definitions from the list of defined terms (exploratory, added 5 Nov after
pre-registration; not in run.yaml's list, so it never enters the decision rule). See a4_workflow.py."""
from src.approaches import a4_workflow
from src.schema import Scenario, VerdictOutput

APPROACH_ID = "A4D"


def run(scenario: Scenario, llm, store) -> VerdictOutput:
    return a4_workflow.run(scenario, llm, store, APPROACH_ID)
