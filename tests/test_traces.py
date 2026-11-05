import math

import pytest

from src.eval import traces

TYPES = {"fwd:travel_delay": "benefit", "fwd:definitions:trip": "definition",
         "fwd:general_exclusions:unlawful_acts": "exclusion", "fwd:missed_connections": "benefit"}
GOLD = {"gold_verdict": "not_covered", "gold_sections": ["fwd:travel_delay", "fwd:general_exclusions:unlawful_acts"]}


@pytest.fixture(autouse=True)
def fake_types(monkeypatch):
    monkeypatch.setattr(traces, "section_type", TYPES.get)


def row(approach, steps, verdict="not_covered", error=None):
    return {"scenario_id": "fwd-009", "approach": approach,
            "output": {"verdict": verdict, "error": error, "steps": steps,
                       "usage": {"model_calls": 3, "prompt_tokens": 900, "completion_tokens": 100, "latency_s": 4.0}}}


A4_STEPS = [{"step": "benefits", "picked": ["fwd:travel_delay", "fwd:missed_connections"], "fallback": False},
            {"step": "definitions", "fetched": ["fwd:definitions:trip"]},
            {"step": "exclusions", "candidates": ["fwd:general_exclusions:unlawful_acts"], "picked": [],
             "fallback": False},
            {"step": "answer", "attempt": 1, "verdict": "covered", "cited_sections": ["fwd:travel_delay"]}]


def test_wrong_answer_without_gold_exclusion_is_missing_evidence():
    t = traces.trace_row(row("A4", A4_STEPS, verdict="covered"), GOLD)
    assert t["failure"] == "missing_evidence" and t["missing"] == ["fwd:general_exclusions:unlawful_acts"]
    assert t["evidence_recall"] == 0.5 and t["context_size"] == 3 and t["unneeded_share"] == pytest.approx(2 / 3)
    assert t["tokens"] == 1000


def test_steps_are_scored_against_gold_of_their_type():
    s = {x["step"]: x for x in traces.step_rows(row("A4", A4_STEPS), GOLD)}
    assert set(s) == {"benefits", "definitions", "exclusions"}                  # the answer step selects nothing
    assert s["benefits"]["recall"] == 1 and s["benefits"]["precision"] == 0.5
    assert s["definitions"]["over_pick"] == 1.0 and math.isnan(s["definitions"]["recall"])   # no gold definition
    assert s["exclusions"]["recall"] == 0 and math.isnan(s["exclusions"]["precision"])


def test_explicit_context_wins_and_search_hits_are_used_otherwise():
    a2 = [{"step": "search", "hits": [{"section_id": "fwd:travel_delay"}, {"section_id": "fwd:missed_connections"}]},
          {"step": "grade", "context": ["fwd:travel_delay", "fwd:general_exclusions:unlawful_acts"]}]
    assert traces.trace_row(row("A2", a2), GOLD)["failure"] is None
    assert traces.context_sections(a2) == set(GOLD["gold_sections"])
    a0 = [{"step": "search", "hits": [{"section_id": "fwd:travel_delay"}, {"section_id": "fwd:travel_delay"}]}]
    t = traces.trace_row(row("A0", a0, verdict="covered"), GOLD)
    assert t["context_size"] == 1 and t["failure"] == "missing_evidence"
    assert traces.trace_row(row("B0", [], error="parse_error"), GOLD)["failure"] == "error"


def test_right_answers_are_split_by_whether_the_evidence_reached_the_model():
    full = [{"step": "search", "hits": [{"section_id": i} for i in GOLD["gold_sections"]]}]
    part = [{"step": "search", "hits": [{"section_id": "fwd:travel_delay"}]}]
    sound = traces.trace_row(row("A0", full), GOLD, faithfulness="yes")
    lucky = traces.trace_row(row("A0", part), GOLD, faithfulness="yes")
    assert sound["correct"] and sound["outcome"] == "sound" and sound["grounded"] is True
    assert lucky["correct"] and lucky["failure"] is None and lucky["outcome"] == "right_without_evidence"
    assert lucky["grounded"] is False                                   # faithful text, but no working process
    assert traces.trace_row(row("A0", full), GOLD, faithfulness="partly")["grounded"] is False
    assert traces.trace_row(row("A0", full), GOLD)["grounded"] is None  # not judged
    assert traces.trace_row(row("B0", []), GOLD)["outcome"] == "right_without_evidence"   # B0 never sees policy text
    assert traces.trace_row(row("A0", full, error="parse_error"), GOLD)["grounded"] is False   # judge skips errors


def test_summary_counts_process_outcomes_and_waits_for_a_full_judge_run():
    full = [{"step": "search", "hits": [{"section_id": i} for i in GOLD["gold_sections"]]}]
    part = [{"step": "search", "hits": [{"section_id": "fwd:travel_delay"}]}]
    ts = [traces.trace_row(row("A0", full), GOLD, "yes"), traces.trace_row(row("A0", part), GOLD, "yes"),
          traces.trace_row(row("A0", full, verdict="covered"), GOLD, "no")]
    s = traces.summarise(ts, [])["A0"]
    assert (s["sound"], s["right_without_evidence"], s["had_evidence"]) == (1, 1, 1)
    assert s["sound_rate"] == pytest.approx(1 / 3) and s["grounded_rate"] == pytest.approx(1 / 3)
    ts.append(traces.trace_row(row("A0", full, error="parse_error"), GOLD))   # unjudged error row: still complete
    assert traces.summarise(ts, [])["A0"]["grounded_rate"] == pytest.approx(1 / 4)
    ts[2]["grounded"] = None                                            # one row not judged yet
    assert math.isnan(traces.summarise(ts, [])["A0"]["grounded_rate"])


def test_citations_are_checked_against_the_policy_and_the_context():
    full = [{"step": "search", "hits": [{"section_id": "fwd:travel_delay"}]}]
    r = row("A0", full)
    r["output"]["cited_sections"] = ["fwd:travel_delay",                     # real and in context
                                     "fwd:general_exclusions:unlawful_acts",  # real, never shown to the model
                                     "fwd:made_up_section",                   # does not exist
                                     "msig:section_25", "fwd:travel_delay"]   # other policy; repeat counted once
    t = traces.trace_row(r, GOLD)
    assert (t["cited"], t["cited_invalid"], t["cited_unseen"]) == (4, 2, 1)
    none = row("B0", [])
    none["output"]["cited_sections"] = []
    s = traces.summarise([t, traces.trace_row(none, GOLD)], [])
    assert s["A0"]["citation_valid_rate"] == 0.5 and s["A0"]["citation_in_context_rate"] == 0.25
    assert s["A0"]["rows_bad_cite"] == 1 and s["B0"]["rows_no_cite"] == 1
    assert math.isnan(s["B0"]["citation_valid_rate"])                      # nothing cited: no rate


def test_a4d_definitions_step_uses_fetched_not_only_picks():
    step = {"step": "definitions", "picked": ["fwd:definitions:b"], "matched": ["fwd:definitions:a"],
            "fallback": False, "fetched": ["fwd:definitions:a", "fwd:definitions:b"]}
    assert traces.selected(step) == ["fwd:definitions:a", "fwd:definitions:b"]
