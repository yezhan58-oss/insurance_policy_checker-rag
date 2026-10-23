# A2 (CRAG) on the dev split

Dev only (20 scenarios), temperature 0. Results are in `results/dev/<model>/` (A2 rows) and
`results/dev/tuning/a2_min1/<model>/` (gitignored, local only). Numbers from `src.eval.score` and `src.eval.traces`.

## First run (min_relevant 2, max_rewrites 2)

| | Llama 3.1 8B | gpt-oss-20b |
|---|---|---|
| Accuracy (A0 / A4 for reference) | 0.45 (0.50 / 0.45) | 0.70 (0.65 / 0.80) |
| Wrong-covered rate (A0) | 0.00 (0.00) | 0.00 (0.17) |
| Mean time per claim | 10.1 s | 26.9 s |
| Claims that rewrote the query | 1 / 20 | 11 / 20 (17 rewrites) |
| Claims where a rewrite found a new gold section | 0 | 2 |
| Claims where the grader dropped a gold section the search had found | 0 | 0 |
| Grader precision (search precision before grading) | 0.37 (0.18) | 0.72 (0.20) |

- The grader works: it removes most of the irrelevant chunks and never dropped a needed one.
- The rewrite loop rarely finds missing evidence; most remaining errors are still missing evidence (5 of 11 wrong on
  Llama, 4 of 6 on gpt-oss). Llama's lenient grader keeps 2+ chunks, so it almost never rewrites.
- 5 of gpt-oss's 17 rewrites repeated an earlier query. A repeated query returns the same chunks, so the loop now
  stops there (commit "A2: stop the loop when a rewrite repeats an earlier query"); this cannot change a verdict.

## Trial: min_relevant 1 (branch `a/a2-trial-min1`, not merged)

Rule fixed before the run: switch to 1 only if dev accuracy and wrong-covered rate are no worse on both models and
time per claim drops.

| | Llama, 2 | Llama, 1 | gpt-oss, 2 | gpt-oss, 1 |
|---|---|---|---|---|
| Accuracy | 0.45 | 0.45 | 0.70 | 0.60 |
| Wrong-covered rate | 0.00 | 0.00 | 0.00 | 0.17 |
| Mean time per claim | 10.1 s | 9.9 s | 26.9 s | 9.9 s |

**Decision: keep min_relevant 2.** On gpt-oss, 1 is 2.7x faster but less accurate and less safe, so it fails the
rule. With 20 scenarios a 0.10 gap is within run-to-run noise (see `PROMPT_TUNING.md`), so this is a trade-off to
report, not a proven effect. The trial also ran with the repeated-query stop, so its time includes that saving.
