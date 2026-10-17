import json

import pytest

from src.approaches import REGISTRY
from src.approaches import a4_workflow
from src.schema import Chunk, Scenario
from tests.test_approaches import GOOD, FakeLLM


def chunk(sid, type_="benefit", title=None):
    return Chunk(chunk_id=sid, section_id=sid, policy="fwd", title=title or sid, type=type_, page=1,
                 text=f"FWD > {sid}\ntext of {sid}")


SECTIONS = {c.section_id: c for c in [
    chunk("fwd:travel_delay"), chunk("fwd:trip_diversion"), chunk("fwd:definitions:x", "definition"),
    chunk("fwd:definitions:typo", "definition"), chunk("fwd:general_exclusions:a", "exclusion"),
    chunk("fwd:general_exclusions:b", "exclusion")]}


class FakeStore:
    def search(self, query, policy, k=5):
        return [SECTIONS["fwd:travel_delay"], SECTIONS["fwd:definitions:x"], SECTIONS["fwd:trip_diversion"]]

    def get_section(self, sid):
        return SECTIONS.get(sid)

    def list_sections(self, policy, type=None):
        return [c for c in SECTIONS.values() if type is None or c.type == type]


@pytest.fixture(autouse=True)
def fake_tools(monkeypatch):
    monkeypatch.setattr(a4_workflow.tools, "find_defined_terms", lambda text, policy: ["fwd:definitions:x"])
    monkeypatch.setattr(a4_workflow.tools, "get_exclusions",
                        lambda sid: [SECTIONS["fwd:general_exclusions:a"], SECTIONS["fwd:general_exclusions:b"]])


SCENARIO = Scenario(id="t", policy="fwd", category="single_section", gold_verdict="covered",
                    scenario="My flight was delayed 7 hours by a typhoon. Can I claim?")


def pick(*ids):
    return json.dumps({"section_ids": list(ids)})


def test_registered():
    assert "A4" in REGISTRY


def test_full_workflow_passes_only_picked_sections_to_the_answer():
    llm = FakeLLM(pick("fwd:travel_delay", "fwd:not_a_candidate"), pick("fwd:general_exclusions:b"), GOOD)
    out = REGISTRY["A4"](SCENARIO, llm, FakeStore())
    assert [s["step"] for s in out.steps] == ["benefits", "definitions", "exclusions", "answer"]
    assert out.steps[0]["picked"] == ["fwd:travel_delay"]                             # unknown ID dropped
    toc = llm.calls[0][1].content                                                     # titles only, benefits only
    assert "[fwd:trip_diversion] fwd:trip_diversion" in toc and "text of" not in toc and "definitions" not in toc
    final_user = llm.calls[2][1].content
    for sid in ("fwd:travel_delay", "fwd:definitions:x", "fwd:general_exclusions:b"):
        assert f"[Section ID: {sid}]" in final_user
    assert "fwd:general_exclusions:a" not in final_user and "fwd:trip_diversion" not in final_user
    assert out.verdict == "covered" and out.usage["model_calls"] == 3


def test_bad_pick_replies_fall_back():
    llm = FakeLLM("garbage", "garbage", GOOD)
    out = REGISTRY["A4"](SCENARIO, llm, FakeStore())
    benefits, _, exclusions, _ = out.steps
    assert benefits["fallback"] and benefits["picked"] == ["fwd:travel_delay"]      # top benefit search hit
    assert exclusions["fallback"] and exclusions["picked"] == ["fwd:general_exclusions:a", "fwd:general_exclusions:b"]
    assert out.error is None


def test_empty_exclusion_pick_is_respected():
    llm = FakeLLM(pick("fwd:travel_delay"), pick(), GOOD)
    out = REGISTRY["A4"](SCENARIO, llm, FakeStore())
    assert out.steps[2]["picked"] == [] and not out.steps[2]["fallback"]
    assert "general_exclusions" not in llm.calls[2][1].content
