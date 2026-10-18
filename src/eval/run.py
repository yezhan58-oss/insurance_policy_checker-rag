"""Run approaches x one model over a split and save raw outputs (resumable).

    python -m src.eval.run --model vllm_llama8b --split dev
    python -m src.eval.run --model vllm_gptoss20b --split dev --approaches B0,A0 --limit 3

Writes one JSONL row per (scenario, approach) to results/<split>/<model>/raw.jsonl: the full VerdictOutput,
the gold labels and the git commit. Rows already there are skipped, so a cut-off job can simply be resubmitted.
Every invocation also appends its config (models.yaml entry without secrets, approaches.yaml, run.yaml, index
settings, commit) to run_config.json in the same folder. The test split refuses to run on uncommitted code.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import yaml

from src import store
from src.approaches import REGISTRY
from src.llm import get_llm, load_model_config
from src.schema import Scenario

ROOT = Path(__file__).resolve().parents[2]
SCEN_DIR = ROOT / "data" / "scenarios"
RESULTS_DIR = ROOT / "results"


def git_commit() -> str:
    """Short HEAD hash, with '-dirty' if tracked files have uncommitted changes."""
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return head + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def load_scenarios(split: str) -> list[Scenario]:
    rows = [json.loads(line) for line in (SCEN_DIR / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    return [Scenario(**r) for r in rows if r.get("status") != "deleted"]


def done_keys(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {(r["scenario_id"], r["approach"]) for r in map(json.loads, f) if r}


def run_split(scenarios: list[Scenario], approaches: dict, llm, store_module, model: str, split: str,
              out_path: Path, commit: str, log=print) -> dict:
    """Run every (scenario, approach) not yet in out_path, appending one row each. Returns counts."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = done_keys(out_path)
    counts = {"done": 0, "skipped": 0, "failed": 0}
    with out_path.open("a", encoding="utf-8") as f:
        for sc in scenarios:
            for aid, run in approaches.items():
                if (sc.id, aid) in done:
                    counts["skipped"] += 1
                    continue
                try:
                    out = run(sc, llm, store_module)
                except Exception as e:   # e.g. server unreachable: no row is written, so a rerun retries it
                    counts["failed"] += 1
                    log(f"FAILED {sc.id} {aid}: {type(e).__name__}: {e}")
                    continue
                row = {"scenario_id": sc.id, "approach": aid, "model": model, "split": split, "policy": sc.policy,
                       "category": sc.category, "gold_verdict": sc.gold_verdict, "gold_sections": sc.gold_sections,
                       "output": out.model_dump(), "commit": commit,
                       "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                counts["done"] += 1
                mark = "OK" if out.error is None and out.verdict == sc.gold_verdict else "xx"
                log(f"{sc.id:10} {aid:3} {mark} gold {sc.gold_verdict:17} got {out.verdict:17}"
                    f" {out.usage.get('latency_s', 0):5.1f}s" + (f"  ERROR {out.error}" if out.error else ""))
    return counts


def record_config(out_dir: Path, model: str, approaches: list[str], split: str, commit: str, run_cfg: dict) -> None:
    model_cfg = {k: v for k, v in load_model_config(model).items() if k != "api_key"}
    entry = {"started_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "commit": commit,
             "split": split, "model": model, "model_config": model_cfg, "approaches": approaches,
             "approaches_config": yaml.safe_load((ROOT / "configs" / "approaches.yaml").read_text(encoding="utf-8")),
             "run_config": run_cfg, "embed_model": store.EMBED_MODEL}
    path = out_dir / "run_config.json"
    history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    path.write_text(json.dumps(history + [entry], indent=1), encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", required=True, help="a name from configs/models.yaml")
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--approaches", help="comma-separated, e.g. B0,A0 (default: run.yaml's list, as available)")
    ap.add_argument("--limit", type=int, help="only the first N scenarios (quick checks)")
    ap.add_argument("--out", type=Path, help="output folder (default results/<split>/<model>)")
    args = ap.parse_args()

    run_cfg = yaml.safe_load((ROOT / "configs" / "run.yaml").read_text(encoding="utf-8"))
    if args.approaches:
        ids = args.approaches.split(",")
        missing = [a for a in ids if a not in REGISTRY]
        if missing:
            sys.exit(f"Unknown approach(es) {missing}; available: {sorted(REGISTRY)}")
    else:
        ids = [a for a in run_cfg["approaches"] if a in REGISTRY]
        skipped = [a for a in run_cfg["approaches"] if a not in REGISTRY]
        if skipped:
            print(f"Not implemented yet, skipped: {skipped}")
    commit = git_commit()
    if args.split == "test" and (commit == "unknown" or commit.endswith("-dirty")):
        sys.exit(f"Refusing to run the test split on commit '{commit}': commit (and freeze) your changes first.")

    scenarios = load_scenarios(args.split)[: args.limit]
    out_dir = args.out or RESULTS_DIR / args.split / args.model
    out_dir.mkdir(parents=True, exist_ok=True)
    record_config(out_dir, args.model, ids, args.split, commit, run_cfg)
    llm = get_llm(args.model, temperature=run_cfg["temperature"])
    store.search("warm up", scenarios[0].policy, k=1)   # load the embedding model before anything is timed
    print(f"{args.model} | {args.split} ({len(scenarios)} scenarios) | {ids} | commit {commit} -> {out_dir}")
    counts = run_split(scenarios, {a: REGISTRY[a] for a in ids}, llm, store, args.model, args.split,
                       out_dir / "raw.jsonl", commit)
    print(f"\n{counts['done']} new rows, {counts['skipped']} already done, {counts['failed']} failed")
    if counts["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
