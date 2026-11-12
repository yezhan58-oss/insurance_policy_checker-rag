"""Figure 1: the study pipeline, drawn with matplotlib (no Graphviz needed).

    python docs/figures/make_architecture.py      -> docs/figures/architecture.png

Replaces the wide Graphviz version (architecture*.dot, 4 Nov): report names instead of codes, ReAct in the main
comparison, the baselines / agentic RAG grouping, and the current demo. Laid out about 5:4 so it reads at report width.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

INK, MUTED, LINE = "#1B2633", "#55606C", "#8A939C"
FILL, PANEL, AGENTIC, BASE = "#F2F2F2", "#FFFFFF", "#E5ECF3", "#F4EFE6"
plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]

fig, ax = plt.subplots(figsize=(9, 7.2))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, title, body="", size=9.5, t_off=1.6, b_off=5.2):
    """A rounded box with a bold title and an optional grey description under it."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.6", fc=FILL, ec=INK, lw=1.0))
    if body:
        ax.text(x + w / 2, y + h - t_off, title, ha="center", va="top", fontsize=size, color=INK, fontweight="bold")
        ax.text(x + w / 2, y + h - b_off, body, ha="center", va="top", fontsize=size - 1.3, color=MUTED,
                linespacing=1.35)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=size, color=INK, fontweight="bold")


def group(x, y, w, h, fill):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.5", fc=fill, ec="none"))


def arrow(p, q, label="", both=False, lx=0.0, ly=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=11, lw=1.1,
                                 color=MUTED, shrinkA=2, shrinkB=2))
    if label:
        ax.text((p[0] + q[0]) / 2 + lx, (p[1] + q[1]) / 2 + ly, label, ha="center", va="center", fontsize=7.8,
                color=MUTED, style="italic", bbox=dict(fc="white", ec="none", pad=0.6))


# row 1: data and index
box(3, 86, 27, 11, "Policy PDFs", "FWD and MSIG wordings")
box(36.5, 86, 27, 11, "Ingestion", "split by headings into sections\nwith stable IDs, then chunks")
box(70, 86, 27, 11, "Index", "Chroma, bge-small (CPU)\n+ defined-terms lookup")
arrow((30, 91.5), (36.5, 91.5))
arrow((63.5, 91.5), (70, 91.5))
box(3, 72.5, 27, 9, "Claim", "124 test, 20 dev")

# row 2: the setups
ax.add_patch(FancyBboxPatch((3, 37), 94, 32, boxstyle="round,pad=0,rounding_size=2", fc=PANEL, ec=LINE, lw=1.2))
ax.text(50, 67.1, "Setups: same index, prompt and answer step; only how they find policy text differs",
        ha="center", va="center", fontsize=9, color=INK, fontweight="bold")
small = dict(size=9, t_off=1.3, b_off=4.6)
group(5, 43, 31, 22, BASE)
ax.text(20.5, 63.2, "BASELINES", ha="center", va="center", fontsize=7.8, color=MUTED, fontweight="bold")
box(7, 53, 27, 8.6, "No-RAG", "no policy text", **small)
box(7, 44, 27, 8.6, "RAG", "one search, top 5 chunks", **small)
group(38, 43, 57, 22, AGENTIC)
ax.text(66.5, 63.2, "AGENTIC RAG  (the model makes retrieval decisions)", ha="center", va="center", fontsize=7.8,
        color="#2F4A66", fontweight="bold")
box(40, 53, 26, 8.6, "CRAG", "grade chunks, rewrite search", **small)
box(67.5, 53, 25.5, 8.6, "Agent", "benefits → definitions → exclusions", **small)
box(40, 44, 53, 8.6, "ReAct", "picks its own lookups, one at a time (max 8)", **small)
ax.text(50, 39.8, "Exploratory extras, outside the winner rule: Full-context (whole policy in the prompt), "
        "Agent-Pick, RAG-10, safe mode", ha="center", va="center", fontsize=7.8, color=MUTED, style="italic")
arrow((16.5, 72.5), (16.5, 69))
arrow((83.5, 86), (83.5, 69), "sections and chunks", ly=4.2)

# row 3: model, output, judge
box(3, 20, 27, 12, "Model (vLLM, SMU cluster)", "Llama 3.1 8B\ngpt-oss-20b")
box(36.5, 20, 27, 12, "Verdict output", "verdict, cited sections,\nexplanation, steps, usage")
box(70, 20, 27, 12, "Claude Haiku judge", "faithfulness of the\nexplanation to the cited text")
arrow((16.5, 32), (16.5, 37), "prompt / answer", both=True, lx=9.5)
arrow((50, 37), (50, 32))
arrow((63.5, 26), (70, 26))

# row 4: scoring and the demo
box(3, 1, 27, 14, "Gold labels", "verdict and deciding\nsections, human-checked")
box(36.5, 1, 27, 14, "Scoring", "accuracy, wrong \"covered\",\nclause recall, significance\ntests, trace metrics")
box(70, 1, 27, 14, "Demo: \"Am I covered?\"", "the four methods side by side,\nwith guardrails")
arrow((30, 8), (36.5, 8))
arrow((50, 20), (50, 15))
arrow((83.5, 20), (60, 15))
arrow((63.5, 8), (70, 8))

out_path = Path(__file__).with_name("architecture.png")
fig.savefig(out_path, dpi=200, bbox_inches="tight", pad_inches=0.08, facecolor="white")
print(out_path)
