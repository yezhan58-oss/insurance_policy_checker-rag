# Report draft: Discussion (both members, first draft by Member B)

Every number is from `results/test/report/leaderboard.md` (test split, 124 claims, commit b80d7c3) unless marked
otherwise. Rewrite in your own words before submitting.

## 8. Discussion

### 8.1 Answer to the research question

Neither agentic approach gave a significantly more accurate verdict than simple RAG on either model. A4 had the highest
accuracy among the pre-registered setups (0.61 vs A0's 0.56 on Llama, 0.71 vs 0.69 on gpt-oss), but McNemar does not
separate it from A0 (p = 0.38 and 0.88). A2 was no better than A0 on Llama (0.60) and worse on gpt-oss (0.62). Both
agents cost more: A4 takes about 2.6 to 2.8 times A0's latency and 2 to 2.5 times its tokens; A2 on gpt-oss takes 4.8
times A0's latency (27.6 s vs 5.8 s). On accuracy alone, the gain is not worth the cost, so the decision rule picked
A0 on both models.

Retrieval itself helped only the larger model. On gpt-oss, A0 beat B0 (0.69 vs 0.46, Holm p = 0.001); on Llama the
two were not separated (0.56 vs 0.54). The 8B model guesses a verdict about as well without the policy as with five
chunks of it, which points to reading the evidence, not finding it, as its main limit.

### 8.2 Better evidence did not become better verdicts

A4 does what it was designed to do. Its evidence recall is 0.91 (Llama) and 0.84 (gpt-oss) against A0's 0.66, and its
sound rate (right answer with every gold section in context) is 0.54 and 0.62 against 0.35 and 0.44. A0 gets more
answers right without the evidence to support them. So A4's answers are better justified even where its accuracy is
not higher. On gpt-oss its explanations are also the most faithful (0.68) and it has the highest grounded rate (0.48).

The gap between process and outcome comes from reasoning. On Llama, 37 of A4's 48 wrong answers had every gold section
in context. A4's typical errors are over-cautious insufficient_info (10 on Llama, 12 on gpt-oss) and all-or-nothing
answers to partially_covered claims (12 on Llama). A0's typical error is wrong_section_retrieved (22 and 19). A4
removes most retrieval failures and moves the bottleneck to the model's reading of a large context (about 18 sections
against A0's 4). Llama 8B handles that context poorly: its A4 explanations are the least faithful of the retrieval
setups (0.29).

### 8.3 The model matters more than the strategy

The model changed accuracy more than any retrieval strategy did. The most striking case is L0 (exploratory: the whole
policy in the prompt). gpt-oss reached 0.76, the highest accuracy of any run, while Llama fell to 0.32. A model that
can read 35k to 52k tokens reliably needs little retrieval on a corpus this small. A model that cannot read that much
depends on retrieval to cut the context down. The CRAG-style loop also depends on the model: gpt-oss's grader and
rewrites lowered accuracy by 7 points against A0 and took the most time of any setup.

### 8.4 A gap in the decision rule: safety

The rule checks safety only against A0, so when A0 wins on the tie-break, nothing checks whether a costlier setup is
safer. Afterwards, A4 is clearly safer on gpt-oss: A0 said covered on 9 of the 53 not_covered claims, A4 on 1 (exact
paired p = 0.021; exploratory, not Holm-corrected). On Llama the gap is smaller and not significant (7 vs 4,
p = 0.45). For an insurance user, a wrong "covered" is the costliest error, because they may spend money expecting a
payout. A real deployment should add a safety check to the tie-break, for example by preferring the setup with the
lower wrong-covered rate when accuracy is tied. Under that rule, A4 would have won on both models (wrong-covered 0.02 vs 0.17 on gpt-oss, 0.08 vs 0.13 on Llama). We kept the pre-registered
rule for the demo and show A4 as a toggle.

### 8.5 Limitations

- **Gold labels.** Blind agreement between the two labellers was moderate (kappa 0.46 four-way). Disagreements were
  resolved against the policy text, but the verdict boundaries (especially insufficient_info vs not_covered) remain
  open to reading. Some of A4's "over-cautious" errors could be fair readings.
- **Power.** With 124 claims, the 95% CIs are about 16 points wide, so McNemar needs a large gap to separate two setups [check: minimum detectable gap]. The 2 to 5 point gains
  we saw may be real but are too small to detect.
- **Scope.** Two policies from two Singapore insurers, one embedding model, and two open models of 8B and 20B
  parameters. The results may not hold for larger models, other policy styles or real claims written by customers.
- **One run.** Each setup ran once at temperature 0. vLLM is not fully deterministic, so a rerun could change a few
  answers.
- **Judge.** The Haiku judge was stricter than the human in 11 of 13 disagreements, so faithfulness is a lower bound.
  It checks the explanation against the cited text, not against the verdict.

### 8.6 Future work

- Make A4's definitions step find terms the claim implies, not only terms it names (fwd-059: "serious public event").
- Add a step that checks for a sub-limit or partial cover before the verdict, to reduce all-or-nothing answers.
- Test hybrid search for A0, since most of its errors are retrieval failures.
- Pre-register a safety-aware tie-break.
