# Leaderboard (test split)

| Model | Approach | Accuracy [95% CI] | Binary acc. | Wrong-covered | Clause recall | Faithfulness | Evidence recall | Sound rate | Grounded rate | Cites in context | Calls | Tokens | Seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Llama 8B | B0 | 0.54 [0.46–0.62] | 0.65 | 0.06 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.0 | 630 | 2.6 |
| Llama 8B | L0 | 0.32 [0.24–0.41] | 0.52 | 0.00 | 0.68 | 0.31 | 1.00 | 0.32 | 0.15 | 0.99 | 1.0 | 34246 | 4.5 |
| Llama 8B | A0 | 0.56 [0.48–0.65] | 0.65 | 0.13 | 0.61 | 0.38 | 0.66 | 0.35 | 0.23 | 0.98 | 1.0 | 2635 | 3.4 |
| Llama 8B | A0K10 | 0.59 [0.50–0.67] | 0.69 | 0.13 | 0.64 | – | 0.75 | 0.39 | – | 1.00 | 1.0 | 4573 | 2.8 |
| Llama 8B | A2 | 0.60 [0.51–0.68] | 0.65 | 0.17 | 0.61 | 0.41 | 0.66 | 0.38 | 0.27 | 0.97 | 2.5 | 4339 | 4.3 |
| Llama 8B | A3 | 0.61 [0.53–0.69] | 0.69 | 0.11 | 0.63 | 0.40 | 0.88 | 0.50 | 0.27 | 0.98 | 7.9 | 45988 | 16.6 |
| Llama 8B | A4 | 0.61 [0.53–0.69] | 0.69 | 0.08 | 0.56 | 0.29 | 0.91 | 0.54 | 0.23 | 0.95 | 3.0 | 6626 | 9.5 |
| Llama 8B | A4D | 0.58 [0.50–0.66] | 0.69 | 0.09 | 0.60 | 0.35 | 0.94 | 0.56 | 0.27 | 0.95 | 4.0 | 7338 | 10.7 |
| gpt-oss-20b | B0 | 0.46 [0.38–0.54] | 0.62 | 0.23 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | – | 1.1 | 1700 | 9.1 |
| gpt-oss-20b | L0 | 0.76 [0.68–0.83] | 0.82 | 0.13 | 0.78 | 0.42 | 1.00 | 0.76 | 0.40 | 0.98 | 1.1 | 40842 | 18.0 |
| gpt-oss-20b | A0 | 0.69 [0.61–0.77] | 0.74 | 0.17 | 0.65 | 0.63 | 0.66 | 0.44 | 0.36 | 1.00 | 1.0 | 3247 | 5.8 |
| gpt-oss-20b | A0K10 | 0.70 [0.62–0.78] | 0.79 | 0.15 | 0.70 | – | 0.75 | 0.52 | – | 1.00 | 1.0 | 5382 | 5.4 |
| gpt-oss-20b | A2 | 0.62 [0.53–0.70] | 0.74 | 0.11 | 0.66 | 0.60 | 0.68 | 0.44 | 0.33 | 1.00 | 2.8 | 6139 | 27.6 |
| gpt-oss-20b | A3 | 0.76 [0.68–0.83] | 0.84 | 0.08 | 0.73 | 0.72 | 0.77 | 0.56 | 0.45 | 1.00 | 3.4 | 8263 | 11.3 |
| gpt-oss-20b | A4 | 0.71 [0.63–0.78] | 0.76 | 0.02 | 0.76 | 0.68 | 0.84 | 0.62 | 0.48 | 1.00 | 3.0 | 6476 | 15.2 |
| gpt-oss-20b | A4D | 0.73 [0.65–0.80] | 0.77 | 0.06 | 0.74 | 0.63 | 0.85 | 0.65 | 0.48 | 1.00 | 4.0 | 7776 | 20.5 |

## Llama 8B (commits b80d7c3, c184cad, c64d688)

- McNemar best agent vs A0: A4 vs A0, p = 0.377, Holm p = 1.000; only A4 right 19, only A0 right 13
- McNemar A0 vs B0: A0 vs B0, p = 0.711, Holm p = 1.000; only A0 right 16, only B0 right 13
- McNemar A2 vs A4: A2 vs A4, p = 0.860, Holm p = 1.000; only A2 right 15, only A4 right 17
- McNemar exploratory: L0 vs A0: p = 0.000 (not corrected, not pre-registered); only L0 right 13, only A0 right 43
- McNemar exploratory: L0 vs best agent: p = 0.000 (not corrected, not pre-registered); only L0 right 8, only A4 right 44
- McNemar exploratory: A3 vs A0: p = 0.362 (not corrected, not pre-registered); only A3 right 18, only A0 right 12
- McNemar exploratory: A3 vs best agent: p = 1.000 (not corrected, not pre-registered); only A3 right 13, only A4 right 13
- McNemar exploratory: A4D vs A0: p = 0.860 (not corrected, not pre-registered); only A4D right 17, only A0 right 15
- McNemar exploratory: A4D vs best agent: p = 0.388 (not corrected, not pre-registered); only A4D right 4, only A4 right 8
- McNemar exploratory: A0K10 vs A0: p = 0.607 (not corrected, not pre-registered); only A0K10 right 9, only A0 right 6
- McNemar exploratory: A0K10 vs best agent: p = 0.690 (not corrected, not pre-registered); only A0K10 right 11, only A4 right 14
- Decision rule: **A0** (A4 and A0 not separated (McNemar p=0.377); A0 is cheaper/faster)
- Decision rule with ReAct (A3) as a full candidate (added after the test results): **A4** (A3 and A4 not separated (McNemar p=1.000); A4 is cheaper/faster); best agent A4 vs A0 p = 0.377, Holm p = 1.000

## gpt-oss-20b (commits b80d7c3, bd31b05, c184cad)

- McNemar best agent vs A0: A4 vs A0, p = 0.878, Holm p = 0.878; only A4 right 22, only A0 right 20
- McNemar A0 vs B0: A0 vs B0, p = 0.000, Holm p = 0.001 (significant); only A0 right 45, only B0 right 16
- McNemar A2 vs A4: A2 vs A4, p = 0.117, Holm p = 0.235; only A2 right 15, only A4 right 26
- McNemar exploratory: L0 vs A0: p = 0.280 (not corrected, not pre-registered); only L0 right 25, only A0 right 17
- McNemar exploratory: L0 vs best agent: p = 0.451 (not corrected, not pre-registered); only L0 right 25, only A4 right 19
- McNemar exploratory: A3 vs A0: p = 0.185 (not corrected, not pre-registered); only A3 right 18, only A0 right 10
- McNemar exploratory: A3 vs best agent: p = 0.430 (not corrected, not pre-registered); only A3 right 23, only A4 right 17
- McNemar exploratory: A4D vs A0: p = 0.644 (not corrected, not pre-registered); only A4D right 23, only A0 right 19
- McNemar exploratory: A4D vs best agent: p = 0.839 (not corrected, not pre-registered); only A4D right 13, only A4 right 11
- McNemar exploratory: A0K10 vs A0: p = 1.000 (not corrected, not pre-registered); only A0K10 right 13, only A0 right 12
- McNemar exploratory: A0K10 vs best agent: p = 1.000 (not corrected, not pre-registered); only A0K10 right 21, only A4 right 22
- Decision rule: **A0** (A4 and A0 not separated (McNemar p=0.878); A0 is cheaper/faster)
- Decision rule with ReAct (A3) as a full candidate (added after the test results): **A4** (A3 and A4 not separated (McNemar p=0.430); A4 is cheaper/faster); best agent A3 vs A0 p = 0.185, Holm p = 0.235

_Cites in context: share of cited section IDs that exist in the policy and were in the model's context (checked in code, no judge)._

_Sound rate: share of all claims answered right with every gold section in the model's context. Grounded rate: sound and the judge found the explanation faithful (shown once every row is judged). Right answers without the evidence are not counted by either._

## Error types (human labels on wrong answers; "other" split by rule)

| Model | Approach | Wrong | wrong section retrieved | over cautious insufficient info | all or nothing partial | other | missed exclusion | accepted false assumption | misread definition |
|---|---|---|---|---|---|---|---|---|---|
| Llama 8B | A0 | 54 | 22 | 2 | 8 | 10 | 6 | 6 | 0 |
| Llama 8B | A4 | 48 | 7 | 10 | 12 | 10 | 3 | 5 | 1 |
| gpt-oss-20b | A0 | 38 | 19 | 7 | 2 | 0 | 8 | 2 | 0 |
| gpt-oss-20b | A4 | 36 | 15 | 12 | 1 | 2 | 2 | 1 | 3 |

_Over-cautious insufficient info: answered insufficient_info with every gold section in context, gold another verdict. All-or-nothing partial: gold partially_covered, answered covered or not_covered. Both split from the human "other" label by rule after the error review; the other types are the human labels._

## Safe mode (exploratory: A0, re-checked by A4 whenever A0 says covered)

| Model | Accuracy | Wrong-covered | Re-checked by A4 | Tokens | Seconds |
|---|---|---|---|---|---|
| Llama 8B | 0.56 | 0.04 (2 of 53) | 39 of 124 | 4790 | 6.6 |
| gpt-oss-20b | 0.66 | 0.00 (0 of 53) | 50 of 124 | 5913 | 12.3 |

_Simulated from the A0 and A4 answers above, no new model calls. Cost = A0 on every claim plus A4 on the re-checked ones._

_L0 (whole policy in the prompt, no retrieval) is exploratory: added after pre-registration, so it is outside the Holm-corrected tests and the decision rule._

_A3 (ReAct tool agent) was added after the test results. It is outside the planned Holm-corrected tests and decision rule; the rule is also reported with A3 as a full candidate._

_A0K10 (A0 with top_k=10 instead of 5) is exploratory: added on 11 Nov after the test results, so it is outside the Holm-corrected tests and the decision rule._
