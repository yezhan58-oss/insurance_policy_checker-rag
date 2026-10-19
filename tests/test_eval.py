import json

import numpy as np
import pytest

from src.eval import run as run_mod
from src.eval.score import decide, mcnemar_p, per_row, score
from src.schema import Scenario, VerdictOutput

SCENARIOS = [Scenario(id=f"s{i}", policy="fwd", category="single_section", gold_verdict="covered",
                      gold_sections=["fwd:travel_delay"], scenario=f"question {i}") for i in range(3)]


def fake_approach(verdict="covered", fail_on=None):
    def run(scenario, llm, store):
        if scenario.id == fail_on:
            raise ConnectionError("server down")
        return VerdictOutput(verdict=verdict, cited_sections=["fwd:travel_delay"], explanation="x",
                             usage={"latency_s": 1.0, "model_calls": 1})
    return run


def test_run_split_writes_rows_and_resumes(tmp_path):
    out = tmp_path / "raw.jsonl"
    first = run_mod.run_split(SCENARIOS, {"B0": fake_approach(fail_on="s1")}, None, None, "m", "dev", out, "abc",
                              log=lambda *_: None)
    assert first == {"done": 2, "skipped": 0, "failed": 1}             # the failed one is not written
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert {r["scenario_id"] for r in rows} == {"s0", "s2"}
    assert rows[0]["output"]["verdict"] == "covered" and rows[0]["commit"] == "abc"
    second = run_mod.run_split(SCENARIOS, {"B0": fake_approach()}, None, None, "m", "dev", out, "abc",
                               log=lambda *_: None)
    assert second == {"done": 1, "skipped": 2, "failed": 0}            # only the failed one is retried


def test_run_split_records_non_transient_errors_as_wrong(tmp_path):
    def broken(scenario, llm, store):
        raise ValueError("model output hit the length limit")
    out = tmp_path / "raw.jsonl"
    counts = run_mod.run_split(SCENARIOS[:1], {"A4": broken}, None, None, "m", "dev", out, "abc", log=lambda *_: None)
    assert counts == {"done": 1, "skipped": 0, "failed": 0}            # recorded, so a rerun does not loop on it
    row = json.loads(out.read_text(encoding="utf-8"))
    assert row["output"]["error"].startswith("exception: ValueError")
    assert per_row([row], {}).correct.iloc[0] == 0


def row(sid, approach, verdict, gold="covered", cited=("fwd:travel_delay",), error=None, calls=1, latency=1.0):
    return {"scenario_id": sid, "approach": approach, "category": "single_section", "gold_verdict": gold,
            "gold_sections": ["fwd:travel_delay", "fwd:definitions:trip"], "commit": "abc",
            "output": {"verdict": verdict, "cited_sections": list(cited), "error": error,
                       "usage": {"latency_s": latency, "model_calls": calls}}}


def test_per_row_metrics():
    df = per_row([row("a", "A0", "covered"),
                  row("b", "A0", "partially_covered", gold="not_covered", cited=()),
                  row("c", "A0", "covered", error="parse_error")], gold={})
    assert df.correct.tolist() == [1, 0, 0]                            # an error row is wrong
    assert df.binary_correct.tolist() == [1, 0, 0]
    assert df.wrong_covered.iloc[1] == 1 and df.wrong_covered.isna().sum() == 2   # only gold not_covered counts
    assert df.clause_recall.tolist() == [0.5, 0.0, 0.5]


def test_faithfulness_from_judge():
    rows = [row("a", "A0", "covered"), row("b", "A0", "covered"), row("c", "A0", "covered", error="parse_error"),
            row("d", "A0", "covered")]
    df = per_row(rows, gold={}, judged={("a", "A0"): "yes", ("b", "A0"): "partly", ("c", "A0"): "yes"})
    assert df.faith.iloc[:3].tolist() == ["yes", "partly", "no"] and df.faith.isna().iloc[3]   # error -> "no"
    assert df.faithful.iloc[:3].tolist() == [1, 0, 0] and np.isnan(df.faithful.iloc[3])
    assert per_row(rows, gold={}).faith.isna().all()                   # judge not run: no faithfulness at all


def test_gold_comes_from_current_labels():
    df = per_row([row("a", "A0", "not_covered")], gold={"a": {"gold_verdict": "not_covered",
                                                             "gold_sections": ["fwd:travel_delay"],
                                                             "category": "tricky"}})
    assert df.correct.iloc[0] == 1 and df.category.iloc[0] == "tricky" and df.clause_recall.iloc[0] == 1


def test_mcnemar_counts_discordant_pairs():
    rows = ([row(f"s{i}", "A0", "covered") for i in range(10)] +
            [row(f"s{i}", "B0", "covered" if i < 2 else "not_covered") for i in range(10)])
    t = mcnemar_p(per_row(rows, {}), "A0", "B0")
    assert (t["only_a_right"], t["only_b_right"], t["n"]) == (8, 0, 10)
    assert t["p"] == pytest.approx(2 * 0.5 ** 8)                       # exact binomial, two-sided


def test_score_runs_preregistered_tests_and_decision():
    rows = ([row(f"s{i}", "A0", "covered") for i in range(10)] +
            [row(f"s{i}", "B0", "not_covered") for i in range(10)] +
            [row(f"s{i}", "A2", "covered", calls=3) for i in range(10)])
    result, by_cat = score(rows, {})
    labels = [t["label"] for t in result["tests"]]
    assert labels == ["best agent vs A0", "A0 vs B0"]                  # A2 vs A4 skipped: A4 did not run
    assert result["tests"][1]["significant"]
    assert result["decision"]["winner"] == "A0"                        # tied with A2 but fewer model calls
    assert set(by_cat.approach) == {"A0", "A2", "B0"}
    assert result["overall"]["A0"]["verdict_accuracy_lo"] == 1.0


def test_decision_excludes_approach_less_safe_than_a0():
    rows = ([row(f"s{i}", "A0", "not_covered", gold="not_covered") for i in range(5)] +
            [row(f"s{i}", "A4", "covered", gold="not_covered") for i in range(5)])
    result, _ = score(rows, {})
    assert result["decision"]["winner"] == "A0"
    assert decide(per_row(rows, {}), {"A0": result["overall"]["A0"]})["reason"] == "only eligible approach"
