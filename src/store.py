"""CONTRACT: read access to the policy index built by `python -m src.ingest`.
Change only with agreement from both members.

    search(query, policy, k)        top-k chunks of one policy by embedding similarity
    get_section(section_id)         one whole section (text of all its chunks joined)
    list_sections(policy, type)     whole sections of a policy, optionally of one type
    definitions(policy)             {term_lowercase: section_id} for defined terms

Whole sections are returned as a Chunk whose chunk_id == section_id and score is None.
Chunk and section text starts with a breadcrumb line, e.g. "FWD Travel Insurance > General exclusions > ...".
"""
import json
import os
from functools import lru_cache
from pathlib import Path

from src.schema import Chunk, SectionType

ROOT = Path(__file__).resolve().parents[1]
# git-ignored; rebuilt on every machine by src.ingest. Cluster jobs set RAG_INDEX_DIR to node-local disk so
# concurrent jobs never share one index (and SQLite never sits on the network filesystem).
INDEX_DIR = Path(os.environ.get("RAG_INDEX_DIR") or ROOT / "data" / "index")
SECTIONS_PATH = INDEX_DIR / "sections.jsonl"  # one whole section per line (ingest output)
DEFINITIONS_PATH = INDEX_DIR / "definitions.json"
CHROMA_DIR = INDEX_DIR / "chroma"
COLLECTION = "policy_chunks"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"        # always loaded with device="cpu"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "   # BGE v1.5 query instruction
OVERSAMPLE = 4                                # fetch k * OVERSAMPLE candidates, then drop exact copies


def _missing_index() -> FileNotFoundError:
    return FileNotFoundError(f"No index at {INDEX_DIR}. Build it first: python -m src.ingest")


@lru_cache(maxsize=1)
def _sections() -> dict[str, dict]:
    if not SECTIONS_PATH.exists():
        raise _missing_index()
    with SECTIONS_PATH.open(encoding="utf-8") as f:
        return {s["section_id"]: s for s in map(json.loads, f)}


@lru_cache(maxsize=1)
def _definitions() -> dict[str, dict[str, str]]:
    if not DEFINITIONS_PATH.exists():
        raise _missing_index()
    return json.loads(DEFINITIONS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _collection():
    import chromadb
    from chromadb.config import Settings

    if not CHROMA_DIR.exists():
        raise _missing_index()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))
    return client.get_collection(COLLECTION)


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL, device="cpu")


def _check_policy(policy: str) -> None:
    known = {s["policy"] for s in _sections().values()}
    if policy not in known:
        raise ValueError(f"Unknown policy '{policy}'. Indexed policies: {', '.join(sorted(known))}")


def _whole(s: dict) -> Chunk:
    return Chunk(chunk_id=s["section_id"], section_id=s["section_id"], policy=s["policy"], title=s["title"],
                 type=s["type"], page=s["page"], text=f"{s['path']}\n{s['text']}", score=None)


def search(query: str, policy: str, k: int = 5) -> list[Chunk]:
    """Top-k chunks from `policy` most similar to `query`, best first, with `score` set (cosine similarity).

    Benefits that share one block of text (e.g. FWD Trip diversion / Travel delay / Missed connections)
    store identical copies of it; only the best-ranked copy is returned, so copies never fill the top k.
    """
    _check_policy(policy)
    vector = _model().encode([QUERY_PREFIX + query], normalize_embeddings=True).tolist()
    res = _collection().query(query_embeddings=vector, n_results=k * OVERSAMPLE, where={"policy": policy},
                              include=["documents", "metadatas", "distances"])
    hits = sorted(zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]),
                  key=lambda h: (h[3], h[0]))   # ties (identical copies) break by chunk id: deterministic
    out, seen = [], set()
    for chunk_id, text, meta, distance in hits:
        body = text.split("\n", 1)[-1]      # first line is the section's breadcrumb, which differs per copy
        if body in seen:
            continue
        seen.add(body)
        out.append(Chunk(chunk_id=chunk_id, section_id=meta["section_id"], policy=meta["policy"],
                         title=meta["title"], type=meta["type"], page=meta["page"], text=text,
                         score=round(1 - distance, 4)))
        if len(out) == k:
            break
    return out


def get_section(section_id: str) -> Chunk | None:
    """The whole section with this id, or None if the id does not exist."""
    s = _sections().get(section_id)
    return _whole(s) if s else None


def list_sections(policy: str, type: SectionType | None = None) -> list[Chunk]:
    """All whole sections of `policy` in document order, optionally only one `type`."""
    _check_policy(policy)
    return [_whole(s) for s in _sections().values() if s["policy"] == policy and (type is None or s["type"] == type)]


def definitions(policy: str) -> dict[str, str]:
    """Defined-term lookup for `policy`: {term_lowercase: section_id}."""
    _check_policy(policy)
    return dict(_definitions().get(policy, {}))
