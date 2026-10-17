import json

import pytest

from src.scenarios.draft import check, split
from src.store import SECTIONS_PATH

pytestmark = pytest.mark.skipif(not SECTIONS_PATH.exists(), reason="index not built (python -m src.ingest)")

GOOD = {"id": "fwd-001", "policy": "fwd", "scenario": "Flight delayed 7 hours by a typhoon.", "category": "single_section",
        "source_clause": "fwd:travel_delay", "gold_verdict": "covered", "gold_sections": ["fwd:travel_delay"]}


def test_check(tmp_path):
    bad = [GOOD,
           {**GOOD, "id": "fwd-001"},                                        # duplicate id
           {**GOOD, "id": "fwd-002", "gold_sections": ["fwd:no_such_section"]},
           {**GOOD, "id": "fwd-003", "gold_verdict": "maybe"}]               # not a verdict
    path = tmp_path / "drafts.jsonl"
    path.write_text("\n".join(map(json.dumps, bad)), encoding="utf-8")
    problems = check(path)
    assert len(problems) == 3
    assert any("duplicate" in p for p in problems)
    assert any("fwd:no_such_section" in p for p in problems)

    path.write_text(json.dumps(GOOD), encoding="utf-8")
    assert check(path) == []


def test_split_is_deterministic_and_drops_deleted(tmp_path):
    rows = [{**GOOD, "id": f"{p}-{n:03d}", "policy": p, "status": "deleted" if n == 0 else "accepted"}
            for p in ("fwd", "msig") for n in range(15)]
    (tmp_path / "reviewed.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    dev, test = split(tmp_path)
    assert len(dev) == 20 and len(test) == 8
    assert sum(r["policy"] == "fwd" for r in dev) == 10
    assert not {r["id"] for r in dev + test} & {"fwd-000", "msig-000"}
    assert [r["id"] for r in split(tmp_path)[0]] == [r["id"] for r in dev]
