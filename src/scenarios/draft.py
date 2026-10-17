"""Helpers for drafting claim scenarios from specific policy clauses (brief section 6).

The drafts themselves are written by Claude Code (no API cost) into data/scenarios/drafts.jsonl, one Scenario per
line with status "draft" and the intended answer in gold_verdict. This script lists and shows clauses to draft
from, and checks the drafts file before review.

    python -m src.scenarios.draft list fwd [--type benefit]
    python -m src.scenarios.draft show fwd:travel_delay
    python -m src.scenarios.draft check [data/scenarios/drafts.jsonl]
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from src import store
from src.schema import Scenario

DRAFTS_PATH = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "drafts.jsonl"


def check(path: Path) -> list[str]:
    """Problems found in a scenarios file (empty list = OK). Prints the verdict / category / policy mix."""
    problems, rows, seen = [], [], set()
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            s = Scenario.model_validate_json(line)
        except ValidationError as e:
            problems.append(f"line {n}: {e.errors()[0]['loc']} {e.errors()[0]['msg']}")
            continue
        if s.id in seen:
            problems.append(f"line {n}: duplicate id {s.id}")
        seen.add(s.id)
        if not s.id.startswith(f"{s.policy}-"):
            problems.append(f"line {n}: id {s.id} does not start with '{s.policy}-'")
        if not s.gold_sections:
            problems.append(f"{s.id}: no gold_sections")
        for sid in [s.source_clause, *s.gold_sections]:
            if sid and store.get_section(sid) is None:
                problems.append(f"{s.id}: unknown section_id {sid}")
            elif sid and not sid.startswith(f"{s.policy}:"):
                problems.append(f"{s.id}: section {sid} is not from policy {s.policy}")
        rows.append(s)
    for field in ("gold_verdict", "category", "policy"):
        mix = Counter(getattr(s, field) for s in rows)
        print(f"{field:13} " + "  ".join(f"{k}={v}" for k, v in mix.most_common()))
    print(f"{len(rows)} scenarios, {len(problems)} problem(s)")
    return problems


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="sections of a policy")
    p.add_argument("policy")
    p.add_argument("--type", choices=["benefit", "definition", "exclusion", "condition", "other"])
    sub.add_parser("show", help="full text of one section").add_argument("section_id")
    sub.add_parser("check", help="validate a scenarios file").add_argument("path", nargs="?", default=DRAFTS_PATH)
    args = ap.parse_args()

    if args.cmd == "list":
        for c in store.list_sections(args.policy, args.type):
            print(f"{c.section_id:70} {c.type:10} p{c.page:<3} {len(c.text.split())}w")
    elif args.cmd == "show":
        c = store.get_section(args.section_id)
        print(c.text if c else f"No section {args.section_id}")
    else:
        problems = check(Path(args.path))
        print("\n".join(problems))
        sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
