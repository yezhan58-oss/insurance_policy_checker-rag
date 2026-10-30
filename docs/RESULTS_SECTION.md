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

- Process vs outcome: sound rate [values] vs verdict accuracy [values]; right without evidence [counts per setup].
  Grounded rate (sound and judged faithful): [values]. [One sentence on whether the accuracy ranking survives when
  only sound answers count.]
- Evidence recall: [values per setup × model]; B0 is 0 by design.
- Wrong answers split into missing evidence (retrieval failure) vs had evidence (reasoning failure): [counts].
- Step quality: A2 grader precision [x] vs search [x]; A4 exclusion step recall [x]. [One sentence on which step
  limits each agent.]
- Hand-check of 20 traces (10 per member): [error-type counts]; [one example trace in two sentences].

### 7.8 By category

[Figure: `accuracy_by_category.png`.]

[Two sentences: where the agents help most (expected: needs_exclusion / needs_definition) and where every setup
struggles (expected: tricky, insufficient_info). Note cells with few claims.]

### 7.9 Faithfulness (Member B)

[Haiku judge results per setup × model; agreement with the 30 human checks.]

### 7.10 Dev vs test

Dev (20 claims) suggested [gpt-oss A4 best, 0.80]. Test [confirms / does not confirm] this. [One sentence on why
dev numbers were not used for any reported claim.]
