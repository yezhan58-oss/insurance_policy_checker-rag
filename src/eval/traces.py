"""Score the traces (`steps`) of each approach, not just its final verdict: did each step find the right policy
sections, did the sections the verdict needs ever reach the model, and how much work did it take.

    python -m src.eval.traces --model vllm_gptoss20b --split dev

Reads results/<split>/<model>/raw.jsonl and the gold labels; writes traces.json and trace_steps.csv next to it.
Everything is measured against gold_sections, so no extra labels are needed. Per approach:

- evidence recall: share of gold sections that reached the answer's context (whether or not they were cited).
- wrong answers split into missing_evidence (a gold section never reached the model: a retrieval failure),
  had_evidence (all gold sections were in context, still wrong: a reasoning failure) and error (no answer).
- per step: recall of the gold sections of the step's type (e.g. A4's exclusions step vs gold exclusions),
  precision of what it selected, how often it selected something when gold has nothing of that type, fallbacks.
- efficiency: model calls, tokens, latency, sections put in context, share of them not needed, parse retries.

Trace convention: a step that decides what policy text the answer sees lists those section IDs
under "context" (A2 should do this). Without one, the context is inferred from "hits" (A0's search), "picked"
(A4's benefits and exclusions) and "fetched" (A4's definitions).
"""
import argparse
import csv
import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

from src import store
from src.eval.run import RESULTS_DIR, load_scenarios

STEP_TYPE = {"benefits": "benefit", "definitions": "definition", "exclusions": "exclusion"}   # step -> section type
NOT_SELECTION = {"answer", "parse_failed"}


@lru_cache(maxsize=None)
def section_type(section_id: str) -> str | None:
    sec = store.get_section(section_id)
    return sec.type if sec else None


def selected(step: dict) -> list[str] | None:
    """Section IDs a step selected, in order, or None for steps that select nothing (e.g. the answer call)."""
    if step["step"] in NOT_SELECTION:
        return None
    for key in ("context", "picked", "fetched"):
        if key in step:
            return list(dict.fromkeys(step[key]))
    if "hits" in step:
        return list(dict.fromkeys(h["section_id"] for h in step["hits"]))
    return None


def context_sections(steps: list[dict]) -> set[str]:
    explicit = [s["context"] for s in steps if "context" in s]
    if explicit:
        return set(explicit[-1])
    return {i for s in steps for i in (selected(s) or [])}


def ratio(num: int, den: int) -> float:
    return num / den if den else float("nan")


def trace_row(row: dict, gold: dict) -> dict:
    o, g = row["output"], gold
    gs = set(g["gold_sections"])
    ctx = context_sections(o.get("steps") or [])
    usage = o.get("usage") or {}
    correct = o.get("error") is None and o["verdict"] == g["gold_verdict"]
    missing = gs - ctx
    failure = None if correct else "error" if o.get("error") else "missing_evidence" if missing else "had_evidence"
    return {"scenario_id": row["scenario_id"], "approach": row["approach"], "correct": correct, "failure": failure,
            "evidence_recall": ratio(len(gs & ctx), len(gs)), "missing": sorted(missing),
            "context_size": len(ctx), "unneeded_share": ratio(len(ctx - gs), len(ctx)),
            "model_calls": usage.get("model_calls", 0),
            "tokens": usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0),
            "latency_s": usage.get("latency_s", 0.0),
            "parse_retries": sum(s["step"] == "parse_failed" for s in o.get("steps") or [])}


def step_rows(row: dict, gold: dict) -> list[dict]:
    """One record per selecting step: what it picked vs the gold sections of its type (all gold if untyped)."""
    out = []
    for s in row["output"].get("steps") or []:
        sel = selected(s)
        if sel is None:
            continue
        typ = STEP_TYPE.get(s["step"])
        gs = {i for i in gold["gold_sections"] if typ is None or section_type(i) == typ}
        out.append({"scenario_id": row["scenario_id"], "approach": row["approach"], "step": s["step"],
                    "selected": len(sel), "gold": len(gs), "hit": len(gs & set(sel)),
                    "recall": ratio(len(gs & set(sel)), len(gs)), "precision": ratio(len(gs & set(sel)), len(sel)),
                    "over_pick": float(bool(sel)) if not gs else float("nan"),
                    "fallback": float(s["fallback"]) if "fallback" in s else float("nan")})
    return out


def nanmean(values) -> float:
    v = np.asarray(list(values), dtype=float)
    return float(np.nanmean(v)) if np.isfinite(v).any() else float("nan")


def summarise(traces: list[dict], steps: list[dict]) -> dict:
    out = {}
    for a in sorted({t["approach"] for t in traces}):
        ts = [t for t in traces if t["approach"] == a]
        wrong = [t for t in ts if not t["correct"]]
        per_step = {}
        for name in dict.fromkeys(s["step"] for s in steps if s["approach"] == a):
            ss = [s for s in steps if s["approach"] == a and s["step"] == name]
            per_step[name] = {"n": len(ss), "mean_selected": nanmean(s["selected"] for s in ss),
                              "recall": nanmean(s["recall"] for s in ss),
                              "precision": nanmean(s["precision"] for s in ss),
                              "over_pick_rate": nanmean(s["over_pick"] for s in ss),
                              "fallback_rate": nanmean(s["fallback"] for s in ss)}
        out[a] = {"n": len(ts), "wrong": len(wrong),
                  **{f: sum(t["failure"] == f for t in wrong) for f in ("missing_evidence", "had_evidence", "error")},
                  **{m: nanmean(t[m] for t in ts) for m in ("evidence_recall", "context_size", "unneeded_share",
                                                            "model_calls", "tokens", "latency_s", "parse_retries")},
                  "steps": per_step}
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--dir", type=Path, help="results folder (default results/<split>/<model>)")
    args = ap.parse_args()

    out_dir = args.dir or RESULTS_DIR / args.split / args.model
    with (out_dir / "raw.jsonl").open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    gold = {s.id: {"gold_verdict": s.gold_verdict, "gold_sections": s.gold_sections}
            for s in load_scenarios(args.split)}
    traces = [trace_row(r, gold[r["scenario_id"]]) for r in rows]
    steps = [s for r in rows for s in step_rows(r, gold[r["scenario_id"]])]
    summary = summarise(traces, steps)
    (out_dir / "traces.json").write_text(json.dumps({"summary": summary, "rows": traces}, indent=1), encoding="utf-8")
    with (out_dir / "trace_steps.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(steps[0]))
        w.writeheader()
        w.writerows(steps)

    print(f"{args.model} | {args.split} | {len(rows)} rows\n")
    for a, s in summary.items():
        print(f"{a:3} evidence recall {s['evidence_recall']:.2f} | wrong {s['wrong']}/{s['n']}: missing evidence "
              f"{s['missing_evidence']}, had evidence {s['had_evidence']}, error {s['error']}"
              f"\n    {s['model_calls']:.1f} calls, {s['tokens']:.0f} tokens, {s['latency_s']:.1f}s, "
              f"{s['context_size']:.1f} sections in context"
              + (f" ({s['unneeded_share']:.0%} not needed)" if s["context_size"] else "")
              + f", {s['parse_retries']:.2f} parse retries")
        for name, st in s["steps"].items():
            print(f"    step {name:12} picks {st['mean_selected']:4.1f}  recall {st['recall']:.2f}  precision "
                  f"{st['precision']:.2f}  picks when gold has none {st['over_pick_rate']:.2f}"
                  f"  fallback {st['fallback_rate']:.2f}  (n={st['n']})")


if __name__ == "__main__":
    main()
