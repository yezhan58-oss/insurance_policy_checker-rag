"""Policy lookups built on store.py, for A4 (and A3 if it is built).

    get_definition(term, policy)        the definition section of one defined term, or None
    find_defined_terms(text, policy)    definition section_ids of the defined terms that appear in `text`
    get_exclusions(section_id)          exclusions that apply to one benefit section

Exclusions: every policy-wide exclusion section, plus (MSIG) the group exclusions whose heading lists the benefit's
section number, e.g. "msig:exclusions_sections_21_22_25_..." applies to msig:section_25. FWD keeps its
benefit-specific exclusions ("What is not covered") inside the benefit section itself.
"""
import re

from src import store
from src.schema import Chunk

# Defined terms too generic to be worth fetching: they appear in almost every sentence.
GENERIC_TERMS = {"we", "us", "our", "you", "your", "policy", "the company", "schedule", "insured", "policyholder",
                 "insured person", "insured persons"}
GROUP_PREFIX = "msig:exclusions_sections_"


def get_definition(term: str, policy: str) -> Chunk | None:
    section_id = store.definitions(policy).get(term.lower().strip())
    return store.get_section(section_id) if section_id else None


def find_defined_terms(text: str, policy: str) -> list[str]:
    """Definition section_ids for the defined terms used in `text`, in order of first appearance, no repeats."""
    hits = {}
    for term, section_id in store.definitions(policy).items():
        if term in GENERIC_TERMS:
            continue
        m = re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE)
        if m and (section_id not in hits or m.start() < hits[section_id]):
            hits[section_id] = m.start()
    return sorted(hits, key=hits.get)


def get_exclusions(section_id: str) -> list[Chunk]:
    """Exclusion sections that apply to the benefit `section_id`, in document order."""
    policy = section_id.split(":", 1)[0]
    number = section_id.removeprefix("msig:section_") if section_id.startswith("msig:section_") else None
    out = []
    for c in store.list_sections(policy, "exclusion"):
        if c.section_id.startswith(GROUP_PREFIX):
            if number and number in c.section_id.removeprefix(GROUP_PREFIX).split("_"):
                out.append(c)
        else:
            out.append(c)
    return out


def _norm(s: str) -> str:
    s = s.lower().replace("’", "'").replace("‘", "'").replace("‑", "-").replace("‐", "-")
    return re.sub(r"[^a-z0-9$%']+", " ", s).strip()


def unsupported_quotes(explanation: str, policy: str) -> list[str]:
    """Quoted phrases (4+ words) in the explanation that appear nowhere in the policy wording.

    Checked against the whole policy, not just cited sections: real answers often quote a definition they did not cite.
    """
    text = _norm(" ".join(c.text for c in store.list_sections(policy)))
    quotes = re.findall(r'"([^"]+)"|“([^”]+)”', explanation)
    bad = []
    for q in (a or b for a, b in quotes):
        parts = [_norm(p) for p in re.split(r"\.\.\.|…", q)]  # ellipsis: check each piece
        if any(len(p.split()) >= 4 and p not in text for p in parts):
            bad.append(q)
    return bad
