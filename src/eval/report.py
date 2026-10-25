"""Leaderboard and charts across both models (brief section 9).

    python -m src.eval.report --split test

Reads results/<split>/<model>/raw.jsonl for every model in configs/run.yaml (plus judged.jsonl and an optional
human error_types.csv with columns scenario_id, approach, error_type) and recomputes scores and trace metrics, so it
never shows stale numbers. Writes to results/<split>/report/:

    leaderboard.md / .csv     one row per approach x model, McNemar tests and the decision rule per model
    accuracy_vs_latency.png   accuracy (95% CI) against mean seconds per claim, one point per approach x model
    accuracy_vs_tokens.png    the same against mean tokens per claim
    accuracy_by_category.png  accuracy per scenario category, one panel per model
    failures.png              wrong answers split into missing evidence / had evidence / error (from traces)
    error_types.png           human error types per approach x model (only if error_types.csv exists)
"""
import argparse
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

from src.eval import traces  # noqa: E402
from src.eval.run import RESULTS_DIR, ROOT, load_scenarios  # noqa: E402
from src.eval.score import score  # noqa: E402

APPROACHES = ["B0", "A0", "A2", "A4"]
COLORS = {"B0": "#2a78d6", "A0": "#eb6834", "A2": "#1baf7a", "A4": "#eda100"}   # validated categorical order
MARKERS = ["o", "s", "^", "D"]
SHORT = {"vllm_llama8b": "Llama 8B", "vllm_gptoss20b": "gpt-oss-20b"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def style(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


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
    tr = [traces.trace_row(r, gold[r["scenario_id"]]) for r in rows]
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
                        "had_evidence": t["had_evidence"], "error_rows": t["error"]})
    df = pd.DataFrame(out)
    df["order"] = df.approach.map({a: i for i, a in enumerate(APPROACHES)})
    return df.sort_values(["model", "order"]).drop(columns="order")


def fmt(x) -> str:
    return "–" if pd.isna(x) else f"{x:.2f}"


def write_markdown(df: pd.DataFrame, data: dict, split: str, path) -> None:
    lines = [f"# Leaderboard ({split} split)", "",
             "| Model | Approach | Accuracy [95% CI] | Binary acc. | Wrong-covered | Clause recall | Faithfulness "
             "| Evidence recall | Calls | Tokens | Seconds |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in df.itertuples():
        lines.append(f"| {r.model} | {r.approach} | {r.accuracy:.2f} [{r.acc_lo:.2f}–{r.acc_hi:.2f}] | "
                     f"{fmt(r.binary_accuracy)} | {fmt(r.wrong_covered_rate)} | {fmt(r.clause_recall)} | "
                     f"{fmt(r.faithfulness)} | {fmt(r.evidence_recall)} | {r.model_calls:.1f} | {r.tokens:.0f} | "
                     f"{r.latency_s:.1f} |")
    for model, d in data.items():
        lines += ["", f"## {SHORT.get(model, model)} (commits {', '.join(d['commits'])})", ""]
        for t in d["result"]["tests"]:
            lines.append(f"- McNemar {t['label']}: {t['a']} vs {t['b']}, p = {t['p']:.3f}, Holm p = {t['p_holm']:.3f}"
                         f"{' (significant)' if t['significant'] else ''}; only {t['a']} right {t['only_a_right']}, "
                         f"only {t['b']} right {t['only_b_right']}")
        dec = d["result"]["decision"]
        lines.append(f"- Decision rule: **{dec['winner']}** ({dec['reason']})")
    if split != "test":
        lines += ["", "_Dev split: for tuning only, not the reported result._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scatter(df: pd.DataFrame, x: str, xlabel: str, path) -> None:
    """One panel per model (shared axes), so each point is labelled with just its approach."""
    models = list(dict.fromkeys(df.model))
    fig, axes = plt.subplots(1, len(models), figsize=(4.6 * len(models), 3.8), dpi=200, sharey=True,
                             squeeze=False)
    for ax, model in zip(axes[0], models):
        style(ax)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        sub = df[df.model == model].sort_values(x)
        for k, r in enumerate(sub.itertuples()):
            ax.errorbar(getattr(r, x), r.accuracy, yerr=[[r.accuracy - r.acc_lo], [r.acc_hi - r.accuracy]],
                        fmt="none", ecolor=COLORS[r.approach], elinewidth=1, alpha=0.5, capsize=0)
            ax.scatter(getattr(r, x), r.accuracy, s=60, color=COLORS[r.approach], edgecolor="white", linewidth=2,
                       zorder=3)
            dy = 8 if k % 2 == 0 else -14            # alternate above / below so close points stay readable
            ax.annotate(f"{r.approach} {r.accuracy:.2f}", (getattr(r, x), r.accuracy), xytext=(6, dy),
                        textcoords="offset points", fontsize=8, color=INK)
        ax.set_title(model, fontsize=10, color=INK, loc="left")
        ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
        ax.set_ylim(0, 1)
        ax.set_xlim(0, df[x].max() * 1.15)        # same x range on both panels, nothing clipped
    axes[0][0].set_ylabel("Verdict accuracy (95% CI)", color=MUTED, fontsize=9)
    handles = [plt.Line2D([], [], marker="o", ls="", color=COLORS[a], label=a) for a in APPROACHES if a in set(df.approach)]
    fig.legend(handles=handles, frameon=False, fontsize=8, ncol=len(handles), loc="upper right")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path)
    plt.close(fig)


def by_category(data: dict, path) -> None:
    fig, axes = plt.subplots(1, len(data), figsize=(5.2 * len(data), 3.8), dpi=200, sharey=True, squeeze=False)
    for ax, (model, d) in zip(axes[0], data.items()):
        style(ax)
        bc = d["by_cat"]
        cats = sorted(bc.category.unique())
        present = [a for a in APPROACHES if a in set(bc.approach)]
        w = 0.8 / len(present)
        for i, a in enumerate(present):
            vals = [bc[(bc.approach == a) & (bc.category == c)].verdict_accuracy.mean() for c in cats]
            xs = [j + i * w for j in range(len(cats))]
            ax.bar(xs, vals, width=w * 0.92, color=COLORS[a], label=a if ax is axes[0][0] else None,
                   edgecolor="white", linewidth=1)
            for xx, v in zip(xs, vals):
                if v == 0:                                       # a zero bar is invisible: say so
                    ax.text(xx, 0.01, "0", ha="center", va="bottom", fontsize=7, color=MUTED)
        ns = [int(bc[bc.category == c].n.max()) for c in cats]
        ax.set_xticks([j + 0.4 - w / 2 for j in range(len(cats))])
        ax.set_xticklabels([f"{c.replace('_', ' ')}\n(n={n})" for c, n in zip(cats, ns)], fontsize=8)
        ax.set_title(SHORT.get(model, model), fontsize=10, color=INK, loc="left")
        ax.set_ylim(0, 1)
    axes[0][0].set_ylabel("Verdict accuracy", color=MUTED, fontsize=9)
    fig.legend(frameon=False, fontsize=8, ncol=len(APPROACHES), loc="upper right")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path)
    plt.close(fig)


def stacked(df: pd.DataFrame, cols: list[str], labels: list[str], colors: list[str], xlabel: str, path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(df) + 1.2), dpi=200)
    style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    names = [f"{r.approach} · {r.model}" for r in df.itertuples()]
    left = [0] * len(df)
    for col, label, color in zip(cols, labels, colors):
        vals = list(df[col])
        ax.barh(names, vals, left=left, color=color, label=label, edgecolor="white", linewidth=2, height=0.7)
        for y, (l, v) in enumerate(zip(left, vals)):
            if v:
                ax.text(l + v / 2, y, str(int(v)), ha="center", va="center", fontsize=8,
                        color="white" if color != "#b9b8b2" else INK)
        left = [a + b for a, b in zip(left, vals)]
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    fig.legend(frameon=False, fontsize=8, ncol=min(len(cols), 3), loc="upper center")
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.5 / (0.42 * len(df) + 1.2)))
    fig.savefig(path)
    plt.close(fig)


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
    scatter(df, "latency_s", "Mean seconds per claim", out / "accuracy_vs_latency.png")
    scatter(df, "tokens", "Mean tokens per claim (prompt + completion)", out / "accuracy_vs_tokens.png")
    by_category(data, out / "accuracy_by_category.png")
    stacked(df, ["missing_evidence", "had_evidence", "error_rows"],
            ["Needed section never reached the model", "Had the evidence, still wrong", "No answer (error)"],
            ["#52514e", "#8a8984", "#b9b8b2"], "Wrong answers", out / "failures.png")
    et = [d["error_types"].assign(model=SHORT.get(m, m)) for m, d in data.items() if d["error_types"] is not None]
    if et:
        counts = pd.concat(et).groupby(["approach", "model", "error_type"]).size().unstack(fill_value=0).reset_index()
        types = [c for c in counts.columns if c not in ("approach", "model")]
        greys = ["#2b2b2a", "#52514e", "#6e6d69", "#8a8984", "#a3a29d", "#b9b8b2", "#d0cfca"][:len(types)]
        stacked(counts, types, types, greys, "Wrong answers by error type", out / "error_types.png")
    print((out / "leaderboard.md").read_text(encoding="utf-8"))
    print(f"Charts and tables in {out}")


if __name__ == "__main__":
    main()
