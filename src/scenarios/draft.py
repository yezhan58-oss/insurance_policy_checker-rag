"""Helpers for drafting claim scenarios from specific policy clauses (brief section 6).

The drafts themselves are written by Claude Code (no API cost) into data/scenarios/drafts.jsonl, one Scenario per
line with status "draft" and the intended answer in gold_verdict. This script lists and shows clauses to draft
from, and checks the drafts file before review.

    python -m src.scenarios.draft list fwd [--type benefit]
    python -m src.scenarios.draft show fwd:travel_delay
    python -m src.scenarios.draft check [data/scenarios/drafts.jsonl]
    python -m src.scenarios.draft split        reviewed.jsonl -> dev.jsonl (10 per policy) + test.jsonl
"""
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from src import store
from src.schema import Scenario

SCEN_DIR = Path(__file__).resolve().parents[2] / "data" / "scenarios"
DRAFTS_PATH = SCEN_DIR / "drafts.jsonl"
SPLIT_SEED, DEV_PER_POLICY = 469, 10


def split(scen_dir: Path = SCEN_DIR) -> tuple[list[dict], list[dict]]:
    """Kept reviewed scenarios -> (dev, test). Dev takes DEV_PER_POLICY random scenarios from each policy."""
    rows = [json.loads(l) for l in (scen_dir / "reviewed.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    kept = [r for r in rows if r["status"] != "deleted"]
    rng = random.Random(SPLIT_SEED)
    dev_ids = set()
    for policy in sorted({r["policy"] for r in kept}):
        dev_ids |= set(rng.sample(sorted(r["id"] for r in kept if r["policy"] == policy), DEV_PER_POLICY))
    dev = [r for r in kept if r["id"] in dev_ids]
    test = [r for r in kept if r["id"] not in dev_ids]
    for name, part in (("dev", dev), ("test", test)):
        (scen_dir / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in part), encoding="utf-8")
    return dev, test


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
    sub.add_parser("split", help="write dev.jsonl and test.jsonl from reviewed.jsonl")
    args = ap.parse_args()

    if args.cmd == "list":
        for c in store.list_sections(args.policy, args.type):
            print(f"{c.section_id:70} {c.type:10} p{c.page:<3} {len(c.text.split())}w")
    elif args.cmd == "show":
        c = store.get_section(args.section_id)
        print(c.text if c else f"No section {args.section_id}")
    elif args.cmd == "split":
        dev, test = split()
        print(f"dev {len(dev)}, test {len(test)} (seed {SPLIT_SEED})")
        for name in ("dev", "test"):
            check(SCEN_DIR / f"{name}.jsonl")
    else:
        problems = check(Path(args.path))
        print("\n".join(problems))
        sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
