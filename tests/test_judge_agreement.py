import pandas as pd
import pytest

from src.eval import judge


def sheet(tmp_path, human):
    p = tmp_path / "hand_check.csv"
    pd.DataFrame({"judge": ["yes", "no"], "explanation": ["a b", "c"], "human": human}).to_csv(p, index=False)
    return p


def test_agreement_rejects_bad_label_and_empty_sheet(tmp_path):
    with pytest.raises(SystemExit, match="maybe"):
        judge.agreement(sheet(tmp_path, ["yes", "maybe"]))
    with pytest.raises(SystemExit, match="No human labels"):
        judge.agreement(sheet(tmp_path, ["", " "]))
    assert judge.agreement(sheet(tmp_path, [" Yes", "no"]))["agreement"] == 1.0
