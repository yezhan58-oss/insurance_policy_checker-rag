"""LLM faithfulness judge (brief section 9): is each explanation supported by the text of the sections it cites?

    python -m src.eval.judge --model vllm_llama8b --split dev              # estimate cost only, no API calls
    python -m src.eval.judge --model vllm_llama8b --split dev --yes        # run the Claude Haiku judge
    python -m src.eval.judge --model vllm_llama8b --split dev --export 30  # 30 random judgments for hand-checks

Reads results/<split>/<model>/raw.jsonl and writes judged.jsonl next to it: one row per (scenario, approach) with
faithfulness yes / partly / no and the judge's reason. Resumable: rows already judged are skipped. Rows with an
error are not judged (they already count as wrong); rows that cite nothing get "no" without a call.
"""
import argparse
import json
import random
import sys
from pathlib import Path
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src import store
from src.eval.run import RESULTS_DIR, done_keys
from src.llm import get_llm

JUDGE_MODEL = "claude_haiku_judge"
PRICE_IN, PRICE_OUT = 0.10 / 1e6, 0.50 / 1e6       # US$ per token, Claude Haiku 5.5
EST_OUT_TOKENS = 120                                # judged label + one or two sentences of reason
BUDGET_STOP = 4.0                                   # brief section 2: stop and ask above US$4

SYSTEM = """You check whether an insurance claim explanation is supported by the policy text it cites.
Judge only support, not whether the verdict is correct.
- yes: every factual claim about the policy in the explanation is stated in the cited text.
- partly: some claims are supported, but at least one is not in the cited text or misstates it.
- no: the main claims are not supported by the cited text, or contradict it.
Give the label and a one- or two-sentence reason."""


class Judgement(BaseModel):
    faithfulness: Literal["yes", "partly", "no"]
    reason: str


def cited_text(section_ids: list[str]) -> str:
    parts = []
    for sid in section_ids:
        sec = store.get_section(sid)
        parts.append(f"[{sid}] {sec.title}\n{sec.text}" if sec else f"[{sid}] (no such section)")
    return "\n\n".join(parts)


def prompt(row: dict) -> list:
    o = row["output"]
    return [SystemMessage(SYSTEM),
            HumanMessage(f"Cited policy text:\n{cited_text(o['cited_sections'])}\n\n"
                         f"Verdict: {o['verdict']}\nExplanation:\n{o['explanation']}")]


def to_judge(rows: list[dict], done: set) -> list[dict]:
    return [r for r in rows if (r["scenario_id"], r["approach"]) not in done and r["output"].get("error") is None]


def estimate_cost(rows: list[dict]) -> float:
    # shortcut: ~4 characters per token; good enough for a budget check, not for billing
    chars = sum(len(m.content) for r in rows if r["output"]["cited_sections"] for m in prompt(r))
    n = sum(1 for r in rows if r["output"]["cited_sections"])
    return chars / 4 * PRICE_IN + n * EST_OUT_TOKENS * PRICE_OUT


def judge_row(row: dict, judge) -> dict:
    if not row["output"]["cited_sections"]:
        return {"faithfulness": "no", "reason": "No sections cited."}
    for attempt in range(2):                        # brief section 7: retry a parse failure once
        try:
            out = judge.invoke(prompt(row))
            if out is not None:                     # None when the model skipped the structured-output tool
                return out.model_dump()
        except ValueError:                          # includes LangChain's OutputParserException
            pass
    return {"faithfulness": None, "reason": "parse_error"}


def run(rows: list[dict], judge, out_path: Path, log=print) -> int:
    todo = to_judge(rows, done_keys(out_path))
    with out_path.open("a", encoding="utf-8") as f:
        for r in todo:
            j = judge_row(r, judge)
            f.write(json.dumps({"scenario_id": r["scenario_id"], "approach": r["approach"], **j},
                               ensure_ascii=False) + "\n")
            f.flush()
            log(f"{r['scenario_id']:10} {r['approach']:3} {j['faithfulness']}")
    return len(todo)


def export_sample(raw: list[dict], judged_path: Path, n: int, out_csv: Path) -> None:
    import pandas as pd
    judged = {(j["scenario_id"], j["approach"]): j for j in map(json.loads, judged_path.open(encoding="utf-8"))}
    keys = random.Random(0).sample(sorted(judged), min(n, len(judged)))
    by_key = {(r["scenario_id"], r["approach"]): r for r in raw}
    pd.DataFrame([{"scenario_id": k[0], "approach": k[1], "cited_sections": ";".join(by_key[k]["output"]["cited_sections"]),
                   "explanation": by_key[k]["output"]["explanation"], "judge": judged[k]["faithfulness"],
                   "judge_reason": judged[k]["reason"], "human": ""} for k in keys]).to_csv(out_csv, index=False)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", required=True, help="the tested model whose results to judge")
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--yes", action="store_true", help="actually call the judge (default: print cost estimate)")
    ap.add_argument("--export", type=int, metavar="N", help="write N random judgments to hand_check.csv")
    args = ap.parse_args()

    out_dir = RESULTS_DIR / args.split / args.model
    raw = [json.loads(line) for line in (out_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines() if line]
    judged_path = out_dir / "judged.jsonl"
    if args.export:
        export_sample(raw, judged_path, args.export, out_dir / "hand_check.csv")
        print(f"Wrote {out_dir / 'hand_check.csv'}")
        return

    todo = to_judge(raw, done_keys(judged_path))
    cost = estimate_cost(todo)
    print(f"{len(todo)} rows to judge, estimated cost US${cost:.3f}")
    if cost > BUDGET_STOP:
        sys.exit(f"Estimate exceeds US${BUDGET_STOP}: ask the team before running.")
    if not args.yes:
        print("Dry run. Re-run with --yes to call the judge.")
        return
    judge = get_llm(JUDGE_MODEL, max_tokens=300).with_structured_output(Judgement)
    print(f"Judged {run(raw, judge, judged_path)} rows -> {judged_path}")


if __name__ == "__main__":
    main()
