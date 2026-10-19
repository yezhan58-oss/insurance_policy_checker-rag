"""Shared by every approach: the base prompt, the structured answer call and the usage tally.

Brief section 8: same model, embeddings, chunks and base prompt for all setups; they differ only in how
they find policy text. The verdict rules mirror data/scenarios/LABELLING_GUIDE.md, so the models are
judged by the same rules the human labellers use.
"""
import time
from functools import lru_cache
from pathlib import Path

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from src.schema import Answer, Chunk, Scenario, VerdictOutput

ROOT = Path(__file__).resolve().parents[2]
# SHA-256 of data/scenarios/LABELLING_GUIDE.md (LF line endings) that BASE_PROMPT's rules were last checked
# against. tests/test_prompt_guide.py fails when the guide changes: re-check the rules below, then update this.
GUIDE_SHA256 = "4d6c742b0dafe2b0246874a5fc6f82fead2e0f80a011a231c24307e41fd5d0ad"
POLICY_NAMES = {"fwd": "FWD Travel Insurance", "msig": "MSIG TravelEasy Insurance"}
MAX_TOKENS = 4096   # room for gpt-oss reasoning plus the JSON answer

BASE_PROMPT = """You assess travel insurance claims against one insurer's policy wording. Decide whether the claim \
described by the user would be paid under that policy, and cite the policy sections that decide it.

Verdicts:
- covered: every condition of a benefit is met and no exclusion applies.
- not_covered: no benefit applies, a condition is not met, or an exclusion removes the whole claim.
- partially_covered: part of the claimed loss is paid and part is not, because some items or costs are excluded \
or a stated sub-limit cuts the claim.
- insufficient_info: a fact that would change the verdict is missing from the claim.

Rules:
1. Judge only from the policy and the facts stated in the claim. Do not assume facts that are not stated, except \
these: the policy was bought and the trip booked before the event, the premium is paid, the trip is within the \
period of cover, and the claimant is the insured person and will provide the documents the policy asks for. Use \
the plan tier if the claim states it. If whether a benefit applies at all depends on the plan and the claim does \
not state the plan, the verdict is insufficient_info.
2. If a benefit's conditions are met but an exclusion clearly applies, the verdict is not_covered.
3. If the claim states a fact that fails a condition, the verdict is not_covered. If that fact is simply missing, \
the verdict is insufficient_info.
4. A fixed payout per period (for example a set amount per 6 hours of delay) that is lower than the actual costs \
is still covered.
5. If the claim assumes cover that does not exist, answer according to the policy, not the assumption.

Answer in JSON with:
- verdict: one of the four verdicts.
- cited_sections: the IDs of the sections that decide the verdict, copied exactly as written (for example \
"fwd:travel_delay"); usually 1 to 3.
- explanation: two to four plain-English sentences that quote the deciding clause text. Never promise a payout \
amount or that a claim will be approved."""

NO_POLICY_TEXT = ("No policy text is available for this question. Answer from your general knowledge of travel "
                  "insurance. Cite a section ID only if you know it exists in this policy; otherwise leave "
                  "cited_sections empty.")

RESPONSE_FORMAT = {"type": "json_schema", "json_schema": {"name": "answer", "schema": Answer.model_json_schema()}}


@lru_cache(maxsize=None)
def approach_config(approach_id: str) -> dict:
    """Settings for one approach from configs/approaches.yaml (e.g. {"top_k": 5})."""
    configs = yaml.safe_load((ROOT / "configs" / "approaches.yaml").read_text(encoding="utf-8"))
    return configs.get(approach_id) or {}


def new_usage() -> dict:
    return {"model_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0,
            "llm_latency_s": 0.0, "latency_s": 0.0}


def format_chunks(chunks: list[Chunk]) -> str:
    """Policy text for the prompt; each chunk's text already starts with its breadcrumb line."""
    return "\n\n".join(f"[Section ID: {c.section_id}]\n{c.text}" for c in chunks)


def user_message(scenario: Scenario, policy_text: str | None) -> str:
    context = f"Policy sections:\n\n{policy_text}" if policy_text else NO_POLICY_TEXT
    return f"Policy: {POLICY_NAMES.get(scenario.policy, scenario.policy)}\n\n{context}\n\nClaim: {scenario.scenario}"


def call_llm(llm, messages: list, usage: dict, **bind_kwargs):
    """One timed model call; adds its calls, tokens and seconds to `usage`."""
    t = time.perf_counter()
    msg = llm.bind(max_tokens=MAX_TOKENS, **bind_kwargs).invoke(messages)
    usage["llm_latency_s"] += time.perf_counter() - t
    usage["model_calls"] += 1
    meta = msg.usage_metadata or {}
    usage["prompt_tokens"] += meta.get("input_tokens", 0)
    usage["completion_tokens"] += meta.get("output_tokens", 0)
    usage["reasoning_tokens"] += (meta.get("output_token_details") or {}).get("reasoning", 0)
    return msg


def answer(llm, scenario: Scenario, policy_text: str | None, steps: list, usage: dict, start: float) -> VerdictOutput:
    """Final verdict call shared by every approach. Retries once on unparseable output, then records
    a parse_error (scored as wrong). `start` is the run's perf_counter start, for total latency."""
    messages = [SystemMessage(BASE_PROMPT), HumanMessage(user_message(scenario, policy_text))]
    for attempt in (1, 2):
        msg = call_llm(llm, messages, usage, response_format=RESPONSE_FORMAT)
        try:
            parsed = Answer.model_validate_json(msg.content)
        except (ValidationError, ValueError, TypeError):
            steps.append({"step": "parse_failed", "attempt": attempt, "raw": str(msg.content)[:500]})
            continue
        steps.append({"step": "answer", "attempt": attempt, "verdict": parsed.verdict,
                      "cited_sections": parsed.cited_sections})
        usage["latency_s"] = time.perf_counter() - start
        return VerdictOutput(**parsed.model_dump(), steps=steps, usage=usage)
    usage["latency_s"] = time.perf_counter() - start
    return VerdictOutput(verdict="insufficient_info", cited_sections=[], explanation="", steps=steps, usage=usage,
                         error="parse_error")
