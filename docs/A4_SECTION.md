# Report draft: A4 claims-workflow agent (Member B)

Placeholders in [brackets] are filled after the final test runs.

## A4: claims-workflow agent

A2 is a generic self-correcting retriever. A4 instead follows the order in which a claims assessor reads a policy: find the benefit the claim falls under, check what its key terms mean, check what is excluded, then decide. It is a fixed LangGraph graph of four nodes, run in the same order for every claim, with no loops:

1. **Benefits.** The model is shown the claim and the titles of every benefit section in the policy (in effect its table of contents) and picks the section(s) the claim would be made under, at most 3. We list titles rather than search because embedding search alone missed the obvious section on dev, for example FWD's overseas medical expenses for plain medical claims.
2. **Definitions.** Defined terms that appear in the claim or the chosen benefit text are found by lookup against the policy's definitions index (built at ingest), and up to 6 definitions are fetched. This step needs no model call.
3. **Exclusions.** All exclusions that apply to the chosen benefits are gathered: general exclusions, plus section-specific ones (MSIG groups its exclusions by benefit number, e.g. "exclusions for sections 32 to 37"). The model then keeps those that could affect the claim given the stated facts.
4. **Decide.** The shared answer call, with the same base prompt as every other setup, over everything gathered.

The two pick calls use JSON-schema structured output; IDs the model invents are dropped. If a pick reply is unusable, the node falls back to a fixed rule (the top benefit search hit; all candidate exclusions) and logs the fallback, so one bad call never stops a claim. Every node appends to `steps`, which drives both the demo's trace view and the trace evaluation. A4 makes at most 3 model calls per claim (2 picks and 1 answer), plus a retry if the answer fails to parse.

A4 is the approach we built for this domain. Its design bet is that the main failure of simple RAG on policies is missing evidence: the deciding definition or exclusion sits far from the benefit text and is not similar to the claim wording, so one similarity search does not find it. On dev, A4 brought the needed sections into context far more often than simple RAG (evidence recall 0.95 on Llama, versus [0.62, check against A's A0 dev traces] for A0).

## Development on dev

All tuning used the 20 dev claims on Llama 3.1 8B. Each change was tested with a rule fixed before the run: keep it only if dev accuracy and wrong-covered rate did not get worse.

- **Checklist step (dropped).** We tried an extra step that asked the model to list the facts the decision depends on before answering. Dev accuracy moved from 10/20 to 11/20, but time per claim rose from about 10 s to 35 s [from session notes of 19 Oct; result files not kept]. One claim on 20 is within noise, so the step was dropped for its cost.
- **Tighter exclusion pick (not adopted).** Traces showed Llama over-selecting exclusions: on average it kept 13.2 per claim (precision 0.03), giving 21.1 sections of context, 93% of them not needed. Since 9 of its 10 wrong dev answers had all the gold evidence in context, we tested whether this excess context caused the errors. A prompt asking for only exclusions whose conditions are met cut exclusions to 1.9 per claim with no loss of exclusion recall (1.00) and context to 9.9 sections, but accuracy did not improve (9/20 versus 10/20 on Llama; 0.75 versus 0.80 on gpt-oss-20b; wrong-covered 0.00 throughout). It failed the rule on both models, and the original prompt was kept.

The lesson from both trials is the same: once A4 has fixed retrieval, Llama's remaining errors on dev are reasoning failures with the evidence already in context, and neither more structure nor less context fixed them.

## Results on test

[A4 accuracy, wrong-covered rate and clause recall per model, with 95% CIs; McNemar vs A2 and vs A0.]

[Trace evaluation: per-step recall/precision for benefits and exclusions; wrong answers split into missing_evidence vs had_evidence; tokens, latency and context size against A0 and A2.]

[Hand-checked traces: 5 A4 traces from the Llama test run (seed 42), error types.]
