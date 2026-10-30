"""Score raw outputs (brief section 9): metrics with bootstrap CIs per approach, overall and per category,
the pre-registered McNemar tests with Holm correction, and the decision rule for the best approach.

    python -m src.eval.score --model vllm_llama8b --split dev

Reads results/<split>/<model>/raw.jsonl and the current gold labels in data/scenarios/<split>.jsonl; writes
scores.json, scores.csv and by_category.csv next to raw.jsonl. Rows with an error (e.g. parse_error) count as
wrong. Faithfulness (share of "yes", plus the yes/partly/no split) is read from judged.jsonl when src/eval/judge.py
has run; error rows and judge parse errors count as "no", rows not yet judged are left out.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.multitest import multipletests

from src.eval.run import RESULTS_DIR, load_scenarios

POSITIVE = {"covered", "partially_covered"}
AGENTS = ("A2", "A3", "A4")                       # agentic approaches eligible as "best agent"
# Added after the comparisons were pre-registered: scored and shown, but never in the Holm family or the decision rule
EXPLORATORY = ("L0",)
METRICS = ("verdict_accuracy", "binary_accuracy", "wrong_covered_rate", "clause_recall")
COSTS = ("latency_s", "model_calls", "prompt_tokens", "completion_tokens", "reasoning_tokens")
N_BOOT, SEED, ALPHA = 1000, 0, 0.05


def per_row(rows: list[dict], gold: dict, judged: dict | None = None) -> pd.DataFrame:
    """One record per (scenario, approach) with the per-scenario scores. judged: {(scenario_id, approach): label}."""
    judged = judged or {}
    out = []
    for r in rows:
        g = gold.get(r["scenario_id"], {"gold_verdict": r["gold_verdict"], "gold_sections": r["gold_sections"],
                                        "category": r["category"]})
        o = r["output"]
        ok = o.get("error") is None
        pred_pos = ok and o["verdict"] in POSITIVE
        cited, gs = set(o.get("cited_sections") or []), g["gold_sections"]
        key = (r["scenario_id"], r["approach"])
        faith = None if not judged else "no" if not ok else (judged[key] or "no") if key in judged else None
        out.append({"scenario_id": r["scenario_id"], "approach": r["approach"], "category": g["category"],
                    "gold": g["gold_verdict"], "pred": o["verdict"] if ok else "error",
                    "correct": float(ok and o["verdict"] == g["gold_verdict"]),
                    "binary_correct": float(ok and pred_pos == (g["gold_verdict"] in POSITIVE)),   # error = wrong
                    "wrong_covered": float(pred_pos) if g["gold_verdict"] == "not_covered" else np.nan,
                    "clause_recall": len(cited & set(gs)) / len(gs) if gs else np.nan,
                    "error": o.get("error"), "faith": faith,
                    "faithful": np.nan if faith is None else float(faith == "yes"),
                    **{c: float(o.get("usage", {}).get(c, 0)) for c in COSTS}})
    return pd.DataFrame(out)


def mean_ci(values, rng) -> tuple[float, float, float]:
    """Mean with a 95% percentile bootstrap CI (NaNs, e.g. not applicable rows, are dropped first)."""
    v = np.asarray([x for x in values if not np.isnan(x)], dtype=float)
    if len(v) == 0:
        return (np.nan, np.nan, np.nan)
    boots = rng.choice(v, size=(N_BOOT, len(v)), replace=True).mean(axis=1)
    return (float(v.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)))


def summarise(df: pd.DataFrame) -> dict:
    """Metrics (with CIs) and mean costs for one approach's rows."""
    rng = np.random.default_rng(SEED)
    cols = {"verdict_accuracy": "correct", "binary_accuracy": "binary_correct",
            "wrong_covered_rate": "wrong_covered", "clause_recall": "clause_recall", "faithfulness": "faithful"}
    res = {"n": int(len(df)), "errors": int(df["error"].notna().sum())}
    for m, c in cols.items():
        res[m], res[f"{m}_lo"], res[f"{m}_hi"] = mean_ci(df[c].to_numpy(), rng)
    for label in ("yes", "partly", "no"):
        res[f"faith_{label}"] = int((df["faith"] == label).sum())
    for c in COSTS:
        res[c] = float(df[c].mean())
    return res


def mcnemar_p(df: pd.DataFrame, a: str, b: str) -> dict:
    """Exact McNemar test on per-scenario correctness of approaches a and b (scenarios both have)."""
    pa = df[df.approach == a].set_index("scenario_id")["correct"]
    pb = df[df.approach == b].set_index("scenario_id")["correct"]
    both = pa.index.intersection(pb.index)
    pa, pb = pa[both], pb[both]
    only_a, only_b = int(((pa == 1) & (pb == 0)).sum()), int(((pa == 0) & (pb == 1)).sum())
    table = [[int(((pa == 1) & (pb == 1)).sum()), only_a], [only_b, int(((pa == 0) & (pb == 0)).sum())]]
    return {"a": a, "b": b, "n": int(len(both)), "only_a_right": only_a, "only_b_right": only_b,
            "p": float(mcnemar(table, exact=True).pvalue)}


def preregistered_tests(df: pd.DataFrame, overall: dict) -> list[dict]:
    """(1) best agent vs A0, (2) A0 vs B0, (3) A2 vs A4, plus best agent vs A1 if A1 ran; Holm-corrected."""
    have = set(overall)
    agents = [a for a in AGENTS if a in have]
    best = max(agents, key=lambda a: overall[a]["verdict_accuracy"]) if agents else None
    pairs = [(best, "A0", "best agent vs A0"), ("A0", "B0", "A0 vs B0"), ("A2", "A4", "A2 vs A4"),
             (best, "A1", "best agent vs A1")]
    tests = [dict(mcnemar_p(df, a, b), label=label) for a, b, label in pairs if a in have and b in have]
    if tests:
        reject, p_holm, *_ = multipletests([t["p"] for t in tests], alpha=ALPHA, method="holm")
        for t, r, ph in zip(tests, reject, p_holm):
            t.update(p_holm=float(ph), significant=bool(r))
    return tests


def exploratory_tests(df: pd.DataFrame, overall: dict) -> list[dict]:
    """L0 vs A0 and vs the best agent: McNemar p-values, not corrected and not part of the pre-registered family."""
    have = set(overall)
    agents = [a for a in AGENTS if a in have]
    best = max(agents, key=lambda a: overall[a]["verdict_accuracy"]) if agents else None
    return [dict(mcnemar_p(df, x, b), label=f"exploratory: {x} vs {label}")
            for x in EXPLORATORY if x in have
            for b, label in (("A0", "A0"), (best, "best agent")) if b in have]


def decide(df: pd.DataFrame, overall: dict) -> dict:
    """Brief section 9: highest verdict accuracy whose wrong_covered_rate is no worse than A0's; if McNemar does
    not separate the top two, the cheaper and faster one wins (fewer mean model calls, then lower latency).
    Exploratory setups (L0) are never candidates."""
    a0_wc = overall.get("A0", {}).get("wrong_covered_rate")
    eligible = [a for a, s in overall.items() if a not in EXPLORATORY
                and (a0_wc is None or np.isnan(a0_wc) or not s["wrong_covered_rate"] > a0_wc)]
    ranked = sorted(eligible, key=lambda a: -overall[a]["verdict_accuracy"])
    if not ranked:
        return {"winner": None, "reason": "no approach is eligible"}
    if len(ranked) == 1:
        return {"winner": ranked[0], "reason": "only eligible approach"}
    top, second = ranked[0], ranked[1]
    test = mcnemar_p(df, top, second)
    if test["p"] < ALPHA:
        return {"winner": top, "reason": f"most accurate; McNemar vs {second} p={test['p']:.3f}", "test": test}
    cheaper = min((top, second), key=lambda a: (overall[a]["model_calls"], overall[a]["latency_s"]))
    return {"winner": cheaper, "reason": f"{top} and {second} not separated (McNemar p={test['p']:.3f}); "
                                         f"{cheaper} is cheaper/faster", "test": test}


def score(rows: list[dict], gold: dict, judged: dict | None = None) -> tuple[dict, pd.DataFrame]:
    df = per_row(rows, gold, judged)
    overall = {a: summarise(g) for a, g in df.groupby("approach")}
    by_cat = pd.DataFrame([{"approach": a, "category": c, **summarise(g)}
                           for (a, c), g in df.groupby(["approach", "category"])])
    by_gold = {a: {v: {"n": int(len(g[g.gold == v])), "right": int(g[g.gold == v].correct.sum()),
                       "predicted": g[g.gold == v].pred.value_counts().to_dict()}
                   for v in ("covered", "not_covered", "partially_covered", "insufficient_info")}
               for a, g in df.groupby("approach")}
    result = {"overall": overall, "by_gold_verdict": by_gold, "tests": preregistered_tests(df, overall),
              "exploratory_tests": exploratory_tests(df, overall), "decision": decide(df, overall)}
    return result, by_cat


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
    gold = {s.id: {"gold_verdict": s.gold_verdict, "gold_sections": s.gold_sections, "category": s.category}
            for s in load_scenarios(args.split)}
    judged_path = out_dir / "judged.jsonl"
    judged = ({(j["scenario_id"], j["approach"]): j["faithfulness"]
               for j in map(json.loads, judged_path.open(encoding="utf-8"))} if judged_path.exists() else None)
    result, by_cat = score(rows, gold, judged)
    result.update(model=args.model, split=args.split, rows=len(rows), commits=sorted({r["commit"] for r in rows}))
    (out_dir / "scores.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    table = pd.DataFrame([{"approach": a, **s} for a, s in result["overall"].items()])
    table.to_csv(out_dir / "scores.csv", index=False)
    by_cat.to_csv(out_dir / "by_category.csv", index=False)

    print(f"{args.model} | {args.split} | {len(rows)} rows | commits {result['commits']}\n")
    for a, s in result["overall"].items():
        print(f"{a:3} acc {s['verdict_accuracy']:.2f} [{s['verdict_accuracy_lo']:.2f}-{s['verdict_accuracy_hi']:.2f}]"
              f"  binary {s['binary_accuracy']:.2f}  wrong-covered {s['wrong_covered_rate']:.2f}"
              f"  clause recall {s['clause_recall']:.2f}  | {s['model_calls']:.1f} calls, {s['latency_s']:.1f}s,"
              f" {s['prompt_tokens'] + s['completion_tokens']:.0f} tokens  (n={s['n']}, errors={s['errors']})"
              + (f"\n    faithfulness {s['faithfulness']:.2f} [{s['faithfulness_lo']:.2f}-{s['faithfulness_hi']:.2f}]"
                 f" yes/partly/no {s['faith_yes']}/{s['faith_partly']}/{s['faith_no']}" if judged else ""))
    for t in result["tests"]:
        print(f"McNemar {t['label']:18} {t['a']} vs {t['b']}: p={t['p']:.3f}, Holm p={t['p_holm']:.3f}"
              f"{' *' if t['significant'] else ''}  (only {t['a']} right {t['only_a_right']}, only {t['b']} right "
              f"{t['only_b_right']})")
    for t in result["exploratory_tests"]:
        print(f"McNemar {t['label']}: p={t['p']:.3f} (not corrected; only {t['a']} right {t['only_a_right']}, "
              f"only {t['b']} right {t['only_b_right']})")
    print("\nRight per gold verdict (and what was predicted instead):")
    for a, per in result["by_gold_verdict"].items():
        print(f"{a:3} " + " | ".join(
            f"{v} {s['right']}/{s['n']}" + (f" ({', '.join(f'{p} {k}' for p, k in s['predicted'].items() if p != v)})"
                                            if s["right"] < s["n"] else "")
            for v, s in per.items() if s["n"]))
    d = result["decision"]
    print(f"\nDecision rule: {d['winner']} ({d['reason']})"
          + ("" if args.split == "test" else "  [dev split: for tuning only, not the reported result]"))


if __name__ == "__main__":
    main()
