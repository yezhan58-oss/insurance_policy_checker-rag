"""Retrieval-only comparison, no LLM calls: how often does one search with the claim text find the gold sections?

    python -m src.eval.retrieval --split test

Compares the embedding search every setup uses (dense, BGE + Chroma) with BM25 keyword search over the same chunks
and a hybrid of the two (reciprocal rank fusion of both rankings), at k = 5 (A0's top_k) and k = 10 chunks.
Per method and k: gold-section recall (mean per claim), share of claims with every gold section found, and recall
per gold section type (a benefit is named in the claim; definitions and exclusions often are not).

Analysis only: no approach uses BM25 or the hybrid, so the frozen setups are unchanged. Dense at k = 5 is exactly
A0's search, so its recall should match A0's evidence recall in src/eval/traces.py (a built-in consistency check).
Needs the index (python -m src.ingest). Writes results/<split>/retrieval/retrieval.json and retrieval.md.
"""
import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict

from src import store
from src.eval.run import RESULTS_DIR, load_scenarios

KS = (5, 10)
DEPTH = 50                 # candidates per ranking before fusion
RRF_K = 60                 # the usual reciprocal-rank-fusion constant
TYPES = ("benefit", "definition", "exclusion", "condition", "other")


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25:
    """Okapi BM25 over a fixed list of documents (k1 = 1.5, b = 0.75)."""

    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.tf = [Counter(tokenize(d)) for d in docs]
        self.len = [sum(tf.values()) for tf in self.tf]
        self.avg = sum(self.len) / len(self.len)
        df = Counter(t for tf in self.tf for t in tf)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        return [sum(self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * n / self.avg))
                    for t in q if t in tf)
                for tf, n in zip(self.tf, self.len)]


def policy_chunks(policy: str) -> list[dict]:
    """Every indexed chunk of one policy (the same chunks dense search ranks), in a fixed order."""
    res = store._collection().get(where={"policy": policy}, include=["documents", "metadatas"])
    chunks = [{"chunk_id": i, "section_id": m["section_id"], "text": d}
              for i, d, m in zip(res["ids"], res["documents"], res["metadatas"])]
    return sorted(chunks, key=lambda c: c["chunk_id"])


def drop_copies(ranked: list[dict]) -> list[dict]:
    """Keep the first of chunks with identical bodies (shared FWD benefit blocks), as store.search does."""
    out, seen = [], set()
    for c in ranked:
        body = c["text"].split("\n", 1)[-1]
        if body not in seen:
            seen.add(body)
            out.append(c)
    return out


def bm25_ranker(chunks_by_policy: dict[str, list[dict]]):
    index = {p: BM25([c["text"] for c in cs]) for p, cs in chunks_by_policy.items()}

    def rank(query: str, policy: str, n: int) -> list[dict]:
        cs, scores = chunks_by_policy[policy], index[policy].scores(query)
        order = sorted(range(len(cs)), key=lambda i: (-scores[i], cs[i]["chunk_id"]))
        return drop_copies([cs[i] for i in order])[:n]
    return rank


def dense_ranker(query: str, policy: str, n: int) -> list[dict]:
    return [{"chunk_id": h.chunk_id, "section_id": h.section_id, "text": h.text} for h in store.search(query, policy, n)]


def fuse(*rankings: list[dict], k: int = RRF_K) -> list[dict]:
    """Reciprocal rank fusion: score = sum of 1 / (k + rank) over the rankings that contain the chunk."""
    score, chunk = defaultdict(float), {}
    for ranking in rankings:
        for r, c in enumerate(ranking, 1):
            score[c["chunk_id"]] += 1 / (k + r)
            chunk[c["chunk_id"]] = c
    return [chunk[i] for i in sorted(score, key=lambda i: (-score[i], i))]


def sections_in(ranked: list[dict], k: int) -> list[str]:
    return list(dict.fromkeys(c["section_id"] for c in ranked[:k]))


def evaluate(scenarios, rankers: dict, section_type) -> dict:
    """{method: {k: metrics}} for rankers {name: rank(query, policy, n) -> ranked chunks}."""
    out = {}
    for name, rank in rankers.items():
        per_k = {k: {"recall": [], "all_found": [], "by_type": defaultdict(lambda: [0, 0])} for k in KS}
        for sc in scenarios:
            gold = list(dict.fromkeys(sc.gold_sections))
            for k in KS:     # one search per k: dense with k = 5 is then exactly A0's call, store.search(claim, policy, 5)
                found = set(sections_in(rank(sc.scenario, sc.policy, k), k))
                m = per_k[k]
                m["recall"].append(sum(g in found for g in gold) / len(gold) if gold else float("nan"))
                m["all_found"].append(float(all(g in found for g in gold)) if gold else float("nan"))
                for g in gold:
                    t = m["by_type"][section_type(g) or "other"]
                    t[0] += g in found
                    t[1] += 1
        out[name] = {k: {"recall": _mean(m["recall"]), "all_found": _mean(m["all_found"]),
                         "by_type": {t: {"found": f, "n": n, "recall": f / n} for t, (f, n) in m["by_type"].items()}}
                     for k, m in per_k.items()}
    return out


def _mean(values: list[float]) -> float:
    v = [x for x in values if x == x]
    return sum(v) / len(v) if v else float("nan")


def markdown(result: dict, split: str, n: int) -> str:
    types = [t for t in TYPES if any(t in m["by_type"] for per_k in result.values() for m in per_k.values())]
    head = "| Method | k | Gold recall | All gold found | " + " | ".join(t.capitalize() for t in types) + " |"
    lines = [f"# Retrieval only: one search with the claim text ({split} split, {n} claims)", "", head,
             "|" + "---|" * (4 + len(types))]
    for name, per_k in result.items():
        for k, m in per_k.items():
            cells = [f"{m['by_type'][t]['recall']:.2f} ({m['by_type'][t]['found']}/{m['by_type'][t]['n']})"
                     if t in m["by_type"] else "–" for t in types]
            lines.append(f"| {name} | {k} | {m['recall']:.2f} | {m['all_found']:.2f} | " + " | ".join(cells) + " |")
    lines += ["", "_k = number of chunks retrieved (A0 uses 5). Type columns: recall of gold sections of that type "
              "(found / total). Dense at k = 5 is A0's own search. BM25 and the hybrid are analysis only._"]
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    args = ap.parse_args()
    scenarios = load_scenarios(args.split)
    chunks = {p: policy_chunks(p) for p in sorted({s.policy for s in scenarios})}
    bm25 = bm25_ranker(chunks)
    rankers = {"dense": dense_ranker, "bm25": bm25,
               "hybrid": lambda q, p, n: fuse(dense_ranker(q, p, DEPTH), bm25(q, p, DEPTH))[:n]}

    def section_type(i):
        sec = store.get_section(i)
        return sec.type if sec else None

    result = evaluate(scenarios, rankers, section_type)
    out = RESULTS_DIR / args.split / "retrieval"
    out.mkdir(parents=True, exist_ok=True)
    (out / "retrieval.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    md = markdown(result, args.split, len(scenarios))
    (out / "retrieval.md").write_text(md, encoding="utf-8")
    print(md + f"\nWrote {out / 'retrieval.md'}")


if __name__ == "__main__":
    main()
