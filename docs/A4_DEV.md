# A4 exclusion-step tuning trial (dev, 26 Oct)

Branch `b/a4-tight-exclusions` (not merged). Jobs 338889 (Llama), 338891 (gpt-oss). Results in `results/dev/tuning/a4_tight/<model>`.

## Report draft

**Exclusion-step tuning trial.** Traces from the dev split showed that Llama 3.1 8B over-selected exclusions in A4's third step: it kept 13.2 exclusions per claim on average (precision 0.03), giving 21.1 sections of context per claim, 93% of them not needed. Since 9 of its 10 wrong dev answers had all the gold evidence in context, we tested whether this excess context caused the reasoning failures. We tightened the exclusion prompt to pick only exclusions whose conditions are met by the stated facts, and fixed the acceptance rule before running: keep the new prompt only if dev accuracy and wrong-covered rate were no worse on both models. The tighter prompt cut exclusions to 1.9 per claim with no loss of exclusion recall (1.00), context to 9.9 sections, tokens from 7.3k to 6.0k and latency from 21.5 s to 6.1 s per claim (approximate: an earlier run of the same current prompt took 9.6 s per claim, so part of this gap reflects cluster load). Accuracy, however, did not improve: 9/20 versus 10/20 on Llama (wrong-covered rate 0.00 in both), and reasoning failures with full evidence rose from 9 to 10. On gpt-oss-20b the tighter prompt also scored lower (0.75 versus 0.80, wrong-covered 0.00 in both; 6.7 versus 6.9 sections in context), so it failed the rule on both models. The difference is one claim on 20 and within noise, but it gives no support to context size as the cause of Llama's errors. The prompt was therefore left unchanged for the test runs. We report this as a cost finding: A4's exclusion step could run noticeably faster on Llama without measurable accuracy loss, but the remaining errors are reasoning failures rather than retrieval or context problems.

## Numbers (Llama A4, dev n=20)

| | Current | Tighter |
|---|---|---|
| Accuracy | 0.50 | 0.45 |
| Wrong-covered | 0.00 | 0.00 |
| Exclusions picked/claim | 13.2 | 1.9 |
| Exclusion recall | 1.00 | 1.00 |
| Sections in context | 21.1 | 9.9 |
| Wrong: had evidence / missing | 9 / 1 | 10 / 1 |
| Tokens, latency | 7.3k, 21.5 s* | 6.0k, 6.1 s |

*Fresh re-run of the current prompt; an earlier run took 9.6 s/claim, so latency differences partly reflect cluster load.

gpt-oss: current prompt (run at fcb70dc) acc 0.80, wrong-covered 0.00, 6.9 sections; tighter prompt acc 0.75, wrong-covered 0.00, 6.7 sections, wrong 5 (3 had evidence, 2 missing). Fails the rule on gpt-oss too.
