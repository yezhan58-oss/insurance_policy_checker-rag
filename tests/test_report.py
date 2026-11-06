import pandas as pd

from src.eval.report import safe_mode, split_other


def test_split_other_by_rule_keeps_other_human_labels():
    cases = [  # id, human label, gold, predicted, trace failure
        ("s1", "other", "covered", "insufficient_info", "had_evidence"),        # over-cautious
        ("s2", "other", "covered", "insufficient_info", "missing_evidence"),    # evidence missing: stays other
        ("s3", "other", "partially_covered", "not_covered", "had_evidence"),   # all-or-nothing
        ("s4", "other", "covered", "not_covered", "had_evidence"),             # stays other
        ("s5", "missed_exclusion", "partially_covered", "covered", "had_evidence"),  # human label kept
    ]
    et = pd.DataFrame([{"scenario_id": c[0], "approach": "A4", "error_type": c[1], "note": ""} for c in cases])
    rows = [{"scenario_id": c[0], "approach": "A4", "gold_verdict": c[2], "output": {"verdict": c[3]}} for c in cases]
    tr = [{"scenario_id": c[0], "approach": "A4", "failure": c[4]} for c in cases]
    assert list(split_other(et, rows, tr).error_type) == [
        "over_cautious_insufficient_info", "other", "all_or_nothing_partial", "other", "missed_exclusion"]


def test_safe_mode_uses_the_check_only_when_the_first_answer_says_covered():
    def row(sid, approach, verdict, gold, tokens):
        return {"scenario_id": sid, "approach": approach, "gold_verdict": gold,
                "output": {"verdict": verdict, "usage": {"prompt_tokens": tokens, "completion_tokens": 0,
                                                          "latency_s": 1.0}}}
    rows = [row("s1", "A0", "covered", "not_covered", 100), row("s1", "A4", "not_covered", "not_covered", 300),
            row("s2", "A0", "not_covered", "not_covered", 100), row("s2", "A4", "covered", "not_covered", 300),
            row("s3", "A0", "covered", "covered", 100), row("s3", "A4", "insufficient_info", "covered", 300)]
    s = safe_mode(rows)
    assert (s["n"], s["checked"], s["wrong_covered"], s["not_covered"]) == (3, 2, 0, 2)
    assert s["accuracy"] == 2 / 3                       # s1 fixed by the check, s2 kept, s3 lost to the check
    assert s["tokens"] == (100 * 3 + 300 * 2) / 3 and s["latency_s"] == 5 / 3
