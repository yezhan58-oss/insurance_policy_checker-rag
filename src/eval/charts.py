"""Charts for src/eval/report.py. Colors: the approach palette and the two failure colors passed a colorblind-safety
check; heatmaps use one blue hue from light to dark; every value is also printed, so nothing relies on color alone."""
import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

APPROACHES = ["B0", "L0", "A0", "A0K10", "A2", "A3", "A4", "A4D"]   # exploratory ones only if they were run
# A3 and A4D (added 4-5 Nov) are outside the validated set; values are printed on every chart, so color is never the only cue
COLORS = {"B0": "#2a78d6", "A0": "#eb6834", "A2": "#1baf7a", "A4": "#eda100", "L0": "#4a3aa7", "A3": "#c4327f", "A4D": "#8a6d00",
          "A0K10": "#9c4a1f"}
# Names shown on the charts (the report's names); results files and code keep the IDs
NAMES = {"B0": "No-RAG", "A0": "RAG", "A2": "CRAG", "A4": "Agent", "L0": "Full-context", "A3": "ReAct",
         "A4D": "Agent-Pick", "A0K10": "RAG-10"}
# Hand-placed labels (points from the dot, alignment) where the defaults collide; key (approach, model index), model 0 =
# the first model in the leaderboard. Everything else sits above its dot.
LABEL_AT = {"tokens": {("A0", 0): (0, -20, "center"), ("A2", 0): (0, -44, "center"), ("A4", 0): (-6, -16, "right"),
                       ("B0", 1): (0, -20, "center"), ("A2", 1): (12, 4, "left"),
                       ("A4", 1): (12, -3, "left")},
            "latency_s": {("A0", 0): (0, -20, "center"), ("L0", 0): (0, -20, "center"), ("B0", 1): (0, -20, "center"),
                          ("A4", 1): (-10, -3, "right")}}
MARKERS = ["o", "s", "^", "D"]
INK, MUTED, GRID, EMPTY = "#0b0b0b", "#52514e", "#e4e3df", "#f3f2ef"
BLUES = ["#eef5fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"]     # light -> dark
FAIL_COLORS = {"missing_evidence": "#6250d6", "had_evidence": "#e87ba4"}
RIGHT_COLORS = {"sound": "#008300", "right_without_evidence": "#5fb563"}   # validated with FAIL_COLORS as one set
METRICS = [("accuracy", "Accuracy", True), ("binary_accuracy", "Binary\naccuracy", True),
           ("wrong_covered_rate", "Wrong-\ncovered", False), ("clause_recall", "Clause\nrecall", True),
           ("evidence_recall", "Evidence\nrecall", True), ("sound_rate", "Sound\nrate", True),
           ("faithfulness", "Faithful-\nness", True),
           ("latency_s", "Seconds\nper claim", False), ("tokens", "Tokens\nper claim", False)]


def style(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def blue(v: float) -> str:
    return BLUES[min(max(int(v * len(BLUES)), 0), len(BLUES) - 1)]


def cell(ax, x, y, v, text, bold=False) -> None:
    """One heatmap cell; v in 0..1 sets the shade, None draws an empty cell."""
    ax.add_patch(plt.Rectangle((x + 0.04, y + 0.06), 0.92, 0.88, color=EMPTY if v is None else blue(v), lw=0))
    dark = v is not None and v >= 4 / len(BLUES)
    ax.text(x + 0.5, y + 0.5, text, ha="center", va="center", fontsize=8.5, color="white" if dark else INK,
            fontweight="bold" if bold else "normal")


def heat_leaderboard(df: pd.DataFrame, path) -> None:
    """Every metric for every approach x model; shade = how good within the column (darker = better)."""
    cols = [m for m in METRICS if df[m[0]].notna().any()]
    rows = list(df.itertuples())
    fig, ax = plt.subplots(figsize=(1.0 * len(cols) + 2.4, 0.46 * len(rows) + 1.2), dpi=200)
    ax.set_xlim(-2.2, len(cols))
    ax.set_ylim(len(rows), -0.9)
    ax.axis("off")
    for j, (col, label, higher) in enumerate(cols):
        vals = df[col].astype(float)
        lo, hi = vals.min(), vals.max()
        ax.text(j + 0.5, -0.1, label, ha="center", va="bottom", fontsize=8, color=MUTED)
        for i, r in enumerate(rows):
            v = getattr(r, col)
            if pd.isna(v):
                cell(ax, j, i, None, "–")
                continue
            good = 0.5 if hi == lo else ((v - lo) if higher else (hi - v)) / (hi - lo)
            text = f"{v:.0f}" if col == "tokens" else f"{v:.1f}" if col == "latency_s" else f"{v:.2f}"
            cell(ax, j, i, good, text, bold=good == 1)
    for i, r in enumerate(rows):
        ax.text(-0.12, i + 0.5, NAMES.get(r.approach, r.approach), ha="right", va="center", fontsize=9, color=INK, fontweight="bold")
        if i == 0 or rows[i - 1].model != r.model:
            ax.text(-0.75, i + 0.5, r.model, ha="right", va="center", fontsize=8.5, color=MUTED)
            if i:
                ax.plot([-2.2, len(cols)], [i, i], color=MUTED, lw=0.8)
    ax.text(len(cols), len(rows) + 0.25, "Shade within each column: darker = better "
            "(for seconds, tokens and wrong-covered, lower is better).", ha="right", va="top", fontsize=7, color=MUTED)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def frontier(df: pd.DataFrame, x: str, xlabel: str, path) -> None:
    """Accuracy against cost; each model's approaches joined in order of cost, so the trade-off reads as a path.
    The main comparison (B0, A0, A2, A4, ReAct) plus Full-context (L0); the smaller exploratory variants are
    reported in the tables, and their labels made the middle of the chart unreadable."""
    df = df[df.approach.isin(["B0", "L0", "A0", "A2", "A4", "A3"])]
    models = list(dict.fromkeys(df.model))
    fig, ax = plt.subplots(figsize=(6.6, 4.2), dpi=200)
    style(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    for k, model in enumerate(models):
        sub = df[df.model == model].sort_values(x)
        ax.plot(sub[x], sub.accuracy, color=MUTED, lw=1, ls="-" if k == 0 else "--", zorder=1)
        last = sub.iloc[-1]
        ax.annotate(model, (last[x], last.accuracy), xytext=(12, 0), textcoords="offset points", fontsize=8,
                    color=MUTED, va="center", style="italic")
        for n, r in enumerate(sub.itertuples()):
            ax.vlines(getattr(r, x), r.acc_lo, r.acc_hi, color=COLORS[r.approach], lw=1.2, alpha=0.35, zorder=1)
            ax.scatter(getattr(r, x), r.accuracy, s=130, marker=MARKERS[k], color=COLORS[r.approach],
                       edgecolor="white", linewidth=2, zorder=3)
            dx, dy, ha = LABEL_AT.get(x, {}).get((r.approach, k), (0, 11 if n % 2 == 0 or x in LABEL_AT else -18,
                                                                    "center"))
            ax.annotate(f"{NAMES.get(r.approach, r.approach)} {r.accuracy:.2f}", (getattr(r, x), r.accuracy),
                        xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=7.5, color=INK,
                        fontweight="bold", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6) if abs(dy) > 30 else None)
    lo, hi = df[x].min(), df[x].max()
    if lo > 0 and hi / lo > 8:          # e.g. L0's whole-policy prompts: a linear axis would squash the rest together
        ax.set_xscale("log")
        ax.set_xlim(lo / 1.6, hi * 2.2)
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())   # plain numbers, no crowded 3x10^0 labels
        xlabel += " (log scale)"
    else:
        ax.set_xlim(0, hi * 1.35)
    ax.set_ylim(0, 1)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    ax.set_ylabel("Verdict accuracy (faint lines: 95% CI)", color=MUTED, fontsize=9)
    handles = [plt.Line2D([], [], marker="o", ls="", ms=8, color=COLORS[a], label=NAMES.get(a, a))
               for a in APPROACHES if a in set(df.approach)]
    handles += [plt.Line2D([], [], marker=MARKERS[k], ls="-" if k == 0 else "--", ms=7, color=MUTED, label=m)
                for k, m in enumerate(models)]
    ax.legend(handles=handles, frameon=False, fontsize=8, ncol=3, loc="lower right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def category_heat(by_cat: dict, path) -> None:
    """Accuracy per scenario category: approaches down, categories across, one panel per model (shade = 0..1)."""
    fig, axes = plt.subplots(1, len(by_cat), figsize=(4.4 * len(by_cat), 2.8), dpi=200, squeeze=False)
    for ax, (model, bc) in zip(axes[0], by_cat.items()):
        cats = sorted(bc.category.unique())
        present = [a for a in APPROACHES if a in set(bc.approach)]
        ax.set_xlim(-0.6, len(cats))
        ax.set_ylim(len(present), -0.9)
        ax.axis("off")
        for j, c in enumerate(cats):
            n = int(bc[bc.category == c].n.max())
            ax.text(j + 0.5, -0.05, f"{c.replace('_', ' ')}\nn={n}", ha="center", va="bottom", fontsize=7.5,
                    color=MUTED)
            for i, a in enumerate(present):
                v = bc[(bc.approach == a) & (bc.category == c)].verdict_accuracy.mean()
                cell(ax, j, i, v, f"{v:.2f}")
        for i, a in enumerate(present):
            ax.text(-0.08, i + 0.5, NAMES.get(a, a), ha="right", va="center", fontsize=9, color=INK, fontweight="bold")
        ax.set_title(model, fontsize=10, color=INK, loc="left")
    fig.text(0.99, 0.0, "Shade = verdict accuracy (white 0, dark blue 1). Few scenarios per cell: read with care.",
             ha="right", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def failures(df: pd.DataFrame, path) -> None:
    """Why answers were wrong (from the traces): never got the needed section, or had it and still erred."""
    rows = list(df.itertuples())
    height = 0.42 * len(rows) + 1.4
    fig, ax = plt.subplots(figsize=(6.6, height), dpi=200)
    style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    names = [f"{NAMES.get(r.approach, r.approach)}  {r.model}" for r in rows]
    parts = [("missing_evidence", "Needed section never reached the model"),
             ("had_evidence", "Had the evidence, still wrong"), ("error_rows", "No answer (error)")]
    left = [0] * len(rows)
    for col, label in parts:
        vals = [getattr(r, col) for r in rows]
        if col in FAIL_COLORS:
            ax.barh(names, vals, left=left, label=label, height=0.66, color=FAIL_COLORS[col], linewidth=0)
        else:
            ax.barh(names, vals, left=left, label=label, height=0.66, color="white", hatch="////",
                    edgecolor=MUTED, linewidth=0.6)
        for y, (l, v) in enumerate(zip(left, vals)):
            if v and col in FAIL_COLORS:
                ax.text(l + v / 2, y, str(int(v)), ha="center", va="center", fontsize=8,
                        color="white" if col == "missing_evidence" else INK)
        left = [a + b for a, b in zip(left, vals)]
    for y, total in enumerate(left):
        ax.text(total + 0.15, y, f"{int(total)} wrong", va="center", fontsize=7.5, color=MUTED)
    for y in range(1, len(rows)):
        if rows[y].model != rows[y - 1].model:
            ax.axhline(y - 0.5, color=MUTED, lw=0.8)
    ax.invert_yaxis()
    ax.set_xlim(0, max(left) * 1.2)
    ax.set_xlabel("Wrong answers", color=MUTED, fontsize=9)
    fig.legend(frameon=False, fontsize=8, ncol=3, loc="upper center")
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.55 / height))
    fig.savefig(path)
    plt.close(fig)


def process_outcomes(df: pd.DataFrame, path) -> None:
    """Every answer by outcome and process, so a right verdict from a broken process is not credited as success:
    right with the evidence (sound), right without it (hatched), wrong with / without it, and errors."""
    rows = list(df.itertuples())
    height = 0.42 * len(rows) + 1.6
    fig, ax = plt.subplots(figsize=(7.2, height), dpi=200)
    style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    names = [f"{NAMES.get(r.approach, r.approach)}  {r.model}" for r in rows]
    parts = [("sound", "Right, evidence reached the model"), ("right_without_evidence", "Right without the evidence"),
             ("had_evidence", "Wrong, had the evidence"), ("missing_evidence", "Wrong, evidence never reached it"),
             ("error_rows", "No answer (error)")]
    colors = {**RIGHT_COLORS, **FAIL_COLORS}
    left = [0] * len(rows)
    for col, label in parts:
        vals = [getattr(r, col) for r in rows]
        style_kw = (dict(color="white", hatch="////", edgecolor=MUTED, linewidth=0.6) if col == "error_rows" else
                    dict(color=colors[col], hatch="////" if col == "right_without_evidence" else None,
                         edgecolor="white", linewidth=0.6 if col == "right_without_evidence" else 0))
        ax.barh(names, vals, left=left, label=label, height=0.66, **style_kw)
        for y, (l, v) in enumerate(zip(left, vals)):
            if v and col != "error_rows":
                ax.text(l + v / 2, y, str(int(v)), ha="center", va="center", fontsize=8,
                        color="white" if col in ("sound", "missing_evidence") else INK,
                        bbox=None if col != "right_without_evidence" else
                        dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
        left = [a + b for a, b in zip(left, vals)]
    for y, r in enumerate(rows):
        ax.text(left[y] + 0.4, y, f"sound {r.sound_rate:.0%}", va="center", fontsize=7.5, color=MUTED)
    for y in range(1, len(rows)):
        if rows[y].model != rows[y - 1].model:
            ax.axhline(y - 0.5, color=MUTED, lw=0.8)
    ax.invert_yaxis()
    ax.set_xlim(0, max(left) * 1.18)
    ax.set_xlabel("Claims", color=MUTED, fontsize=9)
    fig.legend(frameon=False, fontsize=7.5, ncol=3, loc="upper center")
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.6 / height))
    fig.savefig(path)
    plt.close(fig)


def error_types(counts: pd.DataFrame, path) -> None:
    """Human error types stacked per approach x model, most common type darkest."""
    types = sorted([c for c in counts.columns if c not in ("approach", "model")], key=lambda c: -counts[c].sum())
    height = 0.42 * len(counts) + 1.6
    fig, ax = plt.subplots(figsize=(6.6, height), dpi=200)
    style(ax)
    ax.grid(axis="y", visible=False)
    names = [f"{NAMES.get(r.approach, r.approach)}  {r.model}" for r in counts.itertuples()]
    left = [0] * len(counts)
    for typ, color in zip(types, BLUES[::-1]):
        vals = list(counts[typ])
        ax.barh(names, vals, left=left, color=color, label=typ.replace("_", " "), height=0.66, edgecolor="white",
                linewidth=1.5)
        left = [a + b for a, b in zip(left, vals)]
    ax.invert_yaxis()
    ax.set_xlabel("Wrong answers by error type", color=MUTED, fontsize=9)
    fig.legend(frameon=False, fontsize=7.5, ncol=3, loc="upper center")
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.8 / height))
    fig.savefig(path)
    plt.close(fig)
