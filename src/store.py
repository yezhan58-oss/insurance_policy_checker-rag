"""CONTRACT: read access to the policy index built by `python -m src.ingest`.
Change only with agreement from both members.

    search(query, policy, k)        top-k chunks of one policy by embedding similarity
    get_section(section_id)         one whole section (text of all its chunks joined)
    list_sections(policy, type)     whole sections of a policy, optionally of one type
    definitions(policy)             {term_lowercase: section_id} for defined terms

Whole sections are returned as a Chunk whose chunk_id == section_id and score is None.
"""
from pathlib import Path

from src.schema import Chunk, SectionType

ROOT = Path(__file__).resolve().parents[1]
INDEX_DIR = ROOT / "data" / "index"          # git-ignored; rebuilt on every machine by src.ingest
SECTIONS_PATH = INDEX_DIR / "sections.jsonl"  # one whole section per line (ingest output)
DEFINITIONS_PATH = INDEX_DIR / "definitions.json"
CHROMA_DIR = INDEX_DIR / "chroma"
COLLECTION = "policy_chunks"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"        # always loaded with device="cpu"


def search(query: str, policy: str, k: int = 5) -> list[Chunk]:
    """Top-k chunks from `policy` most similar to `query`, best first, with `score` set."""
    raise NotImplementedError("store.search: next task after ingest is checked")


def get_section(section_id: str) -> Chunk | None:
    """The whole section with this id, or None if the id does not exist."""
    raise NotImplementedError("store.get_section: next task after ingest is checked")


def list_sections(policy: str, type: SectionType | None = None) -> list[Chunk]:
    """All whole sections of `policy` in document order, optionally only one `type`."""
    raise NotImplementedError("store.list_sections: next task after ingest is checked")


def definitions(policy: str) -> dict[str, str]:
    """Defined-term lookup for `policy`: {term_lowercase: section_id}."""
    raise NotImplementedError("store.definitions: next task after ingest is checked")
