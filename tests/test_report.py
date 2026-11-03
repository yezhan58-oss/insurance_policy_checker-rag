import pandas as pd

from src.eval.report import split_other


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
