# Report draft: Results (Member A)

Structure fixed before the test run (27 Oct), so what we report does not depend on what we find. Fill the [brackets]
from `results/test/report/` after the 2 Nov runs; every number comes from `leaderboard.md`. Rewrite in your own words
before submitting.

## 7. Results

### 7.1 Test set

[N] claims ([n] FWD, [n] MSIG), frozen on [29 Oct] at commit [hash]. Gold verdicts: [n] covered, [n] not_covered,
[n] partially_covered, [n] insufficient_info. Each of the 4 setups ran once on each model: [8 × N] answers, [n] parse
errors.

### 7.2 Leaderboard

[Figure: `leaderboard.png`. Table: `leaderboard.md`, one row per setup × model.]

Read across, one sentence each:
- Best accuracy on each model: [setup, model, accuracy, CI].
- Retrieval vs no retrieval: A0 [x] vs B0 [x] on Llama, [x] vs [x] on gpt-oss.
- Agents vs simple RAG: A2 [x], A4 [x] vs A0 [x] (per model).
- Model effect: gpt-oss vs Llama on the same setup, [range of gaps].

### 7.3 Significance (pre-registered McNemar, Holm-corrected)

| Comparison | Llama: p (Holm) | gpt-oss: p (Holm) | Only first right / only second right |
|---|---|---|---|
| Best agent vs A0 | [ ] | [ ] | [ ] |
| A0 vs B0 | [ ] | [ ] | [ ] |
| A2 vs A4 | [ ] | [ ] | [ ] |

One sentence on what is and is not separated. If nothing is significant, say so plainly: with [N] claims, a gap of
about [x] points is needed to detect a difference.

### 7.4 Decision rule: the winner

Rule (fixed in advance): highest test accuracy whose wrong-covered rate is no worse than A0's; if McNemar does not
separate the top two, the cheaper and faster one wins.

- Llama: [winner] ([reason line from leaderboard.md]).
- gpt-oss: [winner] ([reason]).
- Overall choice for the demo: [setup + model], because [one line].

### 7.5 Safety

Wrong-covered rate (gold not_covered answered as payable) per setup × model: [values]. [One sentence: which setups
promise payouts they should not, and whether retrieval reduces this.]

### 7.6 Is the gain worth the cost?

[Figures: `accuracy_vs_latency.png`, `accuracy_vs_tokens.png`.]

For each model, compare the winner to A0: +[x] accuracy for [x]× the seconds and [x]× the tokens per claim. State
whether the extra cost buys a significant gain (7.3). This answers the second half of the research question.

**Exploratory: long context (L0).** L0 accuracy [x] (Llama) / [x] (gpt-oss) at [x]× A0's tokens; McNemar vs A0
p = [x], vs the best agent p = [x] (uncorrected, not pre-registered). By policy: FWD (≈35k tokens) [x] vs MSIG
(≈52k) [x]. [One sentence: does reading everything beat retrieving the right parts on this corpus, and at what cost?]

### 7.7 Why answers were wrong (trace evaluation)

[Figure: `failures.png`.]

[Figure: `process_outcomes.png`: every answer as sound / right without evidence / wrong with evidence / wrong without
evidence / error.]

- Citations: [x]% of cited IDs exist in the policy and [x]% were in the model's context (per setup); [n] answers cite
  a section they never saw. B0 cites [x] IDs, [x]% of them invalid. [One sentence on which setups make up citations.]
- Process vs outcome: sound rate [values] vs verdict accuracy [values]; right without evidence [counts per setup].
  Grounded rate (sound and judged faithful): [values]. [One sentence on whether the accuracy ranking survives when
  only sound answers count.]
- Evidence recall: [values per setup × model]; B0 is 0 by design.
- Wrong answers split into missing evidence (retrieval failure) vs had evidence (reasoning failure): [counts].
- Step quality: A2 grader precision [x] vs search [x]; A4 step recall (Llama / gpt-oss): benefits 0.94 / 0.88,
  exclusions 0.90 / 0.81, definitions 0.62 / 0.58. Llama's exclusion step keeps about 10 sections per claim (precision
  0.04) while gpt-oss keeps 1 (precision 0.25). [One sentence on A2.] A4 is limited by the definitions step, which
  matches defined terms by name and misses a term the claim implies but does not use (fwd-059: it fetched
  "natural disaster", not "serious public event"). Once the evidence is in, A4's errors are mostly reasoning: on Llama
  37 of its 48 wrong answers had every gold section in context.
- Hand-check of 20 traces (10 per member): rows 11 to 20 (Member B, 7 A4 and 3 A2): 3 right verdicts (2 of them citing the wrong section or
  for the wrong reason), 2
  wrong_section_retrieved, 1 missed_exclusion, 4 other (2 over-cautious insufficient_info, 1 pre-existing-condition
  eligibility question, 1 "cover not stated" read as not covered). Example: Llama A4 on fwd-080 had the medical
  benefit and the definition of accident in context, yet asked whether a diving injury was accidental and answered
  insufficient_info. [Rows 1 to 10, Member A.]

### 7.8 By category

[Figure: `accuracy_by_category.png`.]

[Two sentences: where the agents help most (expected: needs_exclusion / needs_definition) and where every setup
struggles (expected: tricky, insufficient_info). Note cells with few claims.]

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
context of about 18 sections against A0's 4) but often fails to quote them accurately. gpt-oss reads the same kind of
context without that loss. Faithfulness is not part of the decision rule; it feeds the grounded rate in 7.7.

**Judge vs human.** Member B checked 30 random judgments per model (fixed seed) against the policy text. Agreement
was 77% on Llama (Cohen's kappa 0.64) and 80% on gpt-oss (kappa 0.52). In 11 of the 13 disagreements the judge was
stricter than the human, mostly "partly" where the human said "yes" because an explanation left out a condition
without misstating it. Read the faithfulness numbers as a lower bound. The judge checks the explanation against the
cited text only, not against the verdict. In the 60 hand-checks one right answer (Llama A4, msig-051) had an
explanation that contradicts its own partially_covered verdict; the judge cannot catch this pattern.

### 7.10 Retrieval only: can one search find the evidence? (5.6)

[Table: `results/test/retrieval/retrieval.md`.]

- Gold recall at k = 5: dense [x], BM25 [x], hybrid [x]; dense matches A0's evidence recall ([x]), as expected.
- By section type: benefits [x], definitions [x], exclusions [x]. [One sentence: if definitions and exclusions are
  rarely found by searching with the claim, that is the gap A4 closes by looking them up by structure.]
- [One sentence: would hybrid search have helped A0, and does it matter given that most agent errors were reasoning
  failures (7.7)?]

### 7.11 Dev vs test

Dev (20 claims) suggested [gpt-oss A4 best, 0.80]. Test [confirms / does not confirm] this. [One sentence on why
dev numbers were not used for any reported claim.]
