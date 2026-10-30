"""Quick end-to-end check of approaches on a few made-up scenarios (not gold data, never reported).

    python -m src.eval.smoke --model vllm_llama8b --approaches B0,A0

Needs the model server reachable (tunnel) and the index built. Prints one line per scenario x approach.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

from src import store
from src.approaches import REGISTRY
from src.llm import get_llm
from src.schema import Scenario

SMOKE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "smoke_scenarios.jsonl"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="vllm_llama8b")
    core = yaml.safe_load((SMOKE_PATH.parents[2] / "configs" / "run.yaml").read_text(encoding="utf-8"))["approaches"]
    ap.add_argument("--approaches", default=",".join(a for a in core if a in REGISTRY),
                    help="default: run.yaml's list (L0 needs a long-context server)")
    ap.add_argument("--show", action="store_true", help="also print each explanation")
    args = ap.parse_args()

    llm = get_llm(args.model)
    scenarios = [Scenario(**json.loads(line)) for line in SMOKE_PATH.read_text(encoding="utf-8").splitlines() if line]
    store.search("warm up", scenarios[0].policy, k=1)   # load the embedding model before anything is timed
    right = total = 0
    for sc in scenarios:
        for aid in args.approaches.split(","):
            out = REGISTRY[aid](sc, llm, store)
            ok = out.verdict == sc.gold_verdict
            right, total = right + ok, total + 1
            u = out.usage
            print(f"{sc.id:13} {aid:3} {'OK ' if ok else 'XX '} expected {sc.gold_verdict:17} got {out.verdict:17} "
                  f"cited {out.cited_sections} | {u['model_calls']} call(s), {u['prompt_tokens']} in / "
                  f"{u['completion_tokens']} out ({u['reasoning_tokens']} reasoning), {u['latency_s']:.1f}s"
                  + (f" | ERROR {out.error}" if out.error else ""))
            if args.show:
                print(f"{'':18}{out.explanation}")
    print(f"\n{right}/{total} match the expected verdicts (smoke check only, not a result)")


if __name__ == "__main__":
    main()
