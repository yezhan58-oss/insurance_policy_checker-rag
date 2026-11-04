import json

from src import tools
from src.approaches import REGISTRY
from src.approaches._common import NO_POLICY_TEXT
from src.eval.score import AGENTS, EXPLORATORY
from src.eval.traces import context_sections
from src.schema import Chunk
from tests.test_approaches import GOOD, SCENARIO, FakeLLM, FakeStore


def chunk(sid, type_):
    return Chunk(chunk_id=sid, section_id=sid, policy="fwd", title=sid, type=type_, page=1, text=f"FWD > {sid}\ntext")


class Store(FakeStore):
    def get_section(self, sid):
        return chunk(sid, "benefit") if sid == "fwd:travel_delay" else None

    def definitions(self, policy):
        return {"natural disaster": "fwd:definitions:natural_disaster", "we": "fwd:definitions:we"}


def act(action, input_=""):
    return json.dumps({"thought": "next", "action": action, "input": input_})


def setup(monkeypatch):
    monkeypatch.setattr(tools, "get_definition", lambda term, policy: (
        chunk("fwd:definitions:natural_disaster", "definition") if term == "natural disaster" else None))
    monkeypatch.setattr(tools, "get_exclusions", lambda sid: [chunk("fwd:general_exclusions:war", "exclusion")])


def test_registered_and_exploratory():
    assert "A3" in REGISTRY and "A3" in EXPLORATORY and "A3" not in AGENTS


def test_agent_chooses_lookups_and_answers_from_everything_it_saw(monkeypatch):
    setup(monkeypatch)
    llm, store = FakeLLM(act("search", "travel delay"), act("get_definition", "natural disaster"),
                         act("get_exclusions", "fwd:travel_delay"), act("answer"), GOOD), Store()
    out = REGISTRY["A3"](SCENARIO, llm, store)
    assert out.verdict == "covered" and out.error is None
    assert [s["step"] for s in out.steps] == ["search", "definitions", "exclusions", "stop", "decide", "answer"]
    assert store.queries == [("travel delay", "fwd", 5)]
    assert out.usage["model_calls"] == 5
    assert context_sections(out.steps) == {"fwd:travel_delay", "fwd:definitions:natural_disaster",
                                           "fwd:general_exclusions:war"}
    answer_prompt = llm.calls[-1][1].content
    assert "natural_disaster" in answer_prompt and "general_exclusions:war" in answer_prompt
    assert "Observation" in llm.calls[1][-1].content            # each tool result goes back to the agent


def test_unknown_term_and_bad_section_id_tell_the_agent_what_exists(monkeypatch):
    setup(monkeypatch)
    llm = FakeLLM(act("get_definition", "typhoon"), act("get_exclusions", "msig:section_9"), act("answer"), GOOD)
    out = REGISTRY["A3"](SCENARIO, llm, Store())
    first, second = llm.calls[1][-1].content, llm.calls[2][-1].content
    assert "natural disaster" in first and "we," not in first   # generic terms are left out of the list
    assert "not a section ID of this policy" in second
    assert out.steps[0]["fetched"] == [] and out.steps[1]["picked"] == []
    assert NO_POLICY_TEXT in llm.calls[-1][1].content           # nothing found: answers like B0


def test_lookup_limit_stops_the_agent(monkeypatch):
    setup(monkeypatch)
    llm = FakeLLM(*[act("search", f"query {i}") for i in range(8)], GOOD)
    out = REGISTRY["A3"](SCENARIO, llm, Store())
    assert [s["step"] for s in out.steps].count("search") == 8      # max_tool_calls = 8
    assert {"step": "stop", "reason": "limit"} in out.steps
    assert out.usage["model_calls"] == 9


def test_unusable_reply_answers_with_what_it_has(monkeypatch):
    setup(monkeypatch)
    out = REGISTRY["A3"](SCENARIO, FakeLLM(act("search", "delay"), "not json", GOOD), Store())
    assert [s["step"] for s in out.steps] == ["search", "stop", "decide", "answer"]
    assert out.steps[1]["reason"] == "unusable" and out.verdict == "covered"
