# Report draft: Method, Evaluation design, Development (Member A)

Draft for sections 4, 5 and 6 of the report outline. Every number comes from the repo (configs, `docs/PROMPT_TUNING.md`,
`docs/A2_DEV.md`, `docs/A4_DEV.md`); rewrite in your own words before submitting (course AI policy). Placeholders are
in [brackets]. Section 4.5 (A4) and 6.3 (A4 trial) are Member B's.

## 4. Method

### 4.1 Architecture

[Figure: ingest (PDF → sections → chunks → embeddings) → one shared Chroma index → B0 / A0 / A2 / A4 → one shared
answer call (base prompt, JSON schema) → evaluation (score, traces, judge) → report.]

All four setups are plug-ins behind one interface: each receives a claim, the model client and the policy store, and
returns the same structured output (verdict, cited section IDs, explanation, a step-by-step trace, and usage counts).
The evaluation code never needs to know which setup produced an answer.

### 4.2 A controlled comparison

The setups differ only in how they find policy text. Everything else is shared: the same base prompt, the same
embedding model (BAAI/bge-small-en-v1.5, run on CPU so results are identical on every machine), the same index, the same
model per comparison, temperature 0, and the same final answer call. The base prompt states the four verdicts and five
rules taken from the labelling guide (for example, an exclusion that clearly applies beats a benefit, and a stated
fact that fails a condition gives not_covered while a missing fact gives insufficient_info), so the models are judged
by the rules the human labellers used. A unit test fails if the labelling guide changes without the prompt being
re-checked against it. The answer is forced into a JSON schema; an unparseable reply, or one cut off at the
4,096-token limit, is retried once and otherwise recorded as a parse error, which counts as wrong.

### 4.3 Baselines: B0 and A0

**B0 (no retrieval)** gets the claim and no policy text, and answers from the model's general knowledge. It is the
floor: any gain over B0 is due to retrieval. **A0 (simple RAG)** searches the claim's policy once with the claim text
and answers from the top 5 chunks. It is the standard RAG baseline the agents must beat.

**L0 (long context, exploratory)** puts the whole policy into the prompt (every section in document order, each with
its section ID: about 28k tokens for FWD and 45k for MSIG (measured on test)) with the same base prompt and answer call, and no
retrieval. It tests the simpler alternative to RAG for a small, fixed corpus: can the model simply read everything?
L0 was added on 30 Oct, after the comparisons were pre-registered, so it is reported as exploratory: its McNemar tests
against A0 and the best agent are uncorrected and outside the Holm family, and it can never be chosen by the decision
rule. It runs on a server with a longer context window (131k tokens instead of 16k); everything else is unchanged.
Because the whole policy is always in context, every right L0 answer counts as *sound* (5.4), so its process check is
the grounded rate (the judge). vLLM reuses the cached policy prefix across claims, so L0's seconds per claim understate
the cost of a cold start; its token counts show the full cost.

### 4.4 A2: Corrective RAG

A2 adapts Corrective RAG (Yan et al., 2024) to a closed policy corpus. It is a LangGraph graph with one loop:

[Figure: START → search → grade → route → decide → END, with route → rewrite → search.]

1. **Search** the policy for the current query (initially the claim text), top 5 chunks.
2. **Grade:** the LLM sees the claim and the numbered chunks and returns the numbers of the relevant ones. Relevant
   chunks are added to a pile that persists across searches.
3. **Route:** if fewer than 2 chunks are relevant and fewer than 2 rewrites have been used, rewrite; otherwise decide.
4. **Rewrite:** the LLM writes a new query in the policy's own wording (for example "baggage theft" rather than the
   claimant's story), seeing every earlier query so it does not repeat one.
5. **Decide:** the shared answer call over the relevant chunks only.

Design decisions:

- **One grading call per search** instead of one per chunk as in the paper, to keep latency acceptable for a user
  waiting for an answer.
- **Exclusions count as relevant.** The grading prompt says text that would stop the claim being paid is relevant.
  A grader that kept only supporting text would filter out exclusions and push the model towards "covered", the
  unsafe error.
- **Grade against the claim, not the rewritten query,** so relevance always means relevance to what was asked.
- **Numbered chunks** rather than long section IDs, which a small model copies unreliably.
- **Fail safe:** an unusable grading reply keeps every chunk (the claim then behaves like A0); an unusable rewrite
  keeps the old query; a rewrite that repeats an earlier query ends the loop, since it would return the same chunks.
- **No fallback to ungraded chunks:** if nothing is graded relevant after both rewrites, the answer sees no policy text
  rather than chunks already judged irrelevant.

Differences from the paper: the paper's fine-tuned T5 evaluator is replaced by the LLM itself, and its web search
for poor retrievals by a rewritten search of the same policy, since the answer must come from the policy wording.

### 4.5 A4: Claims-workflow agent (Member B)

A2 is a generic self-correcting retriever. A4 instead follows the order in which a claims assessor reads a policy:
find the benefit, check what its key terms mean, check what is excluded, then decide. It is a fixed LangGraph graph of
four nodes, run in the same order for every claim, with no loops:

1. **Benefits.** The model sees the claim and the titles of every benefit section in the policy (in effect its table
   of contents) and picks at most 3. We list titles rather than search because embedding search alone missed the
   obvious section on dev, e.g. FWD's overseas medical expenses for plain medical claims.
2. **Definitions.** Defined terms in the claim or the chosen benefit text are matched against the policy's definitions
   index (built at ingest), and up to 6 definitions are fetched. No model call.
3. **Exclusions.** All exclusions that apply to the chosen benefits are gathered: general exclusions plus
   section-specific ones (MSIG groups exclusions by benefit number, e.g. "exclusions for sections 32 to 37"). The
   model keeps those that could affect the claim given the stated facts.
4. **Decide.** The shared answer call, with the same base prompt as every other setup, over everything gathered.

The two pick calls use JSON-schema structured output; section IDs the model invents are dropped. If a pick reply is
unusable, the node falls back to a fixed rule (the top benefit search hit; all candidate exclusions) and logs it, so
one bad call never stops a claim. Every node appends to `steps`, which drives the demo's trace view and the trace
evaluation (5.4). A4 makes at most 3 model calls per claim (2 picks and 1 answer), plus a retry if the answer fails to
parse.

Its design bet is that simple RAG fails on policies mainly from missing evidence: the deciding definition or exclusion
sits far from the benefit text and does not resemble the claim wording, so one similarity search misses it.

### 4.5b A3: ReAct tool agent (exploratory, added 4 Nov)

A3 lets the model choose its own lookups (ReAct; Yao et al., 2023). At each step it writes a short thought and one
action: search the policy with a query of its choice, get the definition of a term, get the exclusions of a benefit
section, or answer. It has the same tools as A4, so it can reach the same evidence; the difference is that A4 runs
them in a fixed order and A3 decides for itself. The prompt lists the tools but not an order, because whether a free
agent thinks of definitions and exclusions on its own is what A3 tests. An unknown term returns the list of defined
terms, so the agent can correct itself. After at most 8 lookups, or an unusable reply, the agent stops, and the
shared answer call decides over every section it looked at. Actions are written as JSON rather than native tool
calls, so both models run A3 the same way. A3 was added after the test results, so it is exploratory, like L0.

### 4.6 Models and infrastructure

We compare a small instruction model, Llama 3.1 8B Instruct, with a larger open reasoning model, gpt-oss-20b, both
served with vLLM 0.31 on NVIDIA A40 (48 GB) GPUs of the SMU SCIS cluster through SLURM batch jobs. Both run free on
university hardware, so cost is measured as model calls, tokens and seconds per claim rather than dollars. Seconds
depend on cluster load, so latency is compared within one run, not across runs. Faithfulness is judged by Claude
Haiku 5.5, from a different company than both tested models.

Decoding is greedy (temperature 0, fixed seed). vLLM can still return slightly different answers to identical
requests; on dev, the kept prompt run twice with Llama and A0 gave identical verdicts (6.1), but a rerun of the test
set could move a few claims. Calls are made one at a time, without batching, so seconds per claim are measured the same way for every
setup. Llama runs in 16-bit precision, while gpt-oss-20b is released with 4-bit (MXFP4) expert weights, so the model
comparison also spans a difference in precision.

**Contamination.** The test claims were written for this project and have never been public, so no model can have
seen them. The policy versions used (FWD, April 2024; MSIG, September 2025) are newer than Llama 3.1's training cutoff
(December 2023); gpt-oss-20b's cutoff (June 2024) falls after the FWD version, so it may have seen that wording, though
insurers also reuse wording across versions. B0, which sees no policy text, measures what each model brings from
training.

## 5. Evaluation design

### 5.1 Metrics

| Metric | What it measures |
|---|---|
| Verdict accuracy (main) | verdict equals the gold verdict |
| Binary accuracy | paid (covered or partially) vs not paid matches gold |
| Wrong-covered rate (safety) | share of gold not_covered claims answered covered or partially_covered |
| Clause recall | share of gold sections that the answer cites |
| Faithfulness | LLM judge: is the explanation supported by the cited text (yes / partly / no); [N] judgments hand-checked |
| Cost | mean model calls, tokens (including reasoning tokens) and seconds per claim |

### 5.2 Statistics

Every metric has a 95% bootstrap confidence interval (1,000 resamples, fixed seed). Setups are compared with exact
McNemar tests on per-claim correctness, which suit paired classifiers on the same test set (Dietterich, 1998). Three
comparisons were fixed in advance: best agent vs A0, A0 vs B0, and A2 vs A4, with Holm correction.

### 5.3 Decision rule (fixed before the test run)

The best setup is the one with the highest test accuracy whose wrong-covered rate is no worse than A0's. If McNemar does
not separate the top two, the cheaper and faster one wins. The rule puts safety ahead of accuracy and prefers a
simpler system unless the gain is real.

### 5.4 Trace evaluation

Following feedback that the agents' tool use should be evaluated, not only their verdicts, `src/eval/traces.py` scores
each setup's recorded steps against the gold sections, with no extra labelling:

- **Step correctness:** recall and precision of each step (for example A2's grader, A4's exclusion picker) against
  the gold sections of that type.
- **Evidence recall:** share of gold sections that reached the final answer's context.
- **Failure split:** each wrong answer is classed as *missing evidence* (a gold section never reached the model: a
  retrieval failure) or *had evidence* (all gold sections were present: a reasoning failure).
- **Citation checks (in code, before any judge):** every cited section ID is checked against the policy and against
  what the model was shown. An ID that does not exist in the claim's policy is *invalid* (made up); one that exists
  but never reached the model is *unseen* (cited from memory or a guess). We report the share of cited IDs that exist
  and the share that were in context. Unlike faithfulness, these need no judge and cost nothing.
- **Process vs outcome:** a right verdict can come from a broken process, so right answers are split the same way:
  *sound* (every gold section reached the model) or *right without evidence* (a lucky guess or prior knowledge). The
  **sound rate** (sound answers / all claims) is a stricter accuracy that credits only right answers from a working
  process; the **grounded rate** further requires the judge to rate the explanation faithful. B0 never sees policy text,
  so every right B0 answer is right without evidence by design, which makes B0 the reference for how often a verdict is
  right by chance or prior knowledge.
- **Efficiency:** context size, share of context not needed, calls, tokens, seconds, parse retries.

Twenty agent traces from the test run (5 each from A2 and A4 on both models, fixed seed) are also hand-checked by both
members using the brief's error types.

### 5.5 Data discipline

All tuning used the 20 dev claims. The test set was frozen on 28 Oct and scored once, from one commit ([hash]), by
one person.

### 5.6 Retrieval-only analysis

To see whether a single search can find what a claim needs, `src/eval/retrieval.py` searches each test claim's policy
with the claim text and measures how many gold sections are found, with no model call: the embedding search all setups
use (dense, exactly A0's search at k = 5), BM25 keyword search over the same chunks, and a hybrid of the two (reciprocal
rank fusion). Recall is also split by the type of gold section, because claims name the benefit they fall under but
rarely the defined terms or exclusions that decide them. This is analysis only: no setup uses BM25 or the hybrid.

## 6. Development and tuning

All changes below were tested on dev only. For each trial the acceptance rule was written down before running: keep
the change only if accuracy and wrong-covered rate are no worse on both models.

### 6.1 Prompt tuning (Llama 3.1 8B, A0, dev)

The first dev run showed Llama never answering insufficient_info (0/5) and rarely partially_covered (1/4). Three
prompt changes were tried: a step-by-step checklist (accuracy 0.45 vs 0.50 for the original), the same checklist with
a reasoning field placed before the verdict in the JSON schema (0.50, but insufficient_info was now predicted 12 times
out of 20 and not_covered fell from 6/6 to 3/6), and narrower rules (0.40). The reasoning-first prompt was also
unstable: run twice at temperature 0 it changed 5 of 20 verdicts, while the original prompt run twice changed none.
We kept the original prompt. gpt-oss-20b already handled these verdicts with the same prompt (insufficient_info 3/5
with A0 and 5/5 with A4), which points to a model limitation rather than a prompt problem.

### 6.2 A2: rewrite threshold

On dev, A2's grader raised the share of useful chunks from 0.20 to 0.72 on gpt-oss (0.18 to 0.37 on Llama) and never
dropped a gold section the search had found. Rewriting was used on 11 of 20 claims by gpt-oss but found a new gold
section in only 2, and 5 of its 17 rewrites repeated an earlier query, which led to the repeated-query stop. Lowering
the threshold from 2 relevant chunks to 1 made gpt-oss about 2.7 times faster (9.9 vs 26.9 s per claim) but less
accurate (0.60 vs 0.70) and less safe (wrong-covered 0.17 vs 0.00), so it failed the rule and the threshold stayed
at 2. With 20 claims these gaps are within noise, so we report a trade-off, not a proven effect.

### 6.3 A4: exclusion step (Member B)

Traces showed A4 on Llama fixed retrieval (evidence recall 0.95 on dev, versus 0.62 for A0) but not accuracy: 10/20,
the same as A0, and 9 of its 10 misses had all gold evidence in context. Llama also over-selected exclusions (13.2 per
claim, precision 0.03; 93% of the 21.1 context sections not needed), so we tested whether the excess context caused
the errors. A prompt asking only for exclusions whose conditions are met cut exclusions to 1.9 per claim with no loss
of exclusion recall (1.00) and context to 9.9 sections, but accuracy did not improve (9/20 vs 10/20 on Llama; 0.75 vs
0.80 on gpt-oss-20b; wrong-covered 0.00 throughout). It failed the rule on both models, and the original prompt was
kept. An earlier checklist step (list the deciding facts before answering) gave 11/20 vs 10/20 but raised time per
claim from about 10 s to 35 s, and was dropped for its cost. Both trials point the same way: once A4 has the evidence,
Llama's remaining errors are reasoning failures that neither more structure nor less context fixed.

### 6.4 Engineering fixes found by validation

- A reply that ran into the token limit raised an exception and stopped runs; it is now retried and then scored as a
  parse error like any other unusable reply.
- Two batch jobs rebuilding the same index on the shared file system corrupted it; each job now builds its index on
  the node's local disk.
- The prompt's rules had drifted from the labelling guide; a test now ties the prompt to a hash of the guide.
- Runs are resumable and record the commit and full prompt next to the results, and the test split refuses to run on
  uncommitted code.
