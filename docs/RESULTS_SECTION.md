# Report draft: Results (Member A)

Structure fixed before the test run (27 Oct), so what we report does not depend on what we find. Filled 4 Nov from
`results/test/` (runs at commit b80d7c3). Rewrite in your own words before submitting.

## 7. Results

### 7.1 Test set

124 claims (80 FWD, 44 MSIG), frozen on 28 Oct at commit b7bcde0. Gold verdicts: 46 covered, 53 not_covered,
14 partially_covered, 11 insufficient_info. These runs used commit b80d7c3 (A3 and A4D: c184cad; A0K10: bd31b05). Each of the 4 pre-registered setups and the
exploratory L0 ran once on each model: 1,240 answers. 9 were parse errors, all on gpt-oss (8 L0, 1 A2), scored as
wrong.

### 7.2 Leaderboard

[Figure: `leaderboard.png`. Table: `leaderboard.md`, one row per setup × model.]

- Best accuracy: A4 on both models among the pre-registered setups: 0.61 [0.53–0.69] on Llama, 0.71 [0.63–0.78] on
  gpt-oss. The exploratory L0 on gpt-oss is higher still (0.76, 7.6).
- Retrieval vs no retrieval: A0 0.56 vs B0 0.54 on Llama, 0.69 vs 0.46 on gpt-oss.
- Agents vs simple RAG: A2 0.60 and A4 0.61 vs A0 0.56 on Llama; A2 0.62 and A4 0.71 vs A0 0.69 on gpt-oss.
- Model effect: gpt-oss beats Llama on every retrieval setup (A0 +13 points, A2 +2, A4 +10) but not without
  retrieval (B0 −8).

### 7.3 Significance (pre-registered McNemar, Holm-corrected)

| Comparison | Llama: p (Holm) | gpt-oss: p (Holm) | Only first right / only second right (Llama; gpt-oss) |
|---|---|---|---|
| A4 (best agent) vs A0 | 0.38 (1.00) | 0.88 (0.88) | 19 / 13; 22 / 20 |
| A0 vs B0 | 0.71 (1.00) | <0.001 (0.001) | 16 / 13; 45 / 16 |
| A2 vs A4 | 0.86 (1.00) | 0.12 (0.24) | 15 / 17; 15 / 26 |

Only one comparison is separated: retrieval beats no retrieval on gpt-oss. No agent is separated from A0 on either
model. With 124 claims, a gap of about 14 points (Llama) or 16 points (gpt-oss) between A4 and A0 is needed for 80%
power; the observed gaps are 5 and 2.

### 7.4 Decision rule: the winner

Rule (fixed in advance): highest test accuracy whose wrong-covered rate is no worse than A0's; if McNemar does not
separate the top two, the cheaper and faster one wins.

- Llama: **A0**. A4 has the top accuracy and is eligible (wrong-covered 0.08 vs A0's 0.13). A2 (0.60) is not
  eligible (0.17). A4 and A0 are not separated (p = 0.38), so the cheaper A0 wins.
- gpt-oss: **A0**. A4 is top and eligible (0.02 vs 0.17), but not separated from A0 (p = 0.88).
- Demo: A0 on gpt-oss-20b, the more accurate A0 (0.69 vs 0.56), with A4 as a toggle.

### 7.5 Safety

Wrong-covered rate (gold not_covered answered covered or partially_covered, out of 53):

| | B0 | L0 | A0 | A2 | A4 |
|---|---|---|---|---|---|
| Llama 8B | 0.06 | 0.00 | 0.13 | 0.17 | 0.08 |
| gpt-oss-20b | 0.23 | 0.13 | 0.17 | 0.11 | 0.02 |

Retrieval alone does not make answers safer: on Llama, A0 promises payouts more often than B0, which answers
not_covered to 89 of 124 claims. A4 is the safest retrieval setup on both models (1 of 53 on gpt-oss vs A0's 9, exploratory p = 0.021;
discussion 8.4).

### 7.6 Is the gain worth the cost?

[Figures: `accuracy_vs_latency.png`, `accuracy_vs_tokens.png`.]

The winner is A0, so the question is what A4 buys. On Llama, +5 points for 2.8× the seconds (9.5 vs 3.4) and 2.5× the
tokens (6,626 vs 2,635). On gpt-oss, +2 points for 2.6× the seconds (15.2 vs 5.8) and 2.0× the tokens (6,476 vs
3,247). Neither gain is significant (7.3), so on accuracy the extra cost is not justified. A2 costs more and gains
nothing on gpt-oss (27.6 s, 4.8× A0).

**Exploratory: long context (L0).** L0 accuracy 0.32 (Llama) / 0.76 (gpt-oss) at about 13× A0's tokens (34k and 41k
per claim). On Llama it is far below A0 and A4 (p < 0.001 for both; only A0 right on 43 claims, only L0 on 13): it
answered insufficient_info on 79 of 124 claims, 39 of them gold covered. On
gpt-oss it is not separated from A0 (p = 0.28) or A4 (p = 0.45) (uncorrected, not pre-registered). By policy: FWD
(≈28k tokens) 0.39 vs MSIG (≈45k) 0.20 on Llama, 0.71 vs 0.84 on gpt-oss. Reading the whole policy works for the
reasoning model, at about 3× A0's latency (18.0 s), and fails for the 8B model, worst on the longer policy.

### 7.7 Why answers were wrong (trace evaluation)

[Figure: `failures.png`.]

[Figure: `process_outcomes.png`: every answer as sound / right without evidence / wrong with evidence / wrong without
evidence / error.]

- Citations: 95 to 100% of cited IDs exist in the policy, and every real ID cited was in the model's context: no
  answer cites a real section it never saw. The bad IDs are made up or mistyped, almost all on Llama (A0 2 answers,
  A2 5, A4 5, L0 2); on gpt-oss only L0 has any (4). Without the policy, Llama's B0 cited 4 IDs (2 made up) and
  gpt-oss's B0 cited none.
- Process vs outcome (Llama / gpt-oss):

  | | A0 | A2 | A4 | L0 |
  |---|---|---|---|---|
  | Accuracy | 0.56 / 0.69 | 0.60 / 0.62 | 0.61 / 0.71 | 0.32 / 0.76 |
  | Sound rate | 0.35 / 0.44 | 0.38 / 0.44 | 0.54 / 0.62 | 0.32 / 0.76 |
  | Grounded rate | 0.23 / 0.36 | 0.27 / 0.33 | 0.23 / 0.48 | 0.15 / 0.40 |
  | Right without evidence (claims) | 27 / 32 | 27 / 23 | 9 / 11 | 0 / 0 |

  When only sound answers count, A4's lead over A0 grows from 5 / 2 points to 19 / 18: A0 gets over a third of its
  right answers (27 of 70, 32 of 86) without the evidence. B0 is right on 67 (Llama) and 57 (gpt-oss) claims with no evidence at all.
  Once faithfulness is added (grounded rate), A4 leads only on gpt-oss.
- Evidence recall: A0 0.66 / 0.66, A2 0.66 / 0.68, A4 0.91 / 0.84, L0 1.00; B0 is 0 by design.
- Wrong answers, missing evidence vs had evidence (Llama; gpt-oss): A0 31 vs 23; 26 vs 12. A2 31 vs 19; 31 vs 15
  (+1 parse error). A4 11 vs 37; 18 vs 18. A0 fails mostly at retrieval, A4 mostly at reasoning.
- Step quality: A2's grader raises precision from 0.20 to 0.53 (Llama) and from 0.21 to 0.72 (gpt-oss) while
  keeping recall (0.70 / 0.67), so it removes noise well. Its rewrite rarely helps: A2 rewrote the query on 25
  (Llama) and 70 (gpt-oss) of 124 claims, but a rewrite added a needed section only 2 and 5 times, so A2's
  evidence recall (0.66 / 0.68) matches A0's. On gpt-oss, 42 of the 70 rewrite replies were unusable, most likely
  because the model's reasoning ran past the 2,048-token reply limit (the cause is not logged); A2 then answered from
  what it had. A2 is limited by its search, not its grader. A4 step recall (Llama / gpt-oss): benefits 0.94 / 0.88,
  exclusions 0.90 / 0.81, definitions 0.62 / 0.58. Llama's exclusion step keeps about 10 sections per claim (precision
  0.04) while gpt-oss keeps 1 (precision 0.25). A4 is limited by the definitions step, which
  matches defined terms by name and misses a term the claim implies but does not use (fwd-059: it fetched
  "natural disaster", not "serious public event"). Once the evidence is in, A4's errors are mostly reasoning: on Llama
  37 of its 48 wrong answers had every gold section in context.
- Hand-check of 20 traces (10 per member): rows 11 to 20 (Member B, 7 A4 and 3 A2): 3 right verdicts (2 of them citing the wrong section or
  for the wrong reason), 2
  wrong_section_retrieved, 1 missed_exclusion, 4 other (2 over-cautious insufficient_info, 1 pre-existing-condition
  eligibility question, 1 "cover not stated" read as not covered). Example: Llama A4 on fwd-080 had the medical
  benefit and the definition of accident in context, yet asked whether a diving injury was accidental and answered
  insufficient_info. Rows 1 to 10 (Member A, 7 A2 and 3 A4): 9 right, 1 wrong (Llama A4 on msig-057: had the
  pet-care section, asked for the plan limit and kennel cost, which set the amount, not cover; over-cautious
  insufficient_info). Two patterns: right verdicts often skip a condition in the explanation (a 30-day window or the
  6-hour threshold), and A2 rewrote the query in 5 of its 7 rows, only once adding a needed section. Across all 20
  rows: 12 right, 8 wrong; the halves differ by chance (random sample).

### 7.8 By category

[Figure: `accuracy_by_category.png`.]

Accuracy (Llama / gpt-oss); claims per category in brackets:

| Category | A0 | A2 | A4 |
|---|---|---|---|
| single_section (65) | 0.62 / 0.72 | 0.66 / 0.74 | 0.62 / 0.69 |
| needs_definition (20) | 0.55 / 0.60 | 0.50 / 0.35 | 0.70 / 0.60 |
| needs_exclusion (25) | 0.56 / 0.68 | 0.64 / 0.52 | 0.68 / 0.92 |
| tricky (14) | 0.36 / 0.71 | 0.36 / 0.64 | 0.36 / 0.57 |

A4 helps where it was designed to: claims that need an exclusion (+12 and +24 points over A0) and, on Llama, a
definition (+15). It gains nothing on single-section claims, and on gpt-oss it is worst on tricky claims. Cells of
14 to 25 claims are too small to test; one claim moves a cell by 4 to 7 points.

### 7.9 Faithfulness (Member B)

Share of explanations the Haiku judge rated fully supported by the cited text ("yes"; the rest are "partly" or "no"):

| Setup | Llama 8B | gpt-oss-20b |
|---|---|---|
| B0 | 0.00 | 0.00 |
| L0 | 0.31 | 0.42 |
| A0 | 0.38 | 0.63 |
| A2 | 0.41 | 0.60 |
| A4 | 0.29 | 0.68 |

B0 cites nothing it was shown, so every B0 row is "no" by construction. On gpt-oss, A4 writes the most faithful
explanations (84 of 124 "yes", 3 "no"). On Llama it writes the least faithful of the retrieval setups (36 "yes", 38
"no"), although it has the best evidence recall (0.91). The 8B model gets the right sections from A4's workflow (a
context of about 18 sections against A0's 4) but often fails to quote them accurately. gpt-oss's A4 context is smaller
(about 7 sections, as its exclusions step keeps about 1 instead of 10) and it quotes it well. Faithfulness is not part of the decision rule; it feeds the grounded rate in 7.7.

**Judge vs human.** Member B checked 30 random judgments per model (fixed seed) against the policy text. Agreement
was 77% on Llama (Cohen's kappa 0.64) and 80% on gpt-oss (kappa 0.52). In 11 of the 13 disagreements the judge was
stricter than the human, mostly "partly" where the human said "yes" because an explanation left out a condition
without misstating it. Read the faithfulness numbers as a lower bound. The judge checks the explanation against the
cited text only, not against the verdict. In the 60 hand-checks one right answer (Llama A4, msig-051) had an
explanation that contradicts its own partially_covered verdict; the judge cannot catch this pattern.

### 7.10 Retrieval only: can one search find the evidence? (5.6)

[Table: `results/test/retrieval/retrieval.md`.]

- Gold recall at k = 5: dense 0.66, BM25 0.59, hybrid 0.64. Dense matches A0's evidence recall (0.66), as expected.
  One search finds every needed section for only about half the claims (0.53).
- By section type (dense, k = 5): benefits 0.76, definitions 0.00 (0 of 24), exclusions 0.26. A claim names what
  happened, not the defined terms or exclusions that decide it. This is the gap A4 closes by looking them up by
  structure (evidence recall 0.91 / 0.84).
- BM25 finds 9 of 24 definitions by exact words but fewer benefits (0.58); hybrid at k = 5 finds no definitions.
  A different search would not have fixed A0, and A4 shows that even with the evidence in, reasoning errors remain
  (7.7).

### 7.11 Dev vs test

Dev (20 claims) suggested A4 on gpt-oss was best (0.80, vs A0 0.65). Test agrees that A4 is top on gpt-oss, but the gap
shrinks to 0.71 vs 0.69. On Llama, dev had A4 at 0.45 and A0 at 0.50; test has 0.61 and 0.56. With 20 claims one answer moves
accuracy by 5 points, and the prompts were tuned on dev, so no reported claim uses dev numbers.

### 7.12 A4D: letting the model pick definitions (exploratory)

A4D (6.3) ran once on each model on all 124 test claims (main c184cad). It is exploratory and not in the decision rule.

| Model | Setup | Accuracy [95% CI] | Wrong-covered | Evidence recall | Faithfulness | Calls | Tokens | Seconds |
|---|---|---|---|---|---|---|---|---|
| Llama 8B | A4 | 0.61 [0.53–0.69] | 0.08 | 0.91 | 0.29 | 3.0 | 6,626 | 9.5 |
| Llama 8B | A4D | 0.58 [0.50–0.66] | 0.09 | 0.94 | 0.35 | 4.0 | 7,338 | 10.7 |
| gpt-oss-20b | A4 | 0.71 [0.63–0.78] | 0.02 | 0.84 | 0.68 | 3.0 | 6,476 | 15.2 |
| gpt-oss-20b | A4D | 0.73 [0.65–0.80] | 0.06 | 0.85 | 0.63 | 4.0 | 7,776 | 20.5 |

- The dev gain did not hold: A4D vs A4 is −3 points on Llama (only A4D right 4, only A4 right 8; exploratory McNemar
  p = 0.388) and +2 points on gpt-oss (13 vs 11; p = 0.839). Neither A4D vs A0 test is close to significant (p = 0.860
  Llama, 0.644 gpt-oss).
- Picking terms raised evidence recall only slightly (0.91 to 0.94 on Llama, 0.84 to 0.85 on gpt-oss), consistent with
  7.7: A4's misses were mostly reasoning failures, not missing definitions.
- A4D costs one more call and about 1.1–1.2× A4's tokens, and on gpt-oss its wrong-covered rate is higher (0.06 vs
  0.02). A4 stays the agent we report; A0 remains the winner.

### 7.13 A0K10: simple RAG with 10 passages (exploratory)

A0K10 is A0 with top_k = 10 instead of 5. It was added on 11 Nov, after the test results, to check whether A0 only
needed more passages. It ran once on each model on all 124 test claims (commit bd31b05) and is not in the decision rule.

| Model | Setup | Accuracy [95% CI] | Right | Wrong-covered | Evidence recall | Tokens |
|---|---|---|---|---|---|---|
| Llama 8B | A0 | 0.56 [0.48–0.65] | 70 | 0.13 (7/53) | 0.66 | 2,635 |
| Llama 8B | A0K10 | 0.59 [0.50–0.67] | 73 | 0.13 (7/53) | 0.75 | 4,573 |
| gpt-oss-20b | A0 | 0.69 [0.61–0.77] | 86 | 0.17 (9/53) | 0.66 | 3,247 |
| gpt-oss-20b | A0K10 | 0.70 [0.62–0.78] | 87 | 0.15 (8/53) | 0.75 | 5,382 |

- More passages did not help: +3 claims on Llama (only A0K10 right 9, only A0 right 6; exploratory McNemar p = 0.607)
  and +1 on gpt-oss (13 vs 12; p = 1.00). A0K10 vs A4 is also not significant (p = 0.690 Llama, 1.00 gpt-oss).
- Evidence recall rose from 0.66 to 0.75, as the retrieval-only check in 7.10 predicted, but the extra evidence did not
  turn into correct verdicts. On Llama, wrong answers that had all the evidence rose from 23 to 27.
- Safety did not improve: A4 still has the fewest wrong "covered" answers (1 of 53 on gpt-oss, against 8 for A0K10).
- Cost is 1.7× A0's tokens for the same single call. A0 stays the winner.
- Limits: these two runs used an L40S GPU because the A40 node was down, so seconds per claim are not compared (5.4 s
  gpt-oss, 2.8 s Llama on the L40S). Faithfulness was not judged for A0K10.
