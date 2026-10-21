"""Blind check of the gold labels (brief section 6, step 5): Member A labels 40 test scenarios without seeing
Member B's labels, then Cohen's kappa measures how often the two agree beyond chance.

    python -m src.eval.agreement sheet    # write the blank sheet (40 random test scenarios) and the section-ID list
    python -m src.eval.agreement          # after filling the sheet: check it, write blind_A.jsonl, report kappa

The sheet (data/scenarios/blind_A_sheet.csv) shows only id, policy and claim text, never the drafts' or B's
labels. Fill in `verdict`, `sections` (section IDs separated by ";", as in data/scenarios/section_ids.csv) and
optionally `note`. Scoring refuses an incomplete sheet, so B's labels are only shown once all 40 are done.
Kappa is reported 4-way and binary (covered or partially_covered vs the rest), with 95% bootstrap CIs.
"""
import argparse
import csv
import json
import random
import sys

import numpy as np

from src import store
from src.eval.run import SCEN_DIR, load_scenarios
from src.eval.score import N_BOOT, POSITIVE, SEED

VERDICTS = ("covered", "not_covered", "partially_covered", "insufficient_info")
N_BLIND = 40
SHEET = SCEN_DIR / "blind_A_sheet.csv"
SECTION_LIST = SCEN_DIR / "section_ids.csv"
BLIND = SCEN_DIR / "blind_A.jsonl"
DISAGREEMENTS = SCEN_DIR / "blind_A_disagreements.csv"
SHEET_COLS = ["id", "policy", "scenario", "verdict", "sections", "note"]


def cohen_kappa(a: list[str], b: list[str]) -> float:
    """Agreement beyond chance: (observed - expected) / (1 - expected); nan if chance agreement is already 1."""
    labels = sorted(set(a) | set(b))
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return float("nan") if expected == 1 else (observed - expected) / (1 - expected)


def kappa_ci(a: list[str], b: list[str]) -> tuple[float, float, float]:
    """Kappa with a 95% percentile bootstrap CI over scenarios (resamples where kappa is undefined are dropped)."""
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, len(a), len(a))
        k = cohen_kappa([a[i] for i in idx], [b[i] for i in idx])
        if not np.isnan(k):
            boots.append(k)
    return cohen_kappa(a, b), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def binary(v: str) -> str:
    return "pay" if v in POSITIVE else "no_pay"


def make_sheet() -> None:
    if SHEET.exists():
        sys.exit(f"{SHEET.name} already exists; delete it first only if you really want a new sample.")
    test = load_scenarios("test")
    picked = sorted(random.Random(SEED).sample(sorted(s.id for s in test), N_BLIND))
    by_id = {s.id: s for s in test}
    with SHEET.open("w", encoding="utf-8-sig", newline="") as f:      # utf-8-sig so Excel shows S$ and quotes right
        w = csv.writer(f)
        w.writerow(SHEET_COLS)
        for i in picked:
            w.writerow([i, by_id[i].policy, by_id[i].scenario, "", "", ""])
    with SECTION_LIST.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["section_id", "type", "title", "page"])
        for policy in ("fwd", "msig"):
            for c in store.list_sections(policy):
                w.writerow([c.section_id, c.type, c.title, c.page])
    print(f"Wrote {SHEET} ({N_BLIND} scenarios) and {SECTION_LIST}.")


def read_sheet() -> list[dict]:
    """The filled sheet as validated rows; exits listing every problem if any row is incomplete or wrong."""
    with SHEET.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    problems = []
    for r in rows:
        r["verdict"] = r["verdict"].strip()
        r["sections"] = [s.strip() for s in r["sections"].split(";") if s.strip()]
        if r["verdict"] not in VERDICTS:
            problems.append(f"{r['id']}: verdict must be one of {', '.join(VERDICTS)}")
        if not r["sections"]:
            problems.append(f"{r['id']}: no sections")
        for s in r["sections"]:
            sec = store.get_section(s)
            if sec is None or sec.policy != r["policy"]:
                problems.append(f"{r['id']}: unknown {r['policy']} section ID '{s}'")
    if len(rows) != N_BLIND:
        problems.append(f"expected {N_BLIND} rows, found {len(rows)}")
    if problems:
        sys.exit("Sheet not finished or has errors (no labels shown yet):\n  " + "\n  ".join(problems))
    return rows


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", nargs="?", choices=["sheet"], help="'sheet' writes the blank sheet")
    if ap.parse_args().command == "sheet":
        return make_sheet()

    rows = read_sheet()
    with BLIND.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"id": r["id"], "policy": r["policy"], "gold_verdict": r["verdict"],
                                "gold_sections": r["sections"], "notes": r["note"].strip()}) + "\n")
    reviewed = {r["id"]: r for r in map(json.loads, (SCEN_DIR / "reviewed.jsonl").open(encoding="utf-8"))}
    a = [r["verdict"] for r in rows]
    b = [reviewed[r["id"]]["gold_verdict"] for r in rows]
    k4, k2 = kappa_ci(a, b), kappa_ci([binary(v) for v in a], [binary(v) for v in b])
    same_sections = sum(set(r["sections"]) == set(reviewed[r["id"]]["gold_sections"]) for r in rows)
    overlap = sum(bool(set(r["sections"]) & set(reviewed[r["id"]]["gold_sections"])) for r in rows)
    print(f"Wrote {BLIND}\n\nBlind A vs reviewed (B), n={len(rows)}")
    print(f"  4-way:  agree {sum(x == y for x, y in zip(a, b))}/{len(a)}, kappa {k4[0]:.2f} [{k4[1]:.2f}-{k4[2]:.2f}]")
    print(f"  binary: agree {sum(binary(x) == binary(y) for x, y in zip(a, b))}/{len(a)}, "
          f"kappa {k2[0]:.2f} [{k2[1]:.2f}-{k2[2]:.2f}]")
    print(f"  sections: same set {same_sections}/{len(rows)}, at least one in common {overlap}/{len(rows)}")

    with DISAGREEMENTS.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "scenario", "A_verdict", "B_verdict", "A_sections", "B_sections", "A_note", "B_notes",
                    "decision"])
        n = 0
        for r in rows:
            g = reviewed[r["id"]]
            if r["verdict"] != g["gold_verdict"]:
                n += 1
                w.writerow([r["id"], r["scenario"], r["verdict"], g["gold_verdict"], ";".join(r["sections"]),
                            ";".join(g["gold_sections"]), r["note"], g.get("notes", ""), ""])
    print(f"\n{n} verdict disagreements -> {DISAGREEMENTS} (fill 'decision' together with B)")


if __name__ == "__main__":
    main()
