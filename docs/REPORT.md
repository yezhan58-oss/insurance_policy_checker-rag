<!-- Synced from the shared report doc on 11 Nov 2026 (the doc is the working copy). -->

# Is the agent worth it? Agentic RAG for travel insurance coverage verdicts

IS469 Generative and Agentic AI, group project. Member A: Ye Zhan. Member B: Liang Than. Code, data and results: [github.com/yezhan58-oss/insurance\_policy\_checker-rag](https://github.com/yezhan58-oss/insurance_policy_checker-rag)

## Abstract

A travel insurance claim is rarely decided by one clause. The benefit is in one place, the definition it depends on is at the back of the policy, and the exclusion that cancels it can be many pages away. We wanted to know whether agentic retrieval handles this better than simple RAG, and whether any improvement is worth what it costs. 

We took two real Singapore policies (FWD and MSIG), wrote 124 test claims with human-checked labels, and compared these setups on Llama 3.1 8B and gpt-oss-20b: 

1. No retrieval (No-RAG)
2. simple RAG (RAG)
3. corrective RAG (CRAG) 
4. claims-workflow agent (Agent)
5. ReAct agent (ReAct), which chooses its own lookups, added after the core runs; plus a whole-policy baseline (Full-context) as an exploratory extra

The two agents were the most accurate (workflow agent 0.61 and 0.71, ReAct 0.61 and 0.76, against 0.56 and 0.69 for simple RAG), and the workflow agent found much more of the evidence a claim needs (0.91 and 0.84, against 0.66). 

None of these gaps was statistically significant, so on accuracy alone the agents are not worth their extra cost, and the rule we fixed before testing picks simple RAG (section 7.2 shows how adding ReAct later shifts its tie-break). What the workflow agent did change was the kind of mistake: its errors moved from retrieval to reasoning, and on gpt-oss it called a "not\_covered" claim covered only once in 53, where simple RAG did so 9 times. Our demo therefore runs simple RAG behind guardrails and offers the agent as a second opinion.

## 1. Introduction

Someone whose flight was delayed by a typhoon has one question: can I claim? The answer is in the policy wording, but it is almost never in a single place. The benefit sets a threshold (6 hours of delay), a definition narrows one of its terms ("scheduled public transport"), and a general exclusion somewhere else can take the cover away. A model that reads only the benefit can end up promising a payout the policy does not actually make.

Retrieval-augmented generation (RAG) lets a language model answer from the policy itself. The weakness is that a single search **using the claim's own words** finds what the claim mentions, which is not always the rule that decides it. Agentic RAG tries to fix this by **adding steps that check the evidence and go looking for more**. Those steps are paid for in model calls, tokens and seconds, so we care about two things: **do they help, and is the help worth the price.**

**Research question ->** Which agentic RAG approach gives the most accurate and best-justified coverage verdicts on real insurance policies, and is the gain worth the extra cost and latency compared with simple RAG?

The study combines two course topics: agentic RAG (Topic 8: simple RAG, query rewriting, long context, hybrid search, faithfulness evaluation) and LLM agents (Topic 7: our workflow agent is a Plan-and-Execute agent, ReAct the step-by-step loop).

This report contributes 4 things:

1. A controlled comparison of four setups (no retrieval, simple RAG, corrective RAG and a domain workflow agent) on two models that differ in size and style. All four share one index, one prompt and one answer call. The rule for picking a winner was fixed before the test run, and the paired tests are Holm-corrected.
2. A trace evaluation that scores every step an agent takes against the gold sections. It sorts each wrong answer into a retrieval failure or a reasoning failure, and it reports a "sound rate" that only counts a right answer when the evidence was actually there.
3. A dataset of 144 claims, drafted by an LLM from specific clauses and then hand checked by us.
4. A brief demo built on the winning setup, with guardrails in-place.

## 2. Related work that we referenced

**Retrieval-augmented generation.** RAG gives a language model passages fetched from an outside corpus when it answers (Lewis et al., 2020). Our simple RAG setup is the plainest version of this: one search with the claim text, five chunks, one answer. Policy wordings are a hard case for it, because the text that decides a claim is spread out and a single search rarely brings back the benefit, the definition and the exclusion together.

**Corrective and self-reflective retrieval.** Corrective RAG (CRAG; Yan et al., 2024) grades the passages it retrieves and, when they look weak, rewrites the query or falls back to web search. Self-RAG (Asai et al., 2024) goes further and trains the model to decide when to retrieve and to critique its own output. Our corrective RAG setup follows CRAG, with two changes: an LLM does the grading in place of the fine-tuned evaluator, and there is no web search because our corpus is closed.

**Tool-using agents.** ReAct (Yao et al., 2023) lets a model mix reasoning with tool calls and choose for itself what to look up next. Our plan had flagged tool calling on an 8B model as a risk, so we only built a ReAct agent after the core study, as an exploratory setup. Our workflow agent takes the opposite route. It is a fixed LangGraph workflow that reads a policy the way a claims assessor would, so the domain knowledge is in the graph and not in the model's choices.

**Long context instead of retrieval.** Li et al. (2024) find that long-context models can beat RAG when resources allow, although RAG is far cheaper. Models are also known to use information in the middle of a long prompt less well than information at the start or end (Liu et al., 2024). Our exploratory whole-policy setup tests the first finding. We could not test the second, because in our data the position of a clause and the category of the claim go together.

**LLM as a ****judge.** Strong LLMs can grade open-ended answers almost as consistently as human raters, though with known biases such as favouring their own outputs (Zheng et al., 2023). Our judge is **Claude Haiku 5.5**, which comes from a different company than both tested models, and we checked its grades against human labels.

## 3. Data and Policy used

We used two public Singapore travel policy wordings, **FWD Travel Insurance **(April 2024, 45 pages) and **MSIG TravelEasy** (70 pages, 52 benefit sections). We downloaded them on 16 and 17 Oct 2026 and committed them with their SHA-256 hashes. The two are laid out differently. FWD keeps its definitions at the back and prints its benefit tables as images, which we transcribed by hand, while MSIG points from each benefit to its general exclusions by number.

**Ingestion.** Each policy is split along its own headings. This gives 284 sections (FWD 131, MSIG 153), each with a stable ID such as `fwd:travel_delay` and a type: benefit (93), definition (66), condition (56), exclusion (46) or other (23). Sections longer than 500 words are cut into chunks of about 400 words with a 50-word overlap, which gives 323 chunks that all keep their section ID. Defined terms also go into a lookup table. Ingestion is deterministic, so every machine builds the same index.

**Claims.** Real claims are not public, so we built 156 of our own. An LLM was given one clause at a time and asked to write a short first-person claim aimed at a chosen verdict, and to record that intended verdict and the sections that decide it. The claims come in sets around one clause, so that a small change flips the answer: a 7-hour delay is covered, a 4-hour delay is not, and "my flight was delayed" is "insufficient\_info". Every claim has a verdict ("covered", "not\_covered", "partially\_covered" or "insufficient\_info") and a category (single\_section, needs\_definition, needs\_exclusion or tricky).

**Labelling.** If we graded models against an LLM's own drafts, the results would be biased, so no draft became a gold label until a human had reviewed it. We wrote a one-page labelling guide covering the verdict definitions, the default assumptions and tie-break rules such as "an exclusion that clearly applies beats a benefit". We then checked every draft against the clause text: 143 were accepted, 1 was corrected and 12 were deleted as repeats, which left 144. A fixed-seed split put 20 claims into a dev set for tuning and 124 into a test set that we scored once.

|  | Dev | Test |
| --- | --- | --- |
| Claims (FWD / MSIG) | 20 (10 / 10) | 124 (80 / 44) |
| covered / not\_covered / partially / insufficient | 5 / 6 / 4 / 5 | 46 / 53 / 14 / 11 |
| single\_section / definition / exclusion / tricky | 8 / 3 / 5 / 4 | 65 / 20 / 25 / 14 |

**Blind check.** We labelled 40 random test claims without seeing each other's drafts or labels. Agreement was moderate: 25 of 40 on the four-way verdict (Cohen's kappa 0.46, 95% CI 0.24 to 0.64) and 30 of 40 on covered versus not (kappa 0.50). 

In 39 of the 40 cases both of us picked at least one gold section in common, so the disagreement was about how to read a clause and not about which clause applies. We went through the 15 disagreements together against the policy text, added two rules to the guide, and froze the test set on 28 Oct.

## 4. Methods

![Architecture: one shared index, prompt and answer call; the setups differ only in how they find policy text.](figures/architecture.png)

### 4.1 A controlled comparison

Every setup gets the same three inputs (a claim, the model client and the policy store) and returns the same structured output: a verdict, the cited section IDs, an explanation, a step-by-step trace and usage counts. **Only the way policy text is found changes**. The base prompt, the embedding model (BAAI/bge-small-en-v1.5, run on CPU), the index, temperature 0 and the final answer call are shared by all of them.

The base prompt lists the four verdicts and five rules taken from the labelling guide, so the models are held to the same rules as the labelers. A unit test fails if someone changes the guide without re-checking the prompt. The answer has to fit a JSON schema. If a reply cannot be used, it is retried once and then scored as a wrong answer (a parse error).

### 4.2 The setups

All setups finish with the same answer call. What differs is which policy text that call gets to see and how it was found. In this report each setup goes by a short name; the repository and the results files use the code in the last column.

| Setup (short name) | How it finds the policy text | Model calls per claim (Llama / gpt-oss) | Repo ID |
| --- | --- | --- | --- |
| No retrieval (No-RAG) | It doesn't: the model answers from what it already knows | 1.0 / 1.1 | B0 |
| Simple RAG (RAG) | One search with the claim text, top 5 chunks | 1.0 / 1.0 | A0 |
| Corrective RAG (CRAG) | Search, grade each chunk, and rewrite the query and search again if too few are relevant | 2.5 / 2.8 | A2 |
| Workflow agent (Agent) | Fixed steps like a claims assessor: benefits, then definitions, then exclusions | 3.0 / 3.0 | A4 |
| Whole policy (Full-context) | No search: the whole policy goes into the prompt | 1.0 / 1.1 | L0 |
| ReAct agent (ReAct) | The model chooses its own lookups, one at a time | 7.9 / 3.4 | A3 |
| Agent with term picking (Agent-Pick) | The workflow agent, plus extra definitions the model picks | 4.0 / 4.0 | A4D |
| Simple RAG, 10 passages (RAG-10) | Simple RAG with 10 chunks instead of 5 | 1.0 / 1.0 | A0K10 |
| Safe mode (RAG + Check) | Simple RAG first; the agent re-checks any covered or partially covered answer | simple RAG's call + the agent's on 39 / 50 of 124 claims | none  (simulated) |

The call counts are measured means on the test set; a one-call setup can show slightly more than 1.0 because of retries. The first four setups were fixed before the test run. **ReAct was added on 4 Nov, after the core runs, and joins the main comparison; we report the decision rule both as planned and with ReAct included.** The other exploratory setups are scored but never compete.

**Pre-registered methods:**

1. **No retrieval (No-RAG):** The model sees only the claim, no policy text. This is the floor.
2. **Simple RAG (RAG):** One search with the claim text; the top 5 chunks go to the answer call.
3. **Corrective RAG (CRAG):** A LangGraph loop. It retrieves 5 chunks and the LLM grades which are relevant. If fewer than 2 are, the LLM rewrites the query in the policy's wording and searches again, at most twice. The answer uses only the relevant chunks. Exclusions always count as relevant, so the text that stops a payout is never thrown away.
4. **Workflow agent (Agent):** Built on the idea that simple RAG misses the deciding definition or exclusion because it uses different words from the claim. A fixed four-step LangGraph graph (at most 3 model calls). The model makes the choices inside each step, but the steps always run in this order:
   1. Pick up to 3 benefits from the list of benefit titles (the table of contents).
   2. Look up the defined terms used in the claim and those benefits (no model call).
   3. Collect the exclusions for those benefits and keep the ones that could apply.
   4. Answer from everything gathered.

**Added to the main comparison after the core runs:**

- **ReAct agent (ReAct)**, after Yao et al. (2023): the model decides what to look up. At each step it writes a short thought and picks one action (search the policy, get a definition, get a benefit's exclusions, or answer), with at most 8 lookups. It has the same tools as the workflow agent; the difference is that ReAct chooses its own order instead of following fixed steps.

**Exploratory methods:**

- **Whole policy (Full-context).** The whole policy goes in together with the user's prompt, every section with its ID. That is about 28k tokens for FWD and 45k for MSIG. It asks whether retrieval is needed at all on a corpus this small.
- **Agent with term picking (Agent-Pick).** In step 2 the model also picks up to 3 more definitions from the policy's list of defined terms, to catch terms a claim implies without naming them. It costs one more call than the agent.
- **Simple RAG, 10 passages (RAG-10).** Simple RAG with the top 10 chunks instead of 5. We added it after seeing the test results, to check whether simple RAG just needed more text.
- **Safe mode (RAG+Check).** Simple RAG answers every claim, and whenever it says covered, the agent double-checks and its answer is used. We worked this out from the answers both setups had already given on the test set, so no new runs were needed.

### 4.3 Models and infrastructure

We compare a small instruction model, **Llama 3.1 8B Instruct (16-bit)**, with a larger open reasoning model, **gpt-oss-20b (4-bit expert weights)**. 

Both are served with vLLM on A40 GPUs on the SMU cluster through SLURM batch jobs. They run free on SMU's hardware, so we measure cost in model calls, tokens and seconds per claim rather than dollars. Calls are made one at a time, so seconds are measured the same way for every setup.

**Why these two models:** they were the largest that fit on one 48 GB student GPU, and they differ in kind (a small standard model and a larger reasoning model), so we can see whether a result holds for both. Decoding is greedy with a fixed seed, but vLLM can still give slightly different answers on a rerun. The test claims were written after both models were trained, so neither could have seen them.

## 5. Evaluation design

Every test claim has a gold verdict and gold sections (the clauses that decide it). We ask three questions of every answer: is it right, is it right for the right reason, and what did it cost?

| Measure | What it tells us | Good score |
| --- | --- | --- |
| **Accuracy** (main) | Share of verdicts that match the gold verdict | High |
| **Wrong-covered rate** (safety) | Of the 53 not\_covered claims, the share answered covered or partially covered (a false-positive rate) | Low |
| **Clause recall** | Share of gold sections the answer cites | High |
| **Faithfulness** | Share of explanations a Claude Haiku judge rates fully supported by the cited clauses | High |
| **Evidence recall** | Share of gold sections that reached the model at all | High |
| **Sound rate** | Right verdict *and* every gold section in context | High |
| **Cost** | Model calls, tokens and seconds per claim | Low |

Wrong answers are also split into **missing evidence** (retrieval failed) and **had evidence** (the model read it and reasoned wrongly).

- **Statistics.** 95% bootstrap confidence intervals, and exact McNemar tests on per-claim correctness (Dietterich, 1998), which only count claims where one setup is right and the other wrong. Three comparisons were fixed in advance and Holm-corrected: best agent vs simple RAG, simple RAG vs no retrieval, and corrective RAG vs the workflow agent.
- **Decision rule**, written before the test run and applied to each model:
  1. Drop any setup whose wrong-covered rate is worse than simple RAG's.
  2. The most accurate remaining setup leads.
  3. If McNemar cannot separate the top two (p ≥ 0.05), the cheaper one wins.
- **ReAct**, added after the core runs, is reported both ways: under the rule as planned, and as a full candidate. **The other exploratory setups** are scored but never compete.
- **Human checks.** We checked 60 judge grades against the policy, labelled the error type of all 176 wrong simple RAG and agent answers, and read 20 agent traces step by step.
- **Retrieval only.** We searched each claim's policy with the claim text alone (dense, BM25 and hybrid, no model call) to see whether any single search could find the evidence.

## 6. Development

Tuning used only the 20 dev claims. A change was kept only if accuracy and the wrong-covered rate were no worse on both models. One dev claim is worth 5 points, so dev results only guided yes-or-no decisions.

- **Prompt.** Three variants were tried and none beat the original (0.45, 0.50 and 0.40, against 0.50). A reasoning-first variant also flipped 5 of 20 verdicts on a rerun; the original flipped none.
- **Corrective RAG threshold.** Rewriting only when no chunk was relevant (instead of fewer than 2) made gpt-oss 2.7× faster but less accurate (0.60 vs 0.70) and less safe, so we kept 2.
- **Agent exclusions** (Member B). A stricter prompt halved the context (21 to 10 sections) with no gain in accuracy, which showed Llama's errors come from reasoning, not context size. We kept the original.
- **Engineering fixes.** Replies cut off at the token limit are retried, then scored as errors. Each job builds its own index, after a shared one was corrupted. Runs resume after a crash and refuse to score the test set on uncommitted code.

## 7. Results

The four core setups and Full-context ran once per model over the 124 test claims: 1,240 answers, with 9 parse errors (all gpt-oss) scored as wrong. ReAct ran on 4 Nov, after the core runs, and is shown next to them; Agent-Pick and RAG-10 are in section 7.6.

### 7.1 Leaderboard

| Model | Setup | Accuracy \[95% CI\] | Wrong-covered | Evidence recall | Sound rate | Faithful | Calls | Tokens | Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Llama 8B | No-RAG | 0.54 \[0.46–0.62\] | 0.06 | 0.00 | 0.00 | 0.00 | 1.0 | 630 | 2.6 |
|  | RAG | 0.56 \[0.48–0.65\] | 0.13 | 0.66 | 0.35 | 0.38 | 1.0 | 2,635 | 3.4 |
|  | CRAG | 0.60 \[0.51–0.68\] | 0.17 | 0.66 | 0.38 | 0.41 | 2.5 | 4,339 | 4.3 |
|  | Agent | 0.61 \[0.53–0.69\] | 0.08 | 0.91 | 0.54 | 0.29 | 3.0 | 6,626 | 9.5 |
|  | ReAct (added later) | 0.61 \[0.53–0.69\] | 0.11 | 0.88 | 0.50 | 0.40 | 7.9 | 45,988 | 16.6 |
|  | Full-context (exploratory) | 0.32 \[0.24–0.41\] | 0.00 | 1.00 | 0.32 | 0.31 | 1.0 | 34,246 | 4.5 |
| gpt-oss-20b | No-RAG | 0.46 \[0.38–0.54\] | 0.23 | 0.00 | 0.00 | 0.00 | 1.1 | 1,700 | 9.1 |
|  | RAG | 0.69 \[0.61–0.77\] | 0.17 | 0.66 | 0.44 | 0.63 | 1.0 | 3,247 | 5.8 |
|  | CRAG | 0.62 \[0.53–0.70\] | 0.11 | 0.68 | 0.44 | 0.60 | 2.8 | 6,139 | 27.6 |
|  | Agent | 0.71 \[0.63–0.78\] | 0.02 | 0.84 | 0.62 | 0.68 | 3.0 | 6,476 | 15.2 |
|  | ReAct (added later) | 0.76 \[0.68–0.83\] | 0.08 | 0.77 | 0.56 | 0.72 | 3.4 | 8,263 | 11.3 |
|  | Full-context (exploratory) | 0.76 \[0.68–0.83\] | 0.13 | 1.00 | 0.76 | 0.42 | 1.1 | 40,842 | 18.0 |

- **The two agents were the most accurate:** ReAct and the workflow agent tie on Llama (0.61); on gpt-oss ReAct leads (0.76 against 0.71).
- **Retrieval mattered far more for the bigger model:** simple RAG beat no retrieval by 23 points on gpt-oss, but by only 2 on Llama.
- **The model mattered more than the method:** gpt-oss beat Llama by 13 points on simple RAG, while switching method added at most 6.

### 7.2 Significance and the winner

| Comparison | Llama: p (Holm) | gpt-oss: p (Holm) |
| --- | --- | --- |
| Agent vs RAG | 0.38 (1.00) | 0.88 (0.88) |
| RAG vs No-RAG | 0.71 (1.00) | <0.001 (0.001) |
| CRAG vs Agent | 0.86 (1.00) | 0.12 (0.24) |
| ReAct vs RAG (added later) | 0.36 | 0.18 (0.23 with ReAct as best agent) |

- **Only one comparison is significant:** retrieval beats no retrieval on gpt-oss. Neither agent is significantly more accurate than simple RAG, on either model.
- **The agents' lead is small:** 6 claims on Llama for both, and 2 (workflow agent) or 8 (ReAct) on gpt-oss. With 124 claims, a gap of about 14 to 16 points is needed to show up reliably.
- **Decision rule as planned: simple RAG wins on both models.** The workflow agent and simple RAG are the top two, they are not separated, and simple RAG needs one model call against three.
- **With ReAct included, the rule picks the workflow agent on both models.** ReAct and the workflow agent become the top two, are not separated (p = 1.00 on Llama, 0.43 on gpt-oss), and the workflow agent is cheaper.
- **So the formal winner depends on which setups are in the race,** because the tie-break only compares the top two. What holds either way: no agent is significantly more accurate than simple RAG.

### 7.3 Cost

| Model | Setup | Accuracy (vs RAG) | Calls | Tokens (× RAG) | Seconds (× RAG) | 1,000 claims |
| --- | --- | --- | --- | --- | --- | --- |
| Llama 8B | RAG | 0.56 | 1.0 | 2,635 (1×) | 3.4 (1×) | 1.0 h |
|  | CRAG | 0.60 (+3) | 2.5 | 4,339 (1.6×) | 4.3 (1.3×) | 1.2 h |
|  | Agent | 0.61 (+5) | 3.0 | 6,626 (2.5×) | 9.5 (2.8×) | 2.6 h |
|  | ReAct | 0.61 (+5) | 7.9 | 45,988 (17.5×) | 16.6 (4.8×) | 4.6 h |
| gpt-oss-20b | RAG | 0.69 | 1.0 | 3,247 (1×) | 5.8 (1×) | 1.6 h |
|  | CRAG | 0.62 (−7) | 2.8 | 6,139 (1.9×) | 27.6 (4.7×) | 7.7 h |
|  | Agent | 0.71 (+2) | 3.0 | 6,476 (2.0×) | 15.2 (2.6×) | 4.2 h |
|  | ReAct | 0.76 (+6) | 3.4 | 8,263 (2.5×) | 11.3 (1.9×) | 3.1 h |

- **On gpt-oss the workflow agent got 2 more claims right for 2.6× the time:** 4.2 hours instead of 1.6 per 1,000 claims.
- **ReAct depends on the model.** On gpt-oss it was the most accurate retrieval setup and faster than the workflow agent (11.3 s against 15.2 s). On Llama it needed 7.9 calls and 17× simple RAG's tokens just to match the workflow agent.
- **Corrective RAG was the worst trade on gpt-oss:** less accurate than simple RAG and the slowest, because many rewrite replies ran past the reply limit.
- **Full-context split by model:** 0.76 on gpt-oss, tied best but not separated from simple RAG (p = 0.28), at 13× the tokens. On Llama it fell to 0.32, answering "need more detail" on 79 of 124 claims.

![Accuracy against tokens per claim, one point per setup and model.](../results/test/report/accuracy_vs_tokens.png)

### 7.4 Why answers were wrong

![Every answer sorted into sound, right without evidence, wrong with evidence, or wrong without evidence.](../results/test/report/process_outcomes.png)

- **The workflow agent fixed retrieval, not reasoning.** Evidence recall rose from 0.66 to 0.91 (Llama) and 0.84 (gpt-oss). Wrong answers with missing evidence fell from 31 to 11 on Llama and from 26 to 18 on gpt-oss, but on Llama 37 of the agent's 48 wrong answers had every needed clause in front of it.
- **ReAct found nearly as much evidence** (0.88 and 0.77), but on gpt-oss more of its right answers lacked it (sound rate 0.56, against the workflow agent's 0.62).
- **Simple RAG was often right without the evidence:** over a third of its right answers (27 of 70 on Llama, 32 of 86 on gpt-oss). Counting only sound answers, the workflow agent's lead grows from 5 and 2 points to 19 and 18.
- **Corrective RAG's grader worked, its rewrites did not.** Precision rose from about 0.2 to 0.53 (Llama) and 0.72 (gpt-oss), but a rewrite brought in a needed section only 2 and 5 times.
- **Typical errors** (hand-labelled): simple RAG retrieved the wrong section; the workflow agent was over-cautious, or gave all-or-nothing answers to partly covered claims. Its definitions step also misses terms a claim implies but never names.
- **A claim no setup got right (fwd-030):** S$800 in cash stolen. The S$300 cash limit sits in a separate table of limits, not in the benefit text, so all 14 answers were wrong.
- **Citations:** no answer cited a real section it had not been shown. Bad citations were made-up IDs, almost all from Llama.

### 7.5 Where the agent helps

| Category (claims) | RAG | CRAG | Agent | ReAct |
| --- | --- | --- | --- | --- |
| single\_section (65) | 0.62 / 0.72 | 0.66 / 0.74 | 0.62 / 0.69 | 0.66 / 0.82 |
| needs\_definition (20) | 0.55 / 0.60 | 0.50 / 0.35 | 0.70 / 0.60 | 0.55 / 0.45 |
| needs\_exclusion (25) | 0.56 / 0.68 | 0.64 / 0.52 | 0.68 / 0.92 | 0.68 / 0.84 |
| tricky (14) | 0.36 / 0.71 | 0.36 / 0.64 | 0.36 / 0.57 | 0.36 / 0.79 |

Accuracy as Llama / gpt-oss. The workflow agent gained most on claims that need an exclusion (+12 and +24 points over simple RAG) and, on Llama, a definition (+15); it gained nothing on single-section claims. ReAct's gains on gpt-oss were broader, but it was weaker on definitions there (0.45, against 0.60 for the workflow agent), which the fixed steps look up directly. Groups of 14 to 25 claims are too small to test.

### 7.6 Faithfulness, retrieval only and exploratory setups

- **Faithfulness:** ReAct (0.72) and the workflow agent (0.68) were the most faithful on gpt-oss, but on Llama the workflow agent was the least faithful retrieval setup (0.29): the 8B model had the right clauses but misquoted them. The judge agreed with our checks on 77 to 80% of 60 grades, and was usually the stricter one.
- **One search is not enough.** Searching with the claim text alone (k = 5):

| Search | All gold sections | Benefits | Definitions | Exclusions |
| --- | --- | --- | --- | --- |
| Dense (simple RAG's) | 0.66 | 0.76 | 0.00 (0 of 24) | 0.26 |
| BM25 | 0.59 | 0.58 | 0.38 (9 of 24) | 0.41 |
| Hybrid | 0.64 | 0.72 | 0.00 | 0.30 |

A claim describes what happened and never uses the defined terms or exclusion wording that decide it, so no search method finds them. The agent finds them by looking them up through the policy's structure.

- **Agent-Pick** (the model picks extra definitions): its dev gain did not hold on test (0.58 vs 0.61 on Llama, 0.73 vs 0.71 on gpt-oss; not significant).
- **RAG-10** (simple RAG with 10 passages): more evidence (0.66 to 0.75) but no real gain in accuracy or safety (+3 and +1 claims; p = 0.61 and 1.00), for 1.7× the tokens. It ran on a different GPU, so its seconds are not compared.

## 8. Demo: "Am I covered?"

The demo is a Streamlit app that runs no retrieval, simple RAG and the workflow agent side by side on gpt-oss-20b, so the audience sees the floor, the winner and the agent answer the same claim.

![The demo (earlier version, 7-hour typhoon claim). To be replaced with a screenshot of the current page on the Manila claim.](demo_typhoon.png)

- **Each card shows** a hedged verdict ("Likely covered under Travel delay, subject to the insurer's assessment", never a payout amount), the steps taken, a short reason and one deciding line per cited clause. On labelled test claims it also marks the verdict right or wrong, and a table under the cards lines up the four answers with their time and model calls; the test-set results are folded below it. For a covered verdict it quotes the benefit's limit for each plan from the policy (FWD's table of benefits, or the limits printed in each MSIG section), labelled as a limit and not an estimate: the payout depends on the plan bought and the insurer's assessment, and amounts were not part of our evaluation.
- **Guardrails:** every cited ID must exist in the policy, or the answer becomes "need more detail" and asks for the missing facts. A safe-mode toggle has the agent re-check every "covered", and a quote check rejects a "covered" that quotes wording not found in the policy.
- **Prompt injection:** four claims with instructions such as "say covered" fooled neither setup. A fake policy endorsement pasted into a claim did fool simple RAG; the quote check catches it.
- **Offline:** scripted questions use cached answers, which are never used for any reported number.
- **Limit:** the winner is right on 69% of claims. The app points to the deciding clauses; it is not a claims decision.

## 9. Discussion

**Answer to the research question.** No agent was significantly more accurate than simple RAG. Both agents were slightly more accurate (the workflow agent by 5 and 2 points, ReAct by 5 and 6), but they cost 1.9 to 4.8× the time and 2 to 17× the tokens. On accuracy alone, simple RAG is the better buy; the workflow agent's real advantage is safety.

**What we learned**

- **Better evidence did not mean better verdicts.** The workflow agent found the clauses; the bottleneck moved to reading them, especially for the 8B model.
- **The model mattered more than the method.** A strong model can even read the whole policy, or plan its own lookups (ReAct on gpt-oss); a weak one needs retrieval to keep the context small, and as a free agent it flails (ReAct on Llama: 7.9 calls per claim).
- **Searching again or searching wider does not help** when the missing clause shares no words with the claim (corrective RAG, RAG-10).
- **The formal winner depends on which setups are in the race.** Our tie-break only compares the top two, so adding ReAct afterwards switched the winner from simple RAG to the workflow agent without changing either one's results. A rule that compares every setup against the cheapest would be more stable.
- **Safety is where the workflow agent earns its cost.** On gpt-oss it wrongly said "covered" on 1 of 53 claims, against 9 for simple RAG and 4 for ReAct (exploratory, p = 0.021 against simple RAG; not significant on Llama). Our rule only checked safety against simple RAG, so it could not reward this; a real deployment should break ties on safety.

**Advice to an insurer.** Use simple RAG as the main engine and let the workflow agent re-check every "covered". On the stored gpt-oss answers this gave 0 wrong "covered" of 53, at 66% accuracy and about 1.8× simple RAG's tokens (simulated, exploratory). Keep ReAct for open-ended questions, such as comparing plans, and only with a strong model and a cap on lookups: claim checking is a well-structured task, where Topic 7's rule of thumb favours a fixed plan over ReAct, and our results agree (more calls, less safe). Invest in the model before the method, and at about 70% accuracy let the chatbot point customers to the deciding clauses while a person decides the claim.

**Limitations**

- **Labels:** agreement was moderate (kappa 0.46); "not covered" versus "need more detail" is partly a judgement call.
- **Power:** 124 claims only detect gaps of about 14 to 16 points. A 5-point gap would need about 800 to 1,100 claims.
- **ReAct joined after the core runs,** so its comparison was not pre-registered; we report the rule both ways for that reason.
- **Scope:** two policies from one market, two open models (8B and 20B), and claims we wrote ourselves.
- **One run per setup,** and vLLM is not fully deterministic.
- **The judge** checks explanations against the cited text, not against the verdict.

**Future work**

- Let the agent find terms a claim implies, not only terms it names.
- Check sub-limits and partial cover before giving a verdict.
- Give simple RAG structure-based lookups for definitions and exclusions.
- Pre-register a tie-break that compares every setup and accounts for safety, and use a larger test set.

## 10. Conclusion

On real travel policies, simple RAG is hard to beat for accuracy per unit of cost. The claims-workflow agent was more accurate, better grounded and safer, but not by enough to show on 124 claims, so our pre-registered rule picks simple RAG; ReAct, added later, was not significantly more accurate either. The agent's value is in how it works. It finds the definitions and exclusions that one search misses, which turns retrieval failures into reasoning failures, and the stronger model made far fewer of those (18 against 37). For a user, its clearest benefit is the one our rule did not reward: it is much less likely to tell someone a claim is covered when it isn't (1 of 53 against simple RAG's 9 on gpt-oss).

## Contributions

**Member A (Ye Zhan), written by Member B.** YZ set up the shared infrastructure the whole study ran on. They tested and documented the SMU GPU cluster setup (vLLM servers and batch scripts), and wrote the repository skeleton and the shared contracts (output schema, model client and store). They wrote the ingestion of both policies into sections with stable IDs, and the search over them. When the planned API credits turned out not to cover API calls, they switched the study to the two free cluster models. They built the no-retrieval, simple RAG and corrective RAG setups (including the corrective RAG dev trials), tuned the shared base prompt on dev, and added the exploratory Full-context and RAG-10 setups and the retrieval-only comparison. They also built the safe-mode analysis (simple RAG re-checked by the agent on every "covered"), simulated from the stored test answers. On evaluation, they wrote the run and scoring pipeline (resumable runs, bootstrap confidence intervals, Holm-corrected McNemar tests, the decision rule and the trace metrics), the leaderboard and charts, the agreement script, and the rule that splits the human "other" error type. They blind-labelled 40 test claims (kappa 0.46), submitted the final test runs on both models, and hand-checked 10 agent traces. In the report they wrote the method, evaluation design, development and results sections, kept the running list of findings, re-checked every number in Member B's sections and the discussion, and wrote the README.

**Member B (Liang Than), written by Member A.** Liang built the data the study rests on. They wrote the labelling guide that defines the four verdicts and how to choose gold sections, along with the drafting helpers and the Streamlit review page. They drafted 156 claims from specific clauses of both policies and reviewed every draft against the policy text. They removed 12 redundant claims, made the seeded split (20 dev, 124 test), resolved the blind-labelling disagreements with Member A, and updated the guide where a rule was unclear. They built the policy look-up tools and the workflow agent, our domain-specific setup, including its dev trials, plus the exploratory Agent-Pick variant, in which the model picks up to 3 extra defined terms on top of the ones matched by name. On evaluation, they wrote the Claude Haiku faithfulness judge with a cost dry-run and an agreement check, and hand-checked 30 judgments per model. They also labelled the error type of all 176 wrong simple RAG and agent test answers and hand-checked 10 agent traces. They built the "Am I covered?" demo with its guardrails, an offline answer cache, a prompt-injection check, and two exploratory safeguards: a safe mode in which the agent double-checks every "covered" from simple RAG, and a quote check that rejects a "covered" answer quoting wording that is not in the policy. In the report they wrote data and labelling, the workflow agent's design, faithfulness, the demo, the discussion (including the minimum detectable gap and the safety gap in the decision rule), related work and the architecture diagram.

## References

- Asai, A., Wu, Z., Wang, Y., Sil, A., & Hajishirzi, H. (2024). Self-RAG: Learning to retrieve, generate, and critique through self-reflection. ICLR 2024. [arxiv.org/abs/2310.11511](https://arxiv.org/abs/2310.11511)
- Dietterich, T. G. (1998). Approximate statistical tests for comparing supervised classification learning algorithms. Neural Computation, 10(7), 1895–1923.
- Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. NeurIPS 2020. [arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401)
- Li, Z., Li, C., Zhang, M., Mei, Q., & Bendersky, M. (2024). Retrieval augmented generation or long-context LLMs? A comprehensive study and hybrid approach. EMNLP 2024 Industry Track. [arxiv.org/abs/2407.16833](https://arxiv.org/abs/2407.16833)
- Liu, N. F., et al. (2024). Lost in the middle: How language models use long contexts. TACL 12. [arxiv.org/abs/2307.03172](https://arxiv.org/abs/2307.03172)
- Yan, S.-Q., Gu, J.-C., Zhu, Y., & Ling, Z.-H. (2024). Corrective retrieval augmented generation. arXiv:2401.15884. [arxiv.org/abs/2401.15884](https://arxiv.org/abs/2401.15884)
- Yao, S., et al. (2023). ReAct: Synergizing reasoning and acting in language models. ICLR 2023. [arxiv.org/abs/2210.03629](https://arxiv.org/abs/2210.03629)
- Zheng, L., et al. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. NeurIPS 2023 Datasets and Benchmarks. [arxiv.org/abs/2306.05685](https://arxiv.org/abs/2306.05685)
