# Discussion notes (joint section, both members)

Points to weave into the discussion once the test results are in. Not report text yet.

- **Where the errors are.** If most wrong answers had the evidence in context (7.7), better retrieval (hybrid search,
  re-ranking) is not the next step; the 5.6 retrieval-only analysis shows how much it could add at most.
- **What would come next: the customisation ladder.** We stopped at prompting plus retrieval. Policy wording changes
  between versions, so it belongs in retrieval, not in model weights. The remaining errors are reasoning ("behaviour")
  gaps, which is where fine-tuning helps; with a verdict that can be checked automatically, reinforcement fine-tuning
  with a verifiable reward (for example GRPO) fits the task. 156 labelled claims are too few, and using them would
  consume the test set, so this is future work.
- **Long context vs retrieval (if L0 runs).** Two policies of 35k and 52k tokens fit in one prompt; whether reading
  everything beats retrieving the right parts, and at what token cost, answers "is RAG needed here at all?".
- **Deployment and privacy.** Both tested models run on university hardware, so a claim answered by the system never
  leaves it. The judge is the only external API: it sees the claim, the model's explanation and the cited policy
  text. That is acceptable here because our claims are synthetic; a real deployment would judge offline or in-house.
- **Limitations.** One labeller per claim outside the 40 blind-checked ones (kappa 0.46); 124 test claims detect only
  fairly large differences; two travel policies from one market; seconds depend on cluster load.
