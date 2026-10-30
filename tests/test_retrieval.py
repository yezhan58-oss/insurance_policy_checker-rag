import pytest

from src.eval import retrieval
from src.schema import Scenario

CHUNKS = {"fwd": [
    {"chunk_id": "fwd:travel_delay#0", "section_id": "fwd:travel_delay",
     "text": "FWD > Travel delay\nWe pay if your scheduled flight is delayed for 6 continuous hours."},
    {"chunk_id": "fwd:missed_connections#0", "section_id": "fwd:missed_connections",
     "text": "FWD > Missed connections\nWe pay if your scheduled flight is delayed for 6 continuous hours."},
    {"chunk_id": "fwd:definitions:strike#0", "section_id": "fwd:definitions:strike",
     "text": "FWD > Definitions > Strike\nStrike means any form of industrial action by workers."},
    {"chunk_id": "fwd:baggage#0", "section_id": "fwd:baggage",
     "text": "FWD > Baggage\nWe pay for lost or damaged baggage and personal belongings."}]}
TYPES = {"fwd:travel_delay": "benefit", "fwd:missed_connections": "benefit", "fwd:definitions:strike": "definition",
         "fwd:baggage": "benefit"}


def test_bm25_ranks_matching_chunks_first_and_drops_identical_copies():
    rank = retrieval.bm25_ranker(CHUNKS)
    ranked = rank("my flight was delayed by a strike", "fwd", 10)
    ids = [c["chunk_id"] for c in ranked]
    # "strike" is the rarest query word and appears twice in its chunk, so that chunk leads
    assert ids[0] == "fwd:definitions:strike#0"
    # the two delay chunks share a body: only the first by chunk id is kept, as store.search does
    assert ids[1] == "fwd:missed_connections#0" and "fwd:travel_delay#0" not in ids
    assert ids[-1] == "fwd:baggage#0" and len(ids) == 3                 # shares no query word


def test_fusion_rewards_chunks_both_rankings_agree_on():
    a = [{"chunk_id": x, "section_id": x} for x in ("p", "q", "r")]
    b = [{"chunk_id": x, "section_id": x} for x in ("q", "s", "p")]
    fused = [c["chunk_id"] for c in retrieval.fuse(a, b)]
    assert fused[:2] == ["q", "p"] and set(fused) == {"p", "q", "r", "s"}
    assert retrieval.sections_in([{"section_id": "x"}, {"section_id": "x"}, {"section_id": "y"}], 2) == ["x"]


def test_evaluate_reports_recall_overall_and_by_gold_type():
    sc = Scenario(id="fwd-1", policy="fwd", category="needs_definition", gold_verdict="not_covered",
                  scenario="my flight was delayed by a strike",
                  gold_sections=["fwd:travel_delay", "fwd:definitions:strike"])
    perfect = lambda q, p, n: [{"chunk_id": g, "section_id": g} for g in sc.gold_sections][:n]
    benefit_only = lambda q, p, n: [{"chunk_id": "fwd:travel_delay#0", "section_id": "fwd:travel_delay"}]
    res = retrieval.evaluate([sc], {"perfect": perfect, "benefit_only": benefit_only}, TYPES.get)
    assert res["perfect"][5]["recall"] == 1 and res["perfect"][5]["all_found"] == 1
    m = res["benefit_only"][5]
    assert m["recall"] == pytest.approx(0.5) and m["all_found"] == 0
    assert m["by_type"]["benefit"] == {"found": 1, "n": 1, "recall": 1.0}
    assert m["by_type"]["definition"]["recall"] == 0
    assert "| benefit_only | 5 | 0.50 | 0.00 |" in retrieval.markdown(res, "dev", 1)
