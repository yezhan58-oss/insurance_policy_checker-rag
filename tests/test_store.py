import pytest

from src import store

pytestmark = pytest.mark.skipif(not store.CHROMA_DIR.exists(), reason="index not built (python -m src.ingest)")


def test_search_finds_travel_delay():
    hits = store.search("My flight to Tokyo was delayed 7 hours because of a typhoon. Can I claim?", "fwd", k=5)
    assert len(hits) == 5
    assert "fwd:travel_delay" in [h.section_id for h in hits[:3]]
    assert all(h.policy == "fwd" for h in hits)
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)


def test_search_msig_stays_in_policy():
    hits = store.search("Am I covered if I give birth overseas?", "msig", k=5)
    assert all(h.policy == "msig" for h in hits)
    assert {"msig:section_11", "msig:general_exclusion_4"} <= {h.section_id for h in hits}


def test_search_drops_identical_copies():
    hits = store.search("cancel my trip because my mother was hospitalised", "fwd", k=8)
    bodies = [h.text.split("\n", 1)[1] for h in hits]
    assert len(bodies) == len(set(bodies))


def test_search_rejects_unknown_policy():
    with pytest.raises(ValueError):
        store.search("anything", "nope")


def test_get_section():
    sec = store.get_section("fwd:general_exclusions:mental_illness")
    assert sec.chunk_id == sec.section_id and sec.score is None
    assert sec.type == "exclusion"
    assert sec.text.startswith("FWD Travel Insurance > General exclusions > Mental illness\n")
    assert store.get_section("fwd:no_such_section") is None


def test_list_sections_by_type():
    exclusions = store.list_sections("fwd", "exclusion")
    assert all(s.type == "exclusion" for s in exclusions)
    assert sum(s.section_id.startswith("fwd:general_exclusions:") for s in exclusions) == 21   # pp. 29-30
    assert len(store.list_sections("fwd")) > len(exclusions)


def test_definitions_lookup():
    terms = store.definitions("fwd")
    assert terms["scheduled public transport"] == "fwd:definitions:scheduled_public_transport"
    assert terms["children"] == terms["child"] == "fwd:definitions:children"
    assert store.get_section(terms["pre-existing medical condition"]).type == "definition"
