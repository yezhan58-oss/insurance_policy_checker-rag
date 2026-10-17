import pytest

from src.store import SECTIONS_PATH
from src.tools import find_defined_terms, get_definition, get_exclusions

pytestmark = pytest.mark.skipif(not SECTIONS_PATH.exists(), reason="index not built (python -m src.ingest)")


def test_get_definition():
    assert get_definition("Scheduled public transport", "fwd").section_id == "fwd:definitions:scheduled_public_transport"
    assert get_definition("public transport", "msig").section_id == "msig:definitions:public_transport"
    assert get_definition("no such term", "fwd") is None


def test_find_defined_terms_skips_generic_and_keeps_order():
    text = "We will pay if your scheduled public transport is delayed, unless your travel companion caused it."
    assert find_defined_terms(text, "fwd") == ["fwd:definitions:scheduled_public_transport",
                                               "fwd:definitions:travel_companion"]


def test_get_exclusions_msig_group_matching():
    ids = [c.section_id for c in get_exclusions("msig:section_25")]
    assert "msig:exclusions_sections_21_22_25_26_27_28_29_30_50" in ids
    assert "msig:exclusions_sections_39_40" not in ids
    assert "msig:general_exclusion_1" in ids and "msig:general_exclusion_18" in ids
    # "2" must not match the "21", "22" or "25" in a group heading
    assert "msig:exclusions_sections_21_22_25_26_27_28_29_30_50" not in [c.section_id for c in get_exclusions("msig:section_2")]


def test_get_exclusions_fwd():
    ids = [c.section_id for c in get_exclusions("fwd:travel_delay")]
    assert "fwd:general_exclusions:events_that_happen_before_you_book_or_take_up_cover" in ids
    assert all(i.startswith("fwd:") for i in ids)
