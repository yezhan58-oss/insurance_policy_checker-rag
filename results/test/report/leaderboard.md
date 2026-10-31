# Leaderboard (test split)

| Model | Approach | Accuracy [95% CI] | Binary acc. | Wrong-covered | Clause recall | Faithfulness | Evidence recall | Sound rate | Grounded rate | Cites in context | Calls | Tokens | Seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Llama 8B | B0 | 0.54 [0.46–0.62] | 0.65 | 0.06 | 0.00 | – | 0.00 | 0.00 | – | 0.00 | 1.0 | 630 | 2.6 |
| Llama 8B | L0 | 0.32 [0.24–0.41] | 0.52 | 0.00 | 0.68 | – | 1.00 | 0.32 | – | 0.99 | 1.0 | 34246 | 4.5 |
| Llama 8B | A0 | 0.56 [0.48–0.65] | 0.65 | 0.13 | 0.61 | – | 0.66 | 0.35 | – | 0.98 | 1.0 | 2635 | 3.4 |
| Llama 8B | A2 | 0.60 [0.51–0.68] | 0.65 | 0.17 | 0.61 | – | 0.66 | 0.38 | – | 0.97 | 2.5 | 4339 | 4.3 |
| Llama 8B | A4 | 0.61 [0.53–0.69] | 0.69 | 0.08 | 0.56 | – | 0.91 | 0.54 | – | 0.95 | 3.0 | 6626 | 9.5 |
| gpt-oss-20b | B0 | 0.46 [0.38–0.54] | 0.62 | 0.23 | 0.00 | – | 0.00 | 0.00 | – | – | 1.1 | 1700 | 9.1 |
| gpt-oss-20b | L0 | 0.76 [0.68–0.83] | 0.82 | 0.13 | 0.78 | – | 1.00 | 0.76 | – | 0.98 | 1.1 | 40842 | 18.0 |
| gpt-oss-20b | A0 | 0.69 [0.61–0.77] | 0.74 | 0.17 | 0.65 | – | 0.66 | 0.44 | – | 1.00 | 1.0 | 3247 | 5.8 |
| gpt-oss-20b | A2 | 0.62 [0.53–0.70] | 0.74 | 0.11 | 0.66 | – | 0.68 | 0.44 | – | 1.00 | 2.8 | 6139 | 27.6 |
| gpt-oss-20b | A4 | 0.71 [0.63–0.78] | 0.76 | 0.02 | 0.76 | – | 0.84 | 0.62 | – | 1.00 | 3.0 | 6476 | 15.2 |

## Llama 8B (commits b80d7c3)

- McNemar best agent vs A0: A4 vs A0, p = 0.377, Holm p = 1.000; only A4 right 19, only A0 right 13
- McNemar A0 vs B0: A0 vs B0, p = 0.711, Holm p = 1.000; only A0 right 16, only B0 right 13
- McNemar A2 vs A4: A2 vs A4, p = 0.860, Holm p = 1.000; only A2 right 15, only A4 right 17
- McNemar exploratory: L0 vs A0: p = 0.000 (not corrected, not pre-registered); only L0 right 13, only A0 right 43
- McNemar exploratory: L0 vs best agent: p = 0.000 (not corrected, not pre-registered); only L0 right 8, only A4 right 44
- Decision rule: **A0** (A4 and A0 not separated (McNemar p=0.377); A0 is cheaper/faster)

## gpt-oss-20b (commits b80d7c3)

- McNemar best agent vs A0: A4 vs A0, p = 0.878, Holm p = 0.878; only A4 right 22, only A0 right 20
- McNemar A0 vs B0: A0 vs B0, p = 0.000, Holm p = 0.001 (significant); only A0 right 45, only B0 right 16
- McNemar A2 vs A4: A2 vs A4, p = 0.117, Holm p = 0.235; only A2 right 15, only A4 right 26
- McNemar exploratory: L0 vs A0: p = 0.280 (not corrected, not pre-registered); only L0 right 25, only A0 right 17
- McNemar exploratory: L0 vs best agent: p = 0.451 (not corrected, not pre-registered); only L0 right 25, only A4 right 19
- Decision rule: **A0** (A4 and A0 not separated (McNemar p=0.878); A0 is cheaper/faster)

_Cites in context: share of cited section IDs that exist in the policy and were in the model's context (checked in code, no judge)._

_Sound rate: share of all claims answered right with every gold section in the model's context. Grounded rate: sound and the judge found the explanation faithful (shown once every row is judged). Right answers without the evidence are not counted by either._

_L0 (whole policy in the prompt, no retrieval) is exploratory: added after pre-registration, so it is outside the Holm-corrected tests and the decision rule._
