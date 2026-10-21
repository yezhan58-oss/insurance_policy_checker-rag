import csv

import pytest

from src.eval import agreement


def test_cohen_kappa_known_values():
    assert agreement.cohen_kappa(["x", "x", "y", "y"], ["x", "y", "y", "y"]) == pytest.approx(0.5)
    assert agreement.cohen_kappa(["x", "y", "x"], ["x", "y", "x"]) == pytest.approx(1.0)


def test_sheet_hides_labels_and_is_reproducible(tmp_path, monkeypatch):
    monkeypatch.setattr(agreement.store, "list_sections", lambda policy: [])
    sheets = []
    for run in (1, 2):
        monkeypatch.setattr(agreement, "SHEET", tmp_path / f"sheet{run}.csv")
        monkeypatch.setattr(agreement, "SECTION_LIST", tmp_path / "sections.csv")
        agreement.make_sheet()
        with agreement.SHEET.open(encoding="utf-8-sig", newline="") as f:
            sheets.append(list(csv.DictReader(f)))
    rows = sheets[0]
    assert len(rows) == agreement.N_BLIND and len({r["id"] for r in rows}) == agreement.N_BLIND
    assert list(rows[0]) == agreement.SHEET_COLS                     # no gold_verdict, gold_sections or notes
    assert all(r["verdict"] == r["sections"] == "" for r in rows)
    assert [r["id"] for r in rows] == [r["id"] for r in sheets[1]]   # fixed seed: same 40 every time


def test_incomplete_sheet_is_refused(tmp_path, monkeypatch):
    sheet = tmp_path / "sheet.csv"
    sheet.write_text("id,policy,scenario,verdict,sections,note\nfwd-001,fwd,claim,,,\n", encoding="utf-8-sig")
    monkeypatch.setattr(agreement, "SHEET", sheet)
    with pytest.raises(SystemExit, match="no labels shown yet"):
        agreement.read_sheet()
