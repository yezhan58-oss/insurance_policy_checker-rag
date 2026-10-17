import json

import pytest

from src.ingest import Section, chunk_section, slug, term_aliases
from src.store import SECTIONS_PATH


def test_slug():
    assert slug("Loss of passport, travel documents & theft of money") == \
        "loss_of_passport_travel_documents_and_theft_of_money"
    assert slug("What you're covered for") == "what_youre_covered_for"
    assert slug("Child(ren)") == "children"


def test_term_aliases():
    assert term_aliases("Accident or accidental") == {"accident or accidental", "accident", "accidental"}
    assert {"child", "children"} <= term_aliases("Child(ren)")
    assert {"we", "us", "our"} <= term_aliases("We, us, and our")


def test_short_section_is_one_chunk():
    sec = Section("fwd", "T", "h10", page=3, paras=[(3, "text", "word " * 100), (4, "text", "more " * 100)])
    assert chunk_section(sec) == [(3, sec.text)]


def test_long_section_is_split_with_overlap():
    paras = [(p, "text", f"para{p} " + "w " * 29) for p in range(1, 25)]   # 24 x 30 words
    chunks = chunk_section(Section("fwd", "T", "h10", page=1, paras=paras))
    assert len(chunks) > 1
    assert all(len(body.split()) <= 450 for _, body in chunks)
    first, second = chunks[0][1].splitlines(), chunks[1][1].splitlines()
    assert first[-1] == second[0]          # trailing paragraphs (up to 50 words) carried into the next chunk
    assert chunks[1][0] == int(second[0].split()[0].removeprefix("para"))  # page of the chunk's first paragraph


needs_index = pytest.mark.skipif(not SECTIONS_PATH.exists(), reason="index not built (python -m src.ingest)")


@needs_index
def test_parsed_fwd_sections():
    sections = {s["section_id"]: s for s in map(json.loads, SECTIONS_PATH.open(encoding="utf-8"))}
    assert len(sections) == sum(1 for _ in SECTIONS_PATH.open(encoding="utf-8"))   # ids are unique
    assert sum(s["type"] == "definition" for s in sections.values() if s["policy"] == "fwd") == 24
    assert "6 continuous hours" in sections["fwd:travel_delay"]["text"]
    # shared block of the Trip diversion / Travel delay / Missed connections group is in every member
    assert "written proof of the delay" in sections["fwd:trip_diversion"]["text"]
    # tick tables (images in the PDF) come from data/policies/table_transcriptions.yaml
    assert "hijacked for more than 12 hours: Trip cancellation and loss of deposit = No; " \
           "Trip postponement = No; Trip cut short = Yes" in sections["fwd:trip_cut_short"]["text"]
    assert "Travel delay [Premium S$300, Business S$500, First S$1,000]" in \
        sections["fwd:benefit_limits:protecting_your_travel_plans"]["text"]


@needs_index
def test_parsed_msig_sections():
    sections = {s["section_id"]: s for s in map(json.loads, SECTIONS_PATH.open(encoding="utf-8"))}
    msig = [s for s in sections.values() if s["policy"] == "msig"]
    assert sum(s["section_id"].startswith("msig:section_") for s in msig) == 52
    assert sum(s["section_id"].startswith("msig:general_exclusion_") for s in msig) == 18
    assert sum(s["type"] == "definition" for s in msig) == 42
    assert "every full six hours in a row of delay" in sections["msig:section_25"]["text"]
    # term centred in its table cell: the definition line above it still belongs to it
    assert sections["msig:definitions:travel_companion"]["text"].startswith("A person who has made travel bookings")
    # plan values carry their plan name; a merged "Not covered" cell applies to every row it spans
    assert "Adult insured person aged below 70 [Premier Plan $500,000; Elite Plan $200,000; " \
           "Standard Plan $150,000; Lite Plan $50,000]" in sections["msig:section_1"]["text"]
    assert "Child [Lite Plan Not covered; Standard Plan Not covered; Elite Plan $ 150,000; Premier Plan $ 200,000]" \
        in sections["msig:traveleasy_benefits_summary"]["text"]
