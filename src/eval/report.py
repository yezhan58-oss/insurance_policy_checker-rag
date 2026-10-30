"""Leaderboard and charts across both models (brief section 9).

    python -m src.eval.report --split test

Reads results/<split>/<model>/raw.jsonl for every model in configs/run.yaml (plus judged.jsonl and an optional
human error_types.csv with columns scenario_id, approach, error_type) and recomputes scores and trace metrics, so it
never shows stale numbers. Writes to results/<split>/report/:

    leaderboard.md / .csv     one row per approach x model, McNemar tests and the decision rule per model
    leaderboard.png           the same metrics as a heatmap table (darker = better within each column)
    accuracy_vs_latency.png   accuracy (95% CI) against mean seconds per claim; each model's approaches joined as a path
    accuracy_vs_tokens.png    the same against mean tokens per claim
    accuracy_by_category.png  heatmap of accuracy per scenario category, per model
    failures.png              wrong answers split into missing evidence / had evidence / error (from traces)
    process_outcomes.png      every answer by outcome and process: right from a working process (sound), right
                              without the evidence, wrong with / without the evidence, error (from traces)
    error_types.png           human error types per approach x model (only if error_types.csv exists)
"""
import argparse
import json
import sys

import pandas as pd
import yaml

from src.eval import charts, traces
from src.eval.charts import APPROACHES
from src.eval.run import RESULTS_DIR, ROOT, load_scenarios
from src.eval.score import score

SHORT = {"vllm_llama8b": "Llama 8B", "vllm_gptoss20b": "gpt-oss-20b"}


def load_model(split: str, model: str):
    d = RESULTS_DIR / split / model
    if not (d / "raw.jsonl").exists():
        return None
    rows = [json.loads(line) for line in (d / "raw.jsonl").open(encoding="utf-8") if line.strip()]
    scen = load_scenarios(split)
    gold = {s.id: {"gold_verdict": s.gold_verdict, "gold_sections": s.gold_sections, "category": s.category}
            for s in scen}
    judged_path = d / "judged.jsonl"
    judged = ({(j["scenario_id"], j["approach"]): j["faithfulness"]
               for j in map(json.loads, judged_path.open(encoding="utf-8"))} if judged_path.exists() else None)
    result, by_cat = score(rows, gold, judged)
    faith = traces.load_judged(d)
    tr = [traces.trace_row(r, gold[r["scenario_id"]], faith.get((r["scenario_id"], r["approach"]))) for r in rows]
    trace_summary = traces.summarise(tr, [s for r in rows for s in traces.step_rows(r, gold[r["scenario_id"]])])
    errors_path = d / "error_types.csv"
    error_types = pd.read_csv(errors_path) if errors_path.exists() else None
    return {"result": result, "by_cat": by_cat, "traces": trace_summary, "error_types": error_types,
            "commits": sorted({r["commit"] for r in rows})}


def leaderboard(data: dict) -> pd.DataFrame:
    out = []
    for model, d in data.items():
        for a, s in d["result"]["overall"].items():
            t = d["traces"][a]
            out.append({"model": SHORT.get(model, model), "approach": a, "n": s["n"], "errors": s["errors"],
                        "accuracy": s["verdict_accuracy"], "acc_lo": s["verdict_accuracy_lo"],
                        "acc_hi": s["verdict_accuracy_hi"], "binary_accuracy": s["binary_accuracy"],
                        "wrong_covered_rate": s["wrong_covered_rate"], "clause_recall": s["clause_recall"],
                        # faithfulness only once every row is judged: a partial judge run is not a result
                        "faithfulness": (s["faithfulness"] if s["faith_yes"] + s["faith_partly"] + s["faith_no"]
                                         == s["n"] else float("nan")),
                        "evidence_recall": t["evidence_recall"],
                        "model_calls": s["model_calls"], "tokens": s["prompt_tokens"] + s["completion_tokens"],
                        "latency_s": s["latency_s"], "missing_evidence": t["missing_evidence"],
                        "had_evidence": t["had_evidence"], "error_rows": t["error"],
                        "sound": t["sound"], "right_without_evidence": t["right_without_evidence"],
                        "sound_rate": t["sound_rate"], "grounded_rate": t["grounded_rate"],
                        "citation_valid_rate": t["citation_valid_rate"],
                        "citation_in_context_rate": t["citation_in_context_rate"]})
    df = pd.DataFrame(out)
    df["order"] = df.approach.map({a: i for i, a in enumerate(APPROACHES)})
    return df.sort_values(["model", "order"]).drop(columns="order")


def fmt(x) -> str:
    return "–" if pd.isna(x) else f"{x:.2f}"


def write_markdown(df: pd.DataFrame, data: dict, split: str, path) -> None:
    lines = [f"# Leaderboard ({split} split)", "",
             "| Model | Approach | Accuracy [95% CI] | Binary acc. | Wrong-covered | Clause recall | Faithfulness "
             "| Evidence recall | Sound rate | Grounded rate | Cites in context | Calls | Tokens | Seconds |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in df.itertuples():
        lines.append(f"| {r.model} | {r.approach} | {r.accuracy:.2f} [{r.acc_lo:.2f}–{r.acc_hi:.2f}] | "
                     f"{fmt(r.binary_accuracy)} | {fmt(r.wrong_covered_rate)} | {fmt(r.clause_recall)} | "
                     f"{fmt(r.faithfulness)} | {fmt(r.evidence_recall)} | {fmt(r.sound_rate)} | "
                     f"{fmt(r.grounded_rate)} | {fmt(r.citation_in_context_rate)} | {r.model_calls:.1f} | {r.tokens:.0f} | "
                     f"{r.latency_s:.1f} |")
    for model, d in data.items():
        lines += ["", f"## {SHORT.get(model, model)} (commits {', '.join(d['commits'])})", ""]
        for t in d["result"]["tests"]:
            lines.append(f"- McNemar {t['label']}: {t['a']} vs {t['b']}, p = {t['p']:.3f}, Holm p = {t['p_holm']:.3f}"
                         f"{' (significant)' if t['significant'] else ''}; only {t['a']} right {t['only_a_right']}, "
                         f"only {t['b']} right {t['only_b_right']}")
        dec = d["result"]["decision"]
        lines.append(f"- Decision rule: **{dec['winner']}** ({dec['reason']})")
    lines += ["", "_Cites in context: share of cited section IDs that exist in the policy and were in the model's "
              "context (checked in code, no judge)._"]
    lines += ["", "_Sound rate: share of all claims answered right with every gold section in the model's context. "
              "Grounded rate: sound and the judge found the explanation faithful (shown once every row is judged). "
              "Right answers without the evidence are not counted by either._"]
    if split != "test":
        lines += ["", "_Dev split: for tuning only, not the reported result._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    args = ap.parse_args()
    models = yaml.safe_load((ROOT / "configs" / "run.yaml").read_text(encoding="utf-8"))["models"]
    data = {m: d for m in models if (d := load_model(args.split, m))}
    if not data:
        sys.exit(f"No results under {RESULTS_DIR / args.split}")
    out = RESULTS_DIR / args.split / "report"
    out.mkdir(parents=True, exist_ok=True)

    df = leaderboard(data)
    df.to_csv(out / "leaderboard.csv", index=False)
    write_markdown(df, data, args.split, out / "leaderboard.md")
    charts.heat_leaderboard(df, out / "leaderboard.png")
    charts.frontier(df, "latency_s", "Mean seconds per claim", out / "accuracy_vs_latency.png")
    charts.frontier(df, "tokens", "Mean tokens per claim (prompt + completion)", out / "accuracy_vs_tokens.png")
    charts.category_heat({SHORT.get(m, m): d["by_cat"] for m, d in data.items()}, out / "accuracy_by_category.png")
    charts.failures(df, out / "failures.png")
    charts.process_outcomes(df, out / "process_outcomes.png")
    et = [d["error_types"].assign(model=SHORT.get(m, m)) for m, d in data.items() if d["error_types"] is not None]
    if et:
        counts = pd.concat(et).groupby(["approach", "model", "error_type"]).size().unstack(fill_value=0).reset_index()
        charts.error_types(counts, out / "error_types.png")
    print((out / "leaderboard.md").read_text(encoding="utf-8"))
    print(f"Charts and tables in {out}")


if __name__ == "__main__":
    main()
