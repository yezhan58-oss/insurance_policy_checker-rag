# Prompt tuning on the dev split

**Decision: keep the original `BASE_PROMPT`.** None of the three changes we tried beat it, and the reasoning-first
versions made the answers unstable from one run to the next. The only code change kept is a retry when a reply
hits the token limit (see the last section).

## Setup

- **Model:** Llama 3.1 8B Instruct (`vllm_llama8b`), served by vLLM on the SMU cluster, temperature 0.
- **Approach:** A0 (simple RAG, top 5 chunks). The base prompt is shared by every approach, so A0 is the cheapest
  way to test it.
- **Data:** the 20 dev scenarios (5 covered, 6 not_covered, 4 partially_covered, 5 insufficient_info). The test
  split was not touched.
- **Scoring:** `src/eval/score.py`, with 95% bootstrap CIs (1000 resamples, seed 0).
- **Outputs:** each run's outputs and exact prompt are in `results/dev/tuning/<run>/` (`raw.jsonl`,
  `run_config.json`). These are gitignored, so they exist only locally.

## Why we tuned

On the first dev run, Llama never answered `insufficient_info` (0/5 right) and got 1 of 4 `partially_covered`
right. It answered `not_covered` 13 times out of 20. gpt-oss-20b on the same prompt did much better on these two
verdicts, at 3/4 and 3/5 with A0. So the goal was to help the smaller model with these two verdicts.

## What we tried

| Run | Change to the original prompt |
|---|---|
| baseline | none (commit fcb70dc) |
| exp1 | a 4-step checklist before answering: (a) judge each claimed item on its own; (b) mixed paid and unpaid items mean partially_covered; (c) a missing deciding fact means insufficient_info; (d) use not_covered only for a stated failed condition, a clear exclusion, or no benefit at all |
| exp2 | exp1, plus a `reasoning` field placed **before** `verdict` in the JSON schema, so the model writes its checks before it commits to a verdict |
| exp3 | exp2 with narrower steps (c) and (d): payout amounts, plan limits and conditions that do not apply never make a claim insufficient_info, and covered is used when every applicable condition is met |
| exp3b | the exp3 prompt again, unchanged (noise check) |
| exp0b | the original prompt again, at commit 4c98f79 (noise check) |

## Results (Llama 3.1 8B, A0, dev, n = 20)

| Run | Accuracy [95% CI] | covered | not_covered | partially | insufficient | Errors | Mean latency |
|---|---|---|---|---|---|---|---|
| baseline | **0.50** [0.25–0.70] | 3/5 | 6/6 | 1/4 | 0/5 | 0 | 3.3 s |
| exp1 | 0.45 [0.20–0.70] | 3/5 | 6/6 | 0/4 | 0/5 | 0 | 3.5 s |
| exp2 | **0.50** [0.30–0.75] | 2/5 | 3/6 | 1/4 | 4/5 | 0 | 7.6 s |
| exp3 | 0.40 [0.20–0.65] | 3/5 | 4/6 | 0/4 | 1/5 | 1 | 6.9 s |
| exp3b | 0.35 [0.15–0.55] | 2/5 | 3/6 | 0/4 | 2/5 | 0 | 7.4 s |
| exp0b | **0.50** [0.25–0.70] | 3/5 | 6/6 | 1/4 | 0/5 | 0 | 3.5 s |

The wrong-covered rate (a not_covered claim answered covered or partially_covered) was 0.00 in every run.

## What we learned

1. **Instructions alone did not change the verdicts (exp1).** The JSON schema puts `verdict` first, so the model
   picks a verdict before it writes anything else. A checklist it never gets to write out has almost no effect:
   exp1 still answered not_covered 13 times out of 20, like the baseline.
2. **Reasoning first unlocked insufficient_info but overcorrected (exp2).** insufficient_info went from 0/5 to 4/5
   right. But the model now answered insufficient_info 12 times out of 20, and not_covered fell from 6/6 to 3/6.
   Overall accuracy stayed at 0.50, and the reasoning more than doubled latency (completion tokens went from about 100 to 250).
3. **Narrowing the rules did not fix the overcorrection (exp3).** Accuracy fell to 0.40. One reply looped until it
   hit the 4096-token limit and was scored as an error.
4. **Reasoning-first runs are unstable.** The same exp3 prompt run twice (exp3, exp3b) gave a different verdict on
   5 of 20 scenarios, even at temperature 0. The original prompt run twice (baseline, exp0b) gave the same verdict
   on all 20. Our guess is that small numeric differences in vLLM grow over a long reasoning text, but we did not
   test this. Either way, a 0.05–0.10 change between prompts is within run-to-run noise for the reasoning-first
   versions.
5. **All the CIs overlap.** With 20 scenarios, no prompt is shown to be better than another.
6. **The weakness is the model's, not the prompt's.** gpt-oss-20b, on the original prompt, already gets 3/5
   insufficient_info with A0 and 5/5 with A4. This gap between models is a finding to report, not something to
   tune away for one model.

Keeping the original prompt also means every approach and both models still share one prompt (brief section 8),
and the dev runs already made with it stay valid.

## Code change kept: retry on the token limit

When a reply hits `max_tokens`, the OpenAI client raises `LengthFinishReasonError` instead of returning text. This
happened in exp3 and earlier in an A4 run. `answer()` in `src/approaches/_common.py` now treats this like any
other unparseable reply. It retries once, then records a `parse_error`, which is scored as wrong. The tokens of the
cut-off call are still counted in the cost. This is covered by `test_length_limit_reply_is_retried_then_parse_error`
in `tests/test_approaches.py`.
