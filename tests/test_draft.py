import json

import pytest

from src.scenarios.draft import check
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
