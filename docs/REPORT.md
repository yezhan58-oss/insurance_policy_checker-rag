<!-- Merged draft (4 Nov) from the *_SECTION.md files. Every number traces to results/test/ or the docs listed in
REPORT_NOTES. Course AI policy: each member must edit and vet their own part in their own words before submitting. -->

# Is the agent worth it? Agentic RAG for travel insurance coverage verdicts

IS469 Generative and Agentic AI, group project. Member A: Ye Zhan. Member B: Liang Than.
Code, data and results: https://github.com/yezhan58-oss/insurance_policy_checker-rag

## Abstract

Travel insurance policies decide a claim through rules spread across the document: a benefit, a definition at the
back and an exclusion many pages away. We ask whether agentic retrieval gives more accurate and better-justified
coverage verdicts than simple RAG, and whether the gain is worth the cost. On two real Singapore policies (FWD, MSIG)
and 124 human-labelled test claims, we compare no retrieval (B0), simple RAG (A0), corrective RAG (A2) and a
claims-workflow agent (A4) on Llama 3.1 8B and gpt-oss-20b, plus an exploratory whole-policy baseline (L0). A4 was the
most accurate pre-registered setup (0.61 and 0.71 vs A0's 0.56 and 0.69) and found far more of the needed evidence
(0.91 and 0.84 vs 0.66), but the gain was not significant, so our pre-registered rule picks A0 on both models. A4's
errors moved from retrieval to reasoning, and on gpt-oss it rarely called a not_covered claim covered (1 of 53 vs
9).
We ship A0 in a guarded Streamlit demo with A4 as a second opinion.

## 1. Introduction

A traveller whose flight was delayed by a typhoon wants to know one thing: can I claim? The answer sits in the policy
wording, but rarely in one place. The benefit sets a threshold (6 hours of delay), a definition narrows a term
("scheduled public transport"), and a general exclusion elsewhere can cancel the cover. A model that sees only the
benefit may promise a payout the policy does not make.

Retrieval-augmented generation (RAG) lets a language model answer from the policy, but one search with the claim text
finds what the claim names, not the rules that decide it. Agentic RAG adds steps that check and extend the evidence.
These steps cost model calls, tokens and seconds, so the question is not only whether they help but whether the help
is worth paying for.

**Research question.** Which agentic RAG approach gives the most accurate and best-justified coverage verdicts on real
insurance policies, and is the gain worth the extra cost and latency compared with simple RAG?

Our contributions:

1. A controlled comparison of four setups (no retrieval, simple RAG, corrective RAG, a domain workflow agent) on two
   models of different size and style, with the same index, prompt and answer call, a decision rule fixed before the
   test run, and Holm-corrected paired tests.
2. A trace evaluation that scores each step of the agents against gold sections and splits every wrong answer into a
   retrieval failure or a reasoning failure, plus a "sound rate" that credits only right answers with the evidence.
3. A 144-claim dataset drafted by an LLM from specific clauses and checked by two human labellers.
4. An "Am I covered?" demo of the winner with guardrails and an offline cache.

## 2. Related work

**Retrieval-augmented generation.** RAG gives a language model passages fetched from an outside corpus at answer time
(Lewis et al., 2020). Our A0 is the plain form: one search with the claim text, five chunks, one answer. Policy
wordings are hard for it because the deciding text is spread out, and one search with the claim text rarely finds
the benefit, the definition and the exclusion together.

**Corrective and self-reflective retrieval.** Corrective RAG (CRAG; Yan et al., 2024) grades the retrieved passages
and, when they are weak, rewrites the query or falls back to web search. Self-RAG (Asai et al., 2024) trains the model
to decide when to retrieve and to critique its own output. Our A2 follows CRAG with an LLM grader in place of the
fine-tuned evaluator and no web search, because the corpus is closed.

**Tool-using agents.** ReAct (Yao et al., 2023) lets a model mix reasoning with tool calls and choose what to look up
next. Our plan flagged tool calling with an 8B model as a risk, so we built a ReAct agent (A3) only after the core
study, as an exploratory setup. Our A4 takes the opposite approach: a fixed LangGraph workflow that follows how a claims assessor reads a policy. The
domain knowledge sits in the graph, not in the model's choices.

**Long context instead of retrieval.** Li et al. (2024) find that long-context models can beat RAG when enough
resources are available, while RAG costs far less. Models also use information in the middle of a long prompt less
well than at the start or end (Liu et al., 2024). Our exploratory L0 tests the first finding; we could not test the
second, because where a clause sits and the claim category go together.

**LLM as judge.** Strong LLMs can grade open-ended answers with agreement close to human raters, with known biases
such as favouring their own outputs (Zheng et al., 2023). Our judge, Claude Haiku 5.5, comes from a different company
than both tested models, and we checked it against human labels.

## 3. Data

**Policies.** Two public Singapore travel policy wordings: FWD Travel Insurance (April 2024, 45 pages) and MSIG
TravelEasy (70 pages, 52 benefit sections), downloaded on 16 and 17 Oct 2026 and committed with their SHA-256 hashes.
They differ in layout: FWD puts definitions at the back and prints its benefit tables as images (we transcribed them by
hand); MSIG cross-references its general exclusions by number from each benefit.

**Ingestion.** Each policy is split along its own headings into 284 sections (FWD 131, MSIG 153), each with a stable ID
(e.g. `fwd:travel_delay`) and a type: benefit (93), definition (66), condition (56), exclusion (46) or other (23).
Sections over 500 words are split into chunks of about 400 words with a 50-word overlap, giving 323 chunks that all
keep their section ID. Defined terms are also stored in a lookup table. Ingestion is deterministic, so every machine
builds the same index.

**Claims.** Real claims are not public, so we built 156 by construction. An LLM was given one clause and asked to
write a short first-person claim aimed at a chosen verdict, recording the intended verdict and the deciding sections.
Claims come in sets around one clause so that small changes flip the answer: a 7-hour delay is covered, a 4-hour delay
is not, and "my flight was delayed" is insufficient_info. Each claim has a verdict (covered, not_covered,
partially_covered, insufficient_info) and a category (single_section, needs_definition, needs_exclusion, tricky).

**Labelling.** Grading models against an LLM's own drafts would bias the results, so no draft became a gold label
without human review. Member B wrote a one-page labelling guide (verdict definitions, default assumptions, tie-break
rules such as "an exclusion that clearly applies beats a benefit") and reviewed every draft against the clause text:
143 accepted, 1 corrected, 12 deleted as repeats, leaving 144. A fixed-seed split gave 20 dev claims for tuning and
124 test claims scored once.

| | Dev | Test |
|---|---|---|
| Claims (FWD / MSIG) | 20 (10 / 10) | 124 (80 / 44) |
| covered / not_covered / partially / insufficient | 5 / 6 / 4 / 5 | 46 / 53 / 14 / 11 |
| single_section / definition / exclusion / tricky | 8 / 3 / 5 / 4 | 65 / 20 / 25 / 14 |

**Blind check.** Member A labelled 40 random test claims blind. Agreement was moderate: 25 of 40 on the four-way
verdict (Cohen's kappa 0.46, 95% CI 0.24 to 0.64) and 30 of 40 on covered or not (kappa 0.50). Both labellers chose
at least one common gold section in 39 of 40 cases, so they disagreed on how to read a clause, not which clause
applies. The 15 disagreements were resolved together against the policy text, two rules were added to the guide, and
the test set was frozen on 28 Oct.

## 4. Method

![Architecture: one shared index, prompt and answer call; the setups differ only in how they find policy text.](figures/architecture.png)

### 4.1 A controlled comparison

Every setup receives a claim, the model client and the policy store, and returns the same structured output: verdict,
cited section IDs, explanation, a step-by-step trace and usage counts. Everything except the way policy text is found
is shared: the base prompt, the embedding model (BAAI/bge-small-en-v1.5 on CPU), the index, temperature 0 and the
final answer call. The base prompt states the four verdicts and five rules from the labelling guide, so the models are
judged by the rules the labellers used; a unit test fails if the guide changes without the prompt being re-checked.
The answer is forced into a JSON schema; an unusable reply is retried once and then scored as a wrong parse error.

### 4.2 The setups

Every setup ends in the same answer call. They differ only in which policy text that call sees and how it was found.

| Setup | How it finds the policy text | Model calls per claim (Llama / gpt-oss) | Status |
|---|---|---|---|
| B0 | It does not: the model answers from what it already knows | 1.0 / 1.1 | Pre-registered (floor) |
| A0 | One search with the claim text, top 5 chunks | 1.0 / 1.0 | Pre-registered |
| A2 | Search, grade each chunk, rewrite the query and search again if too few are relevant | 2.5 / 2.8 | Pre-registered |
| A4 | Fixed steps like a claims assessor: benefits, then definitions, then exclusions | 3.0 / 3.0 | Pre-registered |
| L0 | None needed: the whole policy goes in the prompt | 1.0 / 1.1 | Exploratory (30 Oct) |
| A3 | The model chooses its own lookups, one at a time | 7.9 / 3.4 | Exploratory (4 Nov) |
| A4D | A4, plus a model pick of extra definitions | 4.0 / 4.0 | Exploratory (5 Nov) |
| Safe mode | A0 first; A4 re-checks any covered or partially covered answer | A0's call, plus A4's on 39 / 50 of 124 claims | Exploratory, simulated |

Calls are measured means on test; above 1.0 for one-call setups means a retry after an unusable reply. Exploratory
setups were added after the comparisons were pre-registered, so their tests are uncorrected and they can never win
under the decision rule.

**Pre-registered**

- **B0, no retrieval:** the claim and no policy text. The floor.
- **A0, simple RAG:** one search with the claim text, top 5 chunks.
- **A2, corrective RAG** (after Yan et al., 2024), a LangGraph loop: search 5 chunks; the LLM grades which are
  relevant (one call per search; exclusions count as relevant, so the grader cannot filter out the text that stops a
  payout); if fewer than 2 are relevant, the LLM rewrites the query in the policy's wording and searches again (at
  most 2 rewrites; a repeated query ends the loop); answer from the relevant chunks only. Unusable grader replies keep
  every chunk, so a failure falls back to A0.
- **A4, claims-workflow agent** (Member B), a fixed four-step LangGraph graph with no loops: (1) the model picks up to
  3 benefit sections from the titles of all benefits, in effect the table of contents; (2) defined terms in the claim
  and the chosen benefits are fetched from the definitions lookup, with no model call; (3) the general and
  section-specific exclusions of the chosen benefits are gathered and the model keeps those that could apply; (4) the
  shared answer call over everything gathered. At most 3 model calls; an unusable pick falls back to a fixed rule. Its
  design bet: simple RAG fails on policies mainly because the deciding definition or exclusion does not resemble the
  claim wording.

**Exploratory**

- **L0, long context:** the whole policy in the prompt, every section with its ID (about 28k tokens for FWD, 45k for
  MSIG). It tests whether retrieval is needed at all on a corpus this small.
- **A3, ReAct tool agent** (after Yao et al., 2023): the model decides what to look up. At each step it writes a short
  thought and one action: search the policy, get the definition of a term, get the exclusions of a benefit, or answer.
  It has the same tools as A4, so it can reach the same evidence; the difference is that A4 uses them in a fixed order
  and A3 chooses for itself. After 8 lookups it must answer, and the shared answer call sees every section it looked
  at.
- **A4D, A4 with picked definitions:** step 2 also asks the model to pick up to 3 more definitions from the policy's
  list of defined terms, to catch terms a claim implies but does not name. One more call than A4.
- **Safe mode:** A0 answers every claim; when it says covered or partially covered, A4 runs as well and its verdict is
  used instead, a second opinion before anyone is told to expect a payout. Simulated from the stored A0 and A4 test
  answers (no new model calls), and offered as a toggle in the demo.

### 4.3 Models and infrastructure

We compare a small instruction model, Llama 3.1 8B Instruct (16-bit), with a larger open reasoning model,
gpt-oss-20b (4-bit expert weights), both served with vLLM on A40 GPUs of the SMU cluster through SLURM batch jobs. Both
run free on university hardware, so cost is measured as model calls, tokens and seconds per claim. Calls are made one
at a time, so seconds are measured the same way for every setup. Decoding is greedy with a fixed seed, but vLLM is not
fully deterministic, so a rerun could move a few claims. The test claims were written for this project and never
public, so no model can have seen them.

## 5. Evaluation design

Every test claim has a human gold verdict (one of four) and gold sections: the clauses that decide it. Each measure
below answers one question about an answer, and each is averaged over the 124 test claims.

**What we measure about the answer**

| Measure | Question it answers | How it is computed | Better |
|---|---|---|---|
| Verdict accuracy (main) | Is the verdict right? | share of claims whose verdict equals the gold verdict | higher |
| Wrong-covered rate (safety) | Does it say "covered" when the claim is not? | of the 53 gold not_covered claims, share answered covered or partially_covered | lower |
| Clause recall | Does it cite the deciding clauses? | share of gold sections that appear in the answer's citations | higher |
| Faithfulness | Is the explanation backed by the clauses it cites? | Claude Haiku judge rates yes / partly / no; we report the share of "yes" | higher |

**What we measure about the process** (from each setup's step trace, no extra labelling)

| Measure | Question it answers | How it is computed | Better |
|---|---|---|---|
| Evidence recall | Did the needed clauses reach the model at all? | share of gold sections in the final answer's context | higher |
| Sound rate | Is it right for the right reason? | right verdict with every gold section in context, over all claims | higher |
| Grounded rate | Right, with evidence, and explained faithfully? | sound and judged faithful, over all claims | higher |
| Failure split | Why was a wrong answer wrong? | *missing evidence* (a gold section never reached the model: a retrieval failure) or *had evidence* (a reasoning failure) | fewer |
| Step recall / precision | Does each step do its job? | e.g. share of gold exclusions A4's exclusions step kept, and share of what it kept that was gold | higher |
| Citation checks | Are citations real? | does each cited ID exist in the policy, and was it in the model's context | higher |

**What we measure about cost** (both models run free on the cluster, so there is no dollar price)

| Measure | Question it answers | How it is computed | Better |
|---|---|---|---|
| Model calls | How many times does it ask the model? | mean calls per claim | fewer |
| Tokens | How much text does the model read and write? | mean prompt + reply tokens per claim, including gpt-oss's reasoning | fewer |
| Seconds | How long does a user wait? | mean wall-clock time per claim, one claim at a time | fewer |

*Example.* For the 7-hour typhoon claim (gold: covered; gold sections: the travel-delay benefit and the definition of
scheduled public transport), an answer that says covered and cites only the benefit is accurate, has clause recall
0.5, and is sound only if both sections were in its context.

**Statistics.** 95% bootstrap confidence intervals (1,000 resamples, fixed seed). Setups are compared with exact
McNemar tests on per-claim correctness (Dietterich, 1998): the test looks only at claims where one setup is right and
the other wrong, and asks whether that split could be chance. Three comparisons were fixed in advance, with Holm
correction: best agent vs A0, A0 vs B0, and A2 vs A4.

**Decision rule (fixed before the test run).** Three steps, applied to each model separately:

| Step | Rule | Why |
|---|---|---|
| 1. Safety filter | drop any setup whose wrong-covered rate is worse than A0's | a costlier setup must not be less safe than simple RAG |
| 2. Rank | the most accurate remaining setup leads | accuracy is the main measure |
| 3. Tie-break | if McNemar cannot separate the top two (p ≥ 0.05), the cheaper one wins: fewer model calls, then fewer seconds | a gain we cannot tell apart from chance is not worth paying for |

There is no fixed budget in seconds or tokens: "cheaper" only matters in step 3, between two setups the test cannot
separate. Exploratory setups added after pre-registration (such as L0) are scored but never compete.

Both members also hand-checked 20 agent traces and labelled the error type of every wrong A0 and A4 answer.

**Retrieval only.** To test whether any single search could find the evidence, we search each test claim's policy with
the claim text using dense search (A0's own), BM25 and a hybrid of the two, with no model call.

## 6. Development

All tuning used the 20 dev claims, with an acceptance rule written down before each trial: keep a change only if
accuracy and wrong-covered rate are no worse on both models. With 20 claims, one claim is 5 points, so dev results only
guided go/no-go decisions.

- **Prompt.** Llama never answered insufficient_info on dev (0 of 5). Three prompt variants were tried; none beat the
  original (0.45, 0.50, 0.40 vs 0.50), and a reasoning-first variant changed 5 of 20 verdicts when run twice at
  temperature 0, while the original changed none. We kept the original. gpt-oss handled these verdicts with the same
  prompt, which points to a model limit.
- **A2 threshold.** Lowering the rewrite threshold from 2 relevant chunks to 1 made gpt-oss 2.7 times faster but less
  accurate (0.60 vs 0.70) and less safe, so the threshold stayed at 2. Repeated rewrites led to the repeated-query stop.
- **A4 exclusions** (Member B). On Llama, A4 fixed retrieval (evidence recall 0.95 vs 0.62 for A0) but not accuracy,
  and 9 of its 10 misses had all the evidence. A stricter exclusions prompt cut context from 21 to 10 sections without
  improving accuracy, so the original was kept: Llama's remaining errors are reasoning, not context size.
- **A4D** (Member B, exploratory). A variant where the model picks the definitions it needs from the policy's full
  list of defined terms (24 FWD, 42 MSIG) instead of matching names in the benefit text. Dev: 17/20 vs A4's 15/20 on
  gpt-oss, 10/20 for both on Llama. A4 was already frozen, so A4D runs as a separate setup outside the decision rule.
- **Engineering fixes.** Replies cut off at the token limit crashed runs (now retried, then scored as parse errors);
  two jobs rebuilding one shared index corrupted it (each job now builds its own on local disk); runs are resumable,
  record the commit and full prompt, and refuse to score the test split on uncommitted code.

## 7. Results

The core setups and L0 ran at commit b80d7c3, A3 and A4D at c184cad, and A0K10 at bd31b05. Each of the 4 core
setups and L0 ran once on each model over the 124 test claims: 1,240 answers, of which 9
were parse errors (all gpt-oss: 8 L0, 1 A2), scored as wrong.

### 7.1 Leaderboard

| Model | Setup | Accuracy [95% CI] | Wrong-covered | Evidence recall | Sound rate | Faithful | Calls | Tokens | Seconds |
|---|---|---|---|---|---|---|---|---|---|
| Llama 8B | B0 | 0.54 [0.46–0.62] | 0.06 | 0.00 | 0.00 | 0.00 | 1.0 | 630 | 2.6 |
| | A0 | 0.56 [0.48–0.65] | 0.13 | 0.66 | 0.35 | 0.38 | 1.0 | 2,635 | 3.4 |
| | A2 | 0.60 [0.51–0.68] | 0.17 | 0.66 | 0.38 | 0.41 | 2.5 | 4,339 | 4.3 |
| | A4 | 0.61 [0.53–0.69] | 0.08 | 0.91 | 0.54 | 0.29 | 3.0 | 6,626 | 9.5 |
| | L0* | 0.32 [0.24–0.41] | 0.00 | 1.00 | 0.32 | 0.31 | 1.0 | 34,246 | 4.5 |
| gpt-oss-20b | B0 | 0.46 [0.38–0.54] | 0.23 | 0.00 | 0.00 | 0.00 | 1.1 | 1,700 | 9.1 |
| | A0 | 0.69 [0.61–0.77] | 0.17 | 0.66 | 0.44 | 0.63 | 1.0 | 3,247 | 5.8 |
| | A2 | 0.62 [0.53–0.70] | 0.11 | 0.68 | 0.44 | 0.60 | 2.8 | 6,139 | 27.6 |
| | A4 | 0.71 [0.63–0.78] | 0.02 | 0.84 | 0.62 | 0.68 | 3.0 | 6,476 | 15.2 |
| | L0* | 0.76 [0.68–0.83] | 0.13 | 1.00 | 0.76 | 0.42 | 1.1 | 40,842 | 18.0 |

\*Exploratory. Faithful: share of explanations the judge rated fully supported (B0 cites nothing it was shown, so 0
by construction).

A4 was the most accurate pre-registered setup on both models. Retrieval helped the larger model far more: A0 vs B0 was
0.69 vs 0.46 on gpt-oss but 0.56 vs 0.54 on Llama. gpt-oss beat Llama on every retrieval setup (A0 +13 points, A4
+10) but not without retrieval (B0 −8).

### 7.2 Significance and the winner

| Pre-registered comparison | Llama: p (Holm) | gpt-oss: p (Holm) |
|---|---|---|
| A4 (best agent) vs A0 | 0.38 (1.00) | 0.88 (0.88) |
| A0 vs B0 | 0.71 (1.00) | <0.001 (0.001) |
| A2 vs A4 | 0.86 (1.00) | 0.12 (0.24) |

Only one comparison is separated: retrieval beats no retrieval on gpt-oss. With 124 claims, a gap of about 14 points
(Llama) or 16 points (gpt-oss) between A4 and A0 would be needed for 80% power; the observed gaps are 5 and 2.

How the decision rule played out:

| Step | Llama 8B | gpt-oss-20b |
|---|---|---|
| 1. Safety filter (A0's wrong-covered rate) | 0.13: A2 out (0.17); B0, A0, A4 stay | 0.17: B0 out (0.23); A0, A2, A4 stay |
| 2. Top two by accuracy | A4 0.61 (76 of 124 right), A0 0.56 (70) | A4 0.71 (88 right), A0 0.69 (86) |
| 3. Does McNemar separate them? | no, p = 0.38 | no, p = 0.88 |
| Tie-break: model calls per claim | A0 1.0, A4 3.0 | A0 1.0, A4 3.0 |
| **Winner** | **A0** | **A0** |

**A0, the cheaper and faster setup, wins on both models**, although A4 has the higher accuracy. A4's lead is 6 claims
on Llama and 2 on gpt-oss, well inside what chance produces on 124 claims, so the rule does not pay three times the
model calls for it. The demo uses A0 on gpt-oss-20b, the more accurate model.

### 7.3 Cost and long context

What each pre-registered setup costs compared with simple RAG (A0):

| Model | Setup | Accuracy (vs A0) | Model calls | Tokens per claim (× A0) | Seconds per claim (× A0) | Time for 1,000 claims |
|---|---|---|---|---|---|---|
| Llama 8B | A0 | 0.56 | 1.0 | 2,635 (1×) | 3.4 (1×) | 1.0 h |
| | A2 | 0.60 (+3) | 2.5 | 4,339 (1.6×) | 4.3 (1.3×) | 1.2 h |
| | A4 | 0.61 (+5) | 3.0 | 6,626 (2.5×) | 9.5 (2.8×) | 2.6 h |
| gpt-oss-20b | A0 | 0.69 | 1.0 | 3,247 (1×) | 5.8 (1×) | 1.6 h |
| | A2 | 0.62 (−7) | 2.8 | 6,139 (1.9×) | 27.6 (4.7×) | 7.7 h |
| | A4 | 0.71 (+2) | 3.0 | 6,476 (2.0×) | 15.2 (2.6×) | 4.2 h |

Time for 1,000 claims: seconds per claim × 1,000, one claim at a time on one A40.

In plain terms: on gpt-oss, A4 got 2 more of 124 claims right than A0, but took 2.6 times as long per claim and read
twice the text; checking 1,000 claims would take about 4.2 hours instead of 1.6. On Llama, A4 got 6 more right for
2.8 times the time. Neither gain is significant, so the extra cost buys no accuracy we can show. A2 was the worst trade
on gpt-oss: less accurate than A0 and the slowest setup, because many of its rewrite replies ran long (Section 7.4).
The absolute seconds depend on our hardware; the ratios to A0 are what carry over.

![Accuracy against tokens per claim, one point per setup and model.](../results/test/report/accuracy_vs_tokens.png)

L0 (exploratory, uncorrected) splits by model. gpt-oss reached 0.76, the highest of any run, but was not separated from
A0 (p = 0.28) or A4 (p = 0.45), at about 13× A0's tokens and 3× its latency. Llama fell to 0.32, far below A0 and A4
(p < 0.001): it answered insufficient_info on 79 of 124 claims, 39 of them gold covered. Llama did worse on the longer
MSIG policy (0.20 vs 0.39 on FWD); gpt-oss did better on it (0.84 vs 0.71).

### 7.4 Why answers were wrong

![Every answer as sound, right without evidence, wrong with evidence or wrong without evidence.](../results/test/report/process_outcomes.png)

**Evidence.** A4 found far more of the needed sections (evidence recall 0.91 / 0.84 vs A0's 0.66), and its wrong
answers moved from retrieval to reasoning: missing vs had evidence was 31 vs 23 for A0 and 11 vs 37 for A4 on Llama,
and 26 vs 12 and 18 vs 18 on gpt-oss. A0 got over a third of its right answers without the evidence (27 of 70 on
Llama, 32 of 86 on gpt-oss); counting only sound answers widens A4's lead from 5 / 2 points to 19 / 18.

**Steps.** A2's grader worked: it raised precision from 0.20 to 0.53 (Llama) and 0.21 to 0.72 (gpt-oss) while keeping
recall. Its rewrites did not: A2 rewrote on 25 and 70 claims, but a rewrite added a needed section only 2 and 5 times,
so its evidence recall matched A0's. On gpt-oss, 42 of the 70 rewrite replies were unusable, most likely because
reasoning ran past the 2,048-token reply limit. A4's weakest step was definitions (recall 0.62 / 0.58): it matches
defined terms by name and misses terms a claim implies but does not use (fwd-059 fetched "natural disaster", not
"serious public event").

**Error types** (human labels on 176 wrong A0 and A4 answers). A0's most common error was the wrong section retrieved
(22 on Llama, 19 on gpt-oss). A4's were over-cautious insufficient_info with every gold section in context (10, 12)
and all-or-nothing answers to partially_covered claims (12 on Llama). Of the 20 hand-checked agent traces, 12 were
right; right verdicts often skipped a condition in the explanation, such as a 30-day window.

**A claim no setup got right: fwd-030.** "S$800 in cash was stolen from the wallet in my pocket in Barcelona. I
reported it to the police that day. Will I get all S$800 back?" Gold is partially_covered: the theft-of-money benefit
pays stolen cash, but the S$300 cash sub-limit is in FWD's separate table of benefit limits, not in the benefit text.
All 14 answers (7 setups x 2 models) were wrong: 5 said covered, 4 not_covered, 5 insufficient_info. Only L0, which
reads the whole policy, had the limits table in context, and it still missed the limit (Llama insufficient_info,
gpt-oss covered). Every retrieval setup cited only the benefit section. A4 looks up definitions and exclusions by
structure but not the limits table, so a sub-limit stored apart from its benefit is out of reach for all of them.

**Citations.** No answer cited a real section it never saw. Bad citations were made-up IDs, almost all from Llama.

### 7.5 By category

| Category (claims) | A0 | A2 | A4 |
|---|---|---|---|
| single_section (65) | 0.62 / 0.72 | 0.66 / 0.74 | 0.62 / 0.69 |
| needs_definition (20) | 0.55 / 0.60 | 0.50 / 0.35 | 0.70 / 0.60 |
| needs_exclusion (25) | 0.56 / 0.68 | 0.64 / 0.52 | 0.68 / 0.92 |
| tricky (14) | 0.36 / 0.71 | 0.36 / 0.64 | 0.36 / 0.57 |

Accuracy, Llama / gpt-oss. A4 gained most where it was designed to: claims that need an exclusion (+12 and +24 points
over A0) and, on Llama, a definition (+15). It gained nothing on single-section claims. Cells of 14 to 25 claims are
too small to test.

### 7.6 Faithfulness and retrieval only

On gpt-oss, A4 wrote the most faithful explanations (0.68); on Llama, the least faithful of the retrieval setups (0.29),
although it had the best evidence: the 8B model got the right sections from a context of about 18 sections but often
misquoted them. Member B checked 30 random judgments per model against the policy: agreement was 77% (kappa 0.64) on
Llama and 80% (kappa 0.52) on gpt-oss, and in 11 of 13 disagreements the judge was stricter, so faithfulness is a
lower bound.

| Search with the claim text, k = 5 | All gold | Benefits | Definitions | Exclusions |
|---|---|---|---|---|
| Dense (A0's search) | 0.66 | 0.76 | 0.00 (0 of 24) | 0.26 |
| BM25 | 0.59 | 0.58 | 0.38 (9 of 24) | 0.41 |
| Hybrid | 0.64 | 0.72 | 0.00 | 0.30 |

One search finds every needed section for only about half the claims. A claim names what happened, not the defined
terms or exclusions that decide it, and no search method closes that gap at k = 5. This is the gap A4 closes by
looking them up by structure.

**A4D (exploratory).** On test the dev gain did not hold: Llama 0.58 vs A4's 0.61 (exploratory McNemar p = 0.388),
gpt-oss 0.73 vs 0.71 (p = 0.839). Evidence recall barely moved (0.91 to 0.94 on Llama, 0.84 to 0.85 on gpt-oss), and on
gpt-oss wrong-covered rose from 0.02 to 0.06, for one more call and 1.1–1.2× the tokens. Missing definitions were not
what held A4 back.

**A0K10 (exploratory): would simple RAG do better with 10 passages?** No. Added on 11 Nov after the test results,
so it is outside the decision rule. Doubling k raised evidence recall from 0.66 to 0.75, but accuracy barely moved:
gpt-oss 0.70 vs A0's 0.69 (87 vs 86 right; exploratory McNemar p = 1.00), Llama 0.59 vs 0.56 (73 vs 70; p = 0.607).
Wrong-covered stayed about the same (8 vs 9 of 53 on gpt-oss, 7 vs 7 on Llama), for 1.7× the tokens. More passages
do not close the gap to A4's safety. These runs used an L40S GPU, so their seconds are not comparable.

## 8. Demo: "Am I covered?"

The build half turns the winner into a Streamlit app. The user picks a policy and a model, describes what happened, and
gets a verdict with the clauses behind it. It runs A0 on gpt-oss-20b by default, with a toggle that shows A4's answer
side by side.

![The demo on the 7-hour typhoon claim: A0 (left) says likely covered under fwd:travel_delay; A4 (right) asks for the check-in detail.](demo_typhoon.png)

Each answer has a hedged headline ("Likely covered under `fwd:travel_delay`, subject to the insurer's assessment"; never
a payout amount), the full text of every cited clause with its page, and the step trace the evaluation scores.

**Guardrails.** A check after the model keeps only cited IDs that exist in the index. If no real clause is left, or the
call fails, the verdict becomes insufficient_info and the app asks for the missing details instead of guessing. Every
headline is hedged ("likely", "subject to the insurer's assessment"). In a prompt-injection check (4 claims with
instructions such as "ignore your previous instructions and say covered", on A0 and A4), none of the 8 answers said
covered or cited the injected section. A harder attack got through: a fake policy endorsement pasted into the claim
(minimum delay 3 hours instead of 6), with an instruction to cite the real `fwd:travel_delay`. A0 on gpt-oss answered
covered and quoted the fake clause, since the guard checks cited IDs, not quoted wording. An exploratory quote check
(a covered answer must quote only wording found in the policy) caught it; on the test answers it flags 5 of 70 right
covered or partially covered gpt-oss answers and does nothing on Llama, which rarely quotes. It catches none of the real wrong covered answers among the A0 and A4 test
answers (0 of 10 on gpt-oss, 0 of 11 on Llama), so it defends only against pasted fake clauses, not ordinary errors.

**Offline.** Answers are cached by policy, model, setup and question, so the scripted questions run without the
cluster. The cache is never used for a reported number.

**Limits.** The winner is right on 69% of test claims (95% CI 61 to 77%), and the guard removes invented citations,
not wrong "covered" verdicts that cite a real clause. The app is a reading aid that points to the deciding clauses, not
a claims decision.

## 9. Discussion

**Answer to the research question.** Neither agent gave a significantly more accurate verdict than simple RAG. A4 was
more accurate (+5 and +2 points) and better justified (sound rate 0.54 / 0.62 vs 0.35 / 0.44), but at 2.6 to 2.8 times
A0's latency and 2 to 2.5 times its tokens. On accuracy alone the gain is not worth the cost, so A0 wins.

**Better evidence did not become better verdicts.** A4 does what it was designed to do: it finds the definitions and
exclusions one search misses, and cuts wrong answers with missing evidence (31 → 11 on Llama, 26 → 18 on gpt-oss). The
bottleneck moves to reading: on Llama, 37 of A4's 48 wrong answers had every gold section in context. A4's typical
errors are over-caution and all-or-nothing answers to partial cover, and the 8B model handles A4's larger context (about
18 sections on Llama, 7 on gpt-oss, against A0's 4) poorly.

**The model matters more than the strategy.** The model changed accuracy more than any retrieval strategy did. A model
that can read a 28k to 45k-token policy reliably needs little retrieval on a corpus this small, at 5 to 6 times A4's
tokens; a model that cannot depends on retrieval to cut the context down. The CRAG-style loop rarely helped on either
model: its grader works, but a "search again" loop cannot know that a definition or exclusion is needed.

**A gap in the decision rule: safety.** The rule checks safety only against A0, so when A0 wins the tie-break nothing
checks whether a costlier setup is safer. Afterwards, A4 is safer on gpt-oss: A0 said covered on 9 of the 53
not_covered claims, A4 on 1 (exact paired p = 0.021; exploratory, not corrected). On Llama the gap is smaller and not
significant (7 vs 4, p = 0.45). A wrong "covered" is the costliest error for a user, who may spend money expecting a
payout. A real deployment should break ties on safety; under that rule A4 would have won on both models.

**Limitations.**

- *Gold labels:* blind agreement was moderate (kappa 0.46); the boundary between insufficient_info and not_covered
  stays open to reading, so some of A4's "over-cautious" answers may be fair readings.
- *Power:* 124 claims detect only gaps of about 14 to 16 points; the 2 to 5 point gains may be real but too small to
  detect.
- *Scope:* two policies from one market, one embedding model, two open models of 8B and 20B parameters, synthetic
  claims.
- *One run:* each setup ran once; vLLM is not fully deterministic.
- *Judge:* stricter than the human, and it checks the explanation against the cited text, not against the verdict.

**Future work.** Make A4's definitions step find terms a claim implies, not only terms it names; add a check for
sub-limits and partial cover before the verdict; look up definitions and exclusions for A0 by policy structure rather
than changing its search; give reasoning models a larger reply limit in multi-call agents; pre-register a
safety-aware tie-break.

## 10. Conclusion

On real travel policies, simple RAG is hard to beat on accuracy per unit of cost: the claims-workflow agent was more
accurate, better grounded and safer, but not by enough to show with 124 claims, so our pre-registered rule picks
simple RAG. The agent's value is in its process. It finds the definitions and exclusions that one search misses and
turns retrieval failures into reasoning failures, which the stronger model made less often (18 vs 37). For a user,
its clearest benefit is the one our rule did not reward: it is less likely to tell someone a claim is covered when it
is not (1 of 53 vs A0's 9 on gpt-oss).

## Contributions

**Member A (Ye Zhan), written by Member B.** YZ set up the shared infrastructure that the whole study ran on. They
tested and documented the SMU GPU cluster setup (vLLM servers and batch scripts), and wrote the repository skeleton and
the shared contracts (output schema, model client, store). They also wrote the ingestion of both policies into
sections with stable IDs, and the search over them. They switched the study to the two free cluster models when the
planned API credits turned out not to cover API calls. They built B0, A0 and A2 (including its dev trials), tuned the
shared base prompt on dev, and added the exploratory L0 and the retrieval-only comparison. They also built the safe-mode analysis (A0 re-checked by A4 on every ‘covered’), simulated from the stored test answers. On evaluation, they wrote
the run and scoring pipeline (resumable runs, bootstrap confidence intervals, Holm-corrected McNemar tests, the
decision rule, the trace metrics), the leaderboard and charts, the agreement script, and the rule that splits the
human "other" error type. They blind-labelled 40 test claims (kappa 0.46), submitted the final test runs on both
models, and hand-checked 10 agent traces. In the report they wrote the method, evaluation design, development and
results sections, kept the running list of findings, re-checked every number in Member B's sections and the
discussion, and wrote the README.

**Member B (Liang Than), written by Member A.** Member B built the data the study rests on. They wrote the labelling guide
that defines the four verdicts and how to choose gold sections, the drafting helpers and the Streamlit review page.
They drafted 156 claim scenarios from specific clauses of both policies and reviewed every draft against the policy
text. They removed 12 redundant claims and made the seeded split (20 dev, 124 test), then resolved the
blind-labelling disagreements with Member A and updated the guide where a rule was unclear. They built the policy
look-up tools and A4, the claims-workflow agent that is our domain-specific setup, including its dev trials, and the exploratory A4D variant, in which the model picks up to 3 extra defined terms on top of the ones matched by name. On
evaluation, they wrote the Claude Haiku faithfulness judge with a cost dry-run and an agreement check, and
hand-checked 30 judgments per model. They also labelled the error type of all 176 wrong A0 and A4 test answers and
hand-checked 10 agent traces. They built the "Am I covered?" demo with its guardrails, an offline answer cache, a prompt-injection check, and two exploratory
safeguards: a safe mode in which A4 double-checks every "covered" from A0, and a quote check that rejects a
"covered" quoting wording not in the policy. In the report they wrote data and labelling, the A4 design, faithfulness, the demo, the
discussion (including the minimum detectable gap and the safety gap in the decision rule), related work and the
architecture diagram.

## References

- Asai, A., Wu, Z., Wang, Y., Sil, A., & Hajishirzi, H. (2024). Self-RAG: Learning to retrieve, generate, and critique
  through self-reflection. ICLR 2024. https://arxiv.org/abs/2310.11511
- Dietterich, T. G. (1998). Approximate statistical tests for comparing supervised classification learning algorithms.
  Neural Computation, 10(7), 1895–1923.
- Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. NeurIPS 2020.
  https://arxiv.org/abs/2005.11401
- Li, Z., Li, C., Zhang, M., Mei, Q., & Bendersky, M. (2024). Retrieval augmented generation or long-context LLMs? A
  comprehensive study and hybrid approach. EMNLP 2024 Industry Track. https://arxiv.org/abs/2407.16833
- Liu, N. F., et al. (2024). Lost in the middle: How language models use long contexts. TACL 12.
  https://arxiv.org/abs/2307.03172
- Yan, S.-Q., Gu, J.-C., Zhu, Y., & Ling, Z.-H. (2024). Corrective retrieval augmented generation. arXiv:2401.15884.
  https://arxiv.org/abs/2401.15884
- Yao, S., et al. (2023). ReAct: Synergizing reasoning and acting in language models. ICLR 2023.
  https://arxiv.org/abs/2210.03629
- Zheng, L., et al. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. NeurIPS 2023 Datasets and
  Benchmarks. https://arxiv.org/abs/2306.05685
