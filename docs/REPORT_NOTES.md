# Report notes: everything the final report must include

The single list of findings, decisions and caveats collected while building the project that are not yet written into
a section draft. When the final report is written, every item below goes into the section shown in brackets (or is
deliberately left out, with a reason). Numbers here are final unless marked "after the test run".

Sections: 1 Introduction · 2–3 Data and labelling (`DATA_SECTION.md`, Member B) · 4 Method · 5 Evaluation design ·
6 Development and tuning (`METHOD_SECTION.md`) · 7 Results (`RESULTS_SECTION.md`) · 8 Demo (`DEMO_SECTION.md`,
Member B) · 9 Discussion · 10 Conclusion. The A4 write-up (old PR #27) is already inside METHOD 4.5 and 6.3.

---

## R. Results already in (final numbers)

### R1. Retrieval only: one search with the claim text (test, 124 claims) [7.10; method in 5.6]

Run on 30 Oct with `python -m src.eval.retrieval --split test` (laptop, CPU, no model calls). The BM25 rows were
reproduced exactly in a second environment, so the analysis is deterministic.

| Method | k | Gold recall | All gold found | Benefit | Definition | Exclusion | Condition |
|---|---|---|---|---|---|---|---|
| dense | 5 | 0.66 | 0.53 | 0.76 (96/127) | 0.00 (0/24) | 0.26 (7/27) | 0.00 (0/1) |
| dense | 10 | 0.75 | 0.60 | 0.84 (107/127) | 0.04 (1/24) | 0.41 (11/27) | 0.00 (0/1) |
| bm25 | 5 | 0.59 | 0.48 | 0.58 (74/127) | 0.38 (9/24) | 0.41 (11/27) | 1.00 (1/1) |
| bm25 | 10 | 0.69 | 0.58 | 0.70 (89/127) | 0.38 (9/24) | 0.67 (18/27) | 1.00 (1/1) |
| hybrid | 5 | 0.64 | 0.50 | 0.72 (91/127) | 0.00 (0/24) | 0.30 (8/27) | 0.00 (0/1) |
| hybrid | 10 | 0.76 | 0.65 | 0.83 (105/127) | 0.17 (4/24) | 0.59 (16/27) | 1.00 (1/1) |

Dense at k = 5 is exactly A0's search. Findings to write:
- One search finds every needed section for only about half the claims (dense k = 5: 0.53). A0 therefore answers
  about half the claims without part of the evidence, whatever the model does.
- The claim text finds the benefit (76%) but not the rules that decide it: **0 of 24 gold definitions** and 26% of
  gold exclusions. A claim names what happened, not the defined terms or exclusions that decide it.
- Keyword search fails differently: BM25 finds 38% of definitions (exact words such as "strike") but fewer benefits
  (58%). Hybrid (reciprocal rank fusion) does not close the gap: at k = 5 it is slightly below dense (0.64 vs 0.66)
  and still finds no definitions; at k = 10 it reaches 0.76 overall and 17% of definitions.
- Conclusion: the gap is not the choice of search method; searching with the claim text cannot surface definitions
  and exclusions. This is the direct justification for A4 looking them up by policy structure (dev evidence recall
  0.95 vs 0.62 for A0, METHOD 6.3).
- Caveats: the Condition column has one claim, ignore it. Dense k = 10 finds more (0.75), but A0's top_k = 5 was fixed
  before the test set was used: report as an observation, not a reason to change A0.

### R2. Judge smoke test (dev, 30 Oct) [7.9, Member B; method in 5.1]

10 Llama dev rows (all A4), cost about US$0.001. Judge labels: yes 5, partly 5, no 0, no errors. Member B checked all
10 against the FWD text: all 10 judgments correct (the 5 "partly" and the 5 "yes"), none too lenient.
- Pattern 1, explanation contradicts verdict (fwd-090, fwd-091): verdict not_covered, explanation describes cover
  (gold partially_covered). The judge checks explanation vs cited text only, so it cannot catch this; verdict
  accuracy already counts both as wrong. In the 30 test hand-checks, B also flags this on **right** answers, because
  there it would inflate the grounded rate. Report the count. [7.9, error analysis]
- Pattern 2, A4 over-applies the "event known before booking" exclusion (fwd-061, fwd-093). Noted only: approaches
  were locked for the test run. [error analysis]

### R3. Dev results (20 claims, for tuning only) [6, 7.11]

| Accuracy on dev | Llama 3.1 8B | gpt-oss-20b |
|---|---|---|
| A0 | 0.50 | 0.65 |
| A2 | 0.45 | 0.70 |
| A4 | 0.45 | 0.80 |

With 20 claims one claim is 5 points and the 95% interval is about ±22 points, so these were used only for go/no-go
decisions with acceptance rules fixed in advance; the test set (124 claims, about ±9 points) carries every reported
result. On dev, 9 of A4's 10 Llama misses had all needed sections in context (reasoning, not retrieval).

---

## B. Decisions and their reasons

- **Labelling guide changed, prompt not** (28 Oct) [5.5 or 6]: the disagreement resolution added two guide rules
  (optional add-on not stated → insufficient_info; a default assumption never overrides a stated fact). The prompt's
  rules were re-checked and left unchanged: both rules already follow from prompt rules 1 and 3, no dev claim uses
  them, and changing the prompt because of test claims would be tuning on test. The guide-hash test was updated.
- **Test set frozen 28 Oct** (merge of PR #26); later commits touched only the disagreement CSV's wording ("agreed").
- **L0 long-context baseline added 30 Oct as exploratory** [4.3 done, 7.6 placeholder]: after pre-registration, so
  outside the Holm family and the decision rule; prompts about 28k (FWD) and 45k (MSIG) tokens (measured on test), server context 131k.
- **Process-vs-outcome metrics added 29 Oct** (sound rate, grounded rate, `process_outcomes.png`) [5.4 done]: added
  after a course slide stressed that a right answer can come from a broken process; scoring only, before any test run.
- **Citation checks in code added 30 Oct** [5.4 done, 7.7 placeholder].
- **Error-type split added 3 Nov, after the error review** [7.7 / error analysis]: the 7 human types fixed before
  labelling are kept; only the human "other" label is split by rule in `report.py` (`split_other`), agreed with
  Member B: over-cautious insufficient_info (answered insufficient_info, gold another verdict, every gold section in
  context) and all-or-nothing partial (gold partially_covered, answered covered or not_covered). A4 "other" becomes:
  Llama 10 over-cautious, 12 all-or-nothing, 10 other (of 32); gpt-oss 12, 1, 2 (of 15; 2 of its 14
  insufficient_info answers lacked a gold section, so they stay "other"). Say in the report that the split was added
  after the review.
- **How the decision rule played out** [7.1 or 5.3, one sentence]: a setup with a higher wrong-covered rate than A0
  is not eligible. This removed A2 on Llama (0.17 vs A0's 0.13; it was second on accuracy, 0.60) and B0 on gpt-oss
  (0.23 vs 0.17), so on both models the top two eligible setups were A4 and A0.
- **Discussion checked 4 Nov** (PR #53, Member B; fixes by Member A): every number re-derived from the results.
  Minimum detectable gap confirmed (80% power at about 14 points on Llama, 16 on gpt-oss; A0/A4 disagree on 26% and
  34% of claims). Fixed: L0 prompt sizes are about 28k (FWD) and 45k (MSIG) tokens, measured on test, not 35k / 52k
  (also fixed in METHOD, RESULTS 7.6 and the L0 docstring); A2's gap on gpt-oss is no longer blamed on its grader
  (the grader works, the rewrites rarely help, see F); "clearly safer" softened (exploratory p = 0.021); the
  hybrid-search future-work item replaced, since R1 shows hybrid search at k = 5 finds no definitions (BM25 finds 9 of
  24 but loses benefits).

## C. Considered and not done (say so briefly, with the reason)

- **"Lost in the middle" check for L0** [9]: dropped. Source clauses sit almost only in the first two thirds of the
  prompt (test: 56 start, 67 middle, 1 end: benefits come first in both policies), and grouping by the latest needed
  section mirrors claim category (27 of the 32 "end" claims are needs_definition or needs_exclusion). Position cannot
  be separated from category, so any effect would be a category effect. If L0 is weak on definition and exclusion
  claims, mention lost-in-the-middle as one possible reason only.
- **Robustness to paraphrased claims** [9, limitation]: not run; each paraphrase would need a human check that the
  facts are unchanged, and there was no time before the deadline.
- **Fine-tuning** [9]: see D.
- **LangSmith tracing** [4.6 or 9, one sentence]: not used for the measured runs (extra overhead on latency, compute
  nodes may lack internet, would send policy text and claims to another service). Our own step traces cover the same
  need; LangSmith is only an option for the demo.
- **Hybrid search or re-ranking for A0** [9]: not added; R1 shows the gap is definitions and exclusions, which no
  search method found reliably.

## D. Discussion points (joint) [9]

- **Where the errors are.** If most wrong answers had the evidence in context (7.7), better retrieval is not the next
  step; R1 bounds what search changes could add.
- **The customisation ladder.** We stopped at prompting plus retrieval. Policy wording changes between versions, so
  it belongs in retrieval, not in model weights. The remaining errors are reasoning ("behaviour") gaps, which is
  where fine-tuning helps; with a verdict that can be checked automatically, reinforcement fine-tuning with a
  verifiable reward (e.g. GRPO) fits the task. 156 labelled claims are too few, and using them would consume the
  test set, so this is future work.
- **Long context vs retrieval (L0, test run done).** Answers "is RAG needed at all for two policies?": only with a
  strong model, and at a large token cost. Exploratory throughout (see B), never in the decision rule.
  - Accuracy: gpt-oss L0 0.76, the highest of any setup, but not separated from A4 (0.71; McNemar p = 0.45,
    uncorrected); 0.81 (94/116) if its 8 cut-off answers are left out. Llama L0 0.32, the lowest: it answered
    insufficient_info on 39 of 46 covered claims.
  - Why gpt-oss L0 scores high: evidence recall 1.00 (A0 0.66, A4 0.84; 0 wrong answers with missing evidence vs
    26 for A0 and 18 for A4). The gain is on covered claims (38/46 vs A0 31, A4 24) and needs_definition claims (0.80
    vs 0.60 for both): confirming cover needs the definitions and exclusions that one search misses (R1). A4 is best
    on not_covered (49/53) and needs_exclusion (0.92), leaning to denial; L0 is weakest on insufficient_info (3/11)
    and tricky claims (0.50), filling missing facts with assumptions.
  - **Token cost:** one prompt with the whole policy (about 28k tokens FWD, 45k MSIG). Mean tokens per claim: L0
    34,246 (Llama) and 40,842 (gpt-oss) vs A4 about 6,500 and A0 about 2,600–3,200, so about 6× A4 and 12–13× A0.
    Almost all of it is input; gpt-oss is higher because about 1 claim in 10 needed a retry, which resends the policy.
  - Latency stays close (gpt-oss 18.0 s vs A4 15.2 s): one call instead of A4's three in sequence, and vLLM reused
    97–98% of input tokens from its prefix cache on the L0 runs (every claim on a policy starts with the same text).
  - Cost implications: on a paid per-token API L0 costs about 6× A4 per claim, less with prompt caching since the
    policy prefix repeats. Cost grows with document size, not question size: each extra policy makes every claim
    dearer, and beyond about 3 policies the prompt no longer fits the 131k context; RAG cost stays roughly flat.
  - One-line takeaway: about 5 points over A4 (not significant) for about 6× the tokens; the limit on accuracy is
    missing evidence, which supports A4's structure-based lookups.
- **Found while filling RESULTS (4 Nov).** A0 gets over a third of its right answers without the evidence (27 of 70
  Llama, 32 of 86 gpt-oss), so counting only sound answers widens A4's lead from 5 / 2 points to 19 / 18. No
  answer cites a real section it never saw; bad citations are made-up IDs, almost all from Llama. Llama's B0 answers
  not_covered to 89 of 124 claims, which is why it looks safe (0.06 wrong-covered). gpt-oss's A4 context is about 7
  sections, not 18 (its exclusions step keeps about 1). By category, A4 gains most on needs_exclusion (+12 / +24
  over A0) and nothing on single_section.
- **Safety cascade, simulated from existing answers (4 Nov, exploratory, no new runs).** Use A0; when A0 says covered
  or partially_covered, use A4's verdict instead. Llama: accuracy 0.56 (= A0), wrong-covered 0.04 (2 of 53, vs A0
  0.13), A4 run on 39 of 124 claims, 4,790 tokens and 6.6 s per claim (A0 2,635 and 3.4 s). gpt-oss: accuracy 0.66
  (A0 0.69), wrong-covered 0.00 (0 of 53, vs 0.17), A4 on 50 of 124, 5,913 tokens and 12.3 s (A0 3,247 and 5.8 s).
  The safest setup on both models at about 1.8x A0's tokens; costs 3 points of accuracy on gpt-oss.
- **Deployment and privacy.** The tested models run on university hardware, so a claim answered by the system never
  leaves it. The judge is the only external API: it sees the claim, the explanation and the cited policy text,
  acceptable because our claims are synthetic; a real deployment would judge in-house.
- **Limitations.** One labeller per claim outside the 40 blind-checked ones (kappa 0.46); 124 test claims detect only
  fairly large differences (about 14 points on Llama, 16 on gpt-oss, at 80% power); two travel policies from one market; seconds depend on cluster
  load; temperature 0 is still not perfectly repeatable on vLLM; no robustness test; L0 is exploratory.
- **Extra work for the last week, agreed 4 Nov** (all exploratory: tuned on dev only, never in the Holm family or the
  decision rule, which stays A0 on both models): (1) safe mode, A0 with an A4 check whenever A0 says covered
  (numbers: Member A; demo: Member B); (2) A3, a ReAct tool agent (Member A); (3) A0 plus structure lookups, the
  definitions and exclusions linked to the benefits A0 found, no extra model call (Member A); (4) A2 on gpt-oss with
  a larger reply limit (Member A); (5) A4's definitions step picks from the list of defined terms (Member B). Order:
  1, 2, 3, then 4 and 5 if time allows.
- **A3 ReAct agent added 4 Nov as exploratory** [4.2, 7]: built after the test results, so `score.py` lists it in
  EXPLORATORY and drops it from AGENTS (the pre-registered "best agent" stays A2 or A4; results unchanged). Tools =
  A4's (search, get_definition, get_exclusions), so both can reach the same evidence; the prompt lists the tools but
  no order to use them in, since whether the agent thinks of definitions and exclusions itself is the question.
  Actions are JSON in plain text, not native tool calls: same on both models, no server change (gpt-oss's server
  has no tool-call parser). At most 8 lookups; unusable reply or the limit → answer with what it has; the answer is
  the shared answer call over every section it looked at. Run with MAX_LEN=131072 (the conversation grows each step;
  estimated 15k–30k tokens per claim vs A4's 6.5k).
- **A3 dev check (5 Nov, 20 dev claims, a/react ff1b056, A40)** [7, 9]: runs on both models, 0 errors.
  Llama: 9/20 (A4 9, A0 10), evidence recall 0.88 (A4 0.90), but **50k tokens and 22 s per claim (7× A4)**: 6.1
  lookups per claim, 9 of 20 hit the 8-lookup limit, 31 of 122 lookups repeat an earlier one, 1 unusable reply.
  It asks for exclusions on 17 of 20 claims but definitions on only 4. gpt-oss: 14/20 (A4 16, A0 13), evidence
  recall 0.95 (A4 0.93), 11k tokens and 15 s per claim; stops by itself after 1.65 lookups (max 3), definitions on
  2 claims, exclusions on 5: its searches already bring back the needed sections. So the free agent rarely
  thinks of definitions; the small model loops (as the brief warned), the reasoning model stops early. Run on
  test as is (no tuning), since how the agent behaves untuned is the question.
- **ReAct (A3) in the main comparison (11 Nov, after the test results; disclosed in the report)** [4.2, 7.2, 9]:
  shown next to the four core setups in every table, chart, slide and the demo, marked "added later". score.py
  also reports the decision rule with A3 as a full candidate (`with_react` in scores.json); the planned result is
  unchanged. As planned: A0 wins on both models. With A3: the top two become A3 and A4, not separated (p = 1.00
  Llama, 0.43 gpt-oss), so A4 wins as the cheaper. A3 vs A0: p = 0.36 / 0.18 (Holm 0.23 on gpt-oss as best agent).
  Finding: the top-two tie-break makes the formal winner depend on which setups are in the race; what holds either
  way is that no agent is significantly more accurate than A0. Headline: "simple RAG is the best value, the
  workflow agent the safest". YZ built A3 (b93b856, 4 Nov); the Contributions paragraph does not say so yet.
- **Advice to an insurer, refined (11 Nov)** [9]: simple RAG as the main engine, workflow agent re-checks every
  "covered" (0 of 53 wrong, 66% accuracy, about 1.8x tokens, simulated). ReAct only for open-ended questions
  (comparing plans, multi-part questions), with a strong model and a lookup cap: claim checking is well-structured,
  where Topic 7 slide 36 (ReAct vs Plan-and-Execute) favours a fixed plan, and A3 was less safe (4 of 53 vs 1) with
  unpredictable cost (7.9 calls on Llama). Invest in the model first (+13 points vs at most +6 from method). At
  about 70% accuracy, point customers to the deciding clauses and leave the claim decision to a person.
- **Power** [9]: with the observed discordance (32 to 42 of 124 claims), a 5-point gap needs about 800 to 1,100
  claims for 80% power (McNemar, two-sided 5%); about 230 to 290 for a 10-point gap.
- **Course links** [1, 2]: Topic 7 slides 18-19 (ReAct loop), 36 (ReAct vs Plan-and-Execute: the workflow agent is
  Plan-and-Execute), 38 (planning ladder); Topic 8 slides 10-12 (long context, lost in the middle: Full-context),
  13 (RAG pipeline), 28 (BM25 hybrid: retrieval-only check), 32 and 43-44 (query rewriting, judge and re-query:
  corrective RAG), 46 (faithfulness, trajectory metrics), 47 (cap retrieval calls).
- **Why these two models** [4.3]: largest that fit one 48 GB student GPU. Shared models on the cluster
  (/common/public/llm-models, checked 11 Nov): Llama 3.1 8B/70B/405B, Llama 3.3 70B, gpt-oss-20b/120b,
  DeepSeek-R1 and its 7B/8B/14B/32B/70B distills, Qwen2.5-VL 7B/72B, NVLM-D-72B, Janus, whisper; several folders
  locked. Only the R1 distills (7B to 14B) were real alternatives, and they are reasoning models like gpt-oss.
- **Names and presentation (11 Nov)**: report, slides, script, demo and charts use names instead of codes
  (B0 No-RAG, A0 RAG, A2 CRAG, A4 Agent, L0 Full-context, A3 ReAct, A4D Agent-Pick, A0K10 RAG-10); code and
  results files keep the IDs. Report cut toward 10 pages; slides cut to short cue phrases; slide 3 has a ReAct row,
  slide 6 a ReAct bar, slide 9 a ReAct line. Demo: ReAct card (live, plus saved test-run answers for fwd-010 and
  fwd-003; not covered on fwd-010, like A4). Charts: scatter plots show the core setups, ReAct and Full-context.
- **Live demo test (11 Nov, L40S job 363304, gpt-oss)** [8]: all four methods run live, steps shown as they happen.
  Manila (fwd-010): simple RAG covered every time (wrong), the workflow agent not covered every time (right), ReAct
  not covered in 2 of 3 live runs and in the test run (3 of 4 right): it picks its own searches, and once looked for
  weather exclusions instead of the news exclusion. Slide 9 and the script no longer promise ReAct finds it. ReAct
  answers saved for all 7 scripted examples; neither injection test made it say covered.
- **Policy limit in the demo (11 Nov)** [8]: YZ asked for the dollar amount on covered verdicts. The brief's
  guardrail forbids promising a payout, amounts were never evaluated, and the payout depends on the plan, so the
  card quotes the cited benefit's limit per plan from the policy (FWD table of benefits, MSIG "The maximum we will
  pay under this section is:" lines), labelled "Policy limit, not an estimate". No calculation; no block for
  no-retrieval or non-covered verdicts; "see your policy schedule" when the clause prints no limit.
- **Demo layout, round 2 (11 Nov)** [8]: at 1440 px the four cards were 239 px wide and up to 1,457 px tall. Now: the
  sidebar starts collapsed and the page is wider (cards 300 px, at most about 1,000 px tall); flat verdict labels instead
  of tilted stamps; one-line reason; clause titles with one deciding quote; policy limit as "Up to S$300 - S$1,000, by
  plan" plus its basis; one fold-out per card. The summary is now one table of this claim's answers (verdict, right
  or wrong, time, calls, clauses cited); the static 124-claim results are folded below it. Live run 3 on Manila: ReAct
  right again (4 of 5 runs), and no retrieval guessed not covered for a wrong reason (weather), so the script has a
  fallback line for that.
- **Agentic RAG naming (11 Nov)** [4.2]: No-RAG and RAG are the baselines; CRAG, the workflow agent and ReAct are all
  agentic RAG (the model makes retrieval decisions), so they are named "Agentic RAG: Corrective / Workflow agent /
  ReAct" in the report's setup list and table, the abstract and slide 3. Short names stay in charts and results
  tables. Demo columns sit under ruled "Baselines" and "Agentic RAG" headers. Safe mode is not a sixth
  method: it is simple RAG with the workflow agent re-checking each "covered".
- **Demo look, round 3 (11 Nov)** [8]: YZ found the rounded cards generic. Now one flat page: no cards, shadows,
  pills or gradient banner; a masthead with the policy, model and live/saved status; the four methods as plain
  columns under two ruled headers ("Baselines", "Agentic RAG"); the verdict in large coloured serif type, with the
  right/wrong mark straight under it; numbered steps (running step orange, steps to come grey); a ruled summary
  table. All four verdicts and marks fit on the first screen at 1280 x 720; no sideways scroll at phone width.
  Another live run on Manila (gpt-oss): no retrieval not covered (a guess, weather reason), simple RAG covered (wrong),
  workflow agent not covered (right), ReAct covered (wrong). ReAct is now right in 4 of 6 runs on this claim (the test run and 5 live);
  the script's fallback line says so.
- **Demo look, round 4 (12 Nov)** [8]: round 3 was too flat (the four methods ran together). Now the results are one
  white panel with a line between methods: a band per group (slate "Baselines", navy "Agentic RAG"), the name
  and time on a tint, the verdict as a solid colour block (green covered, red not covered, slate need more
  detail), the right/wrong mark under it, and ruled, labelled sections (what it did, why, clauses, policy limit).
  The summary table is a white panel too. Checked at 1280 x 720 (all verdicts on the first screen) and phone width.
  Another live run on Manila: no retrieval need more detail, simple RAG covered (wrong), workflow agent not covered
  (right, 13.4 s), ReAct need more detail (wrong). The workflow agent has been right in every run, ReAct in 4 of 7
  (the test run and 6 live); the script's ReAct fallback now covers "need more detail" too.
  Then, at YZ's request, a little rounding: the panel's outer corners, the verdict blocks, small pill tags and
  right/wrong marks (in the columns and the summary table), circled step numbers, softer buttons and text box. The
  column lines and group bands stay square; on a phone each stacked method is its own rounded box.
  The 124-claim results fold-out is now its own panel. Its wrong-"covered" column is renamed "Said 'covered' on a
  not-covered claim (of 53)" (YZ asked why only 53: that mistake is only possible on the 53 test claims whose answer
  is not covered; "Right" is over all 124), and the three takeaways (best value, safer, our advice) are separate blocks.
  Reverted (12 Nov, YZ's call): the demo look is back to the 11 Nov card version (commit 92489df: navy banner,
  rounded cards with Baseline / Agentic RAG labels, flat verdict stamps). Kept from rounds 3-4: the renamed
  columns ("Right (of 124)", "Said 'covered' on a not-covered claim (of 53)"), the clean-up of stray "}" and ".…"
  in the one-line reasons, and the live-run counts and script fallback for ReAct.
- **A0K10 on test (11 Nov, branch a/a0-k10 at bd31b05, L40S; exploratory, a test only; code merged in PR #71)** [7]: A0 with
  top_k 10. 124 claims each, 0 errors. Accuracy (wrong-covered): gpt-oss 0.70 (0.15) vs A0 0.69 (0.17), McNemar
  p = 1.00 (13 vs 12); Llama 0.59 (0.13) vs A0 0.56 (0.13), p = 0.607 (9 vs 6). Evidence recall 0.66 to 0.75 on
  both; tokens 1.7× (gpt-oss 3,247 to 5,382; Llama 2,635 to 4,573). So more passages find more evidence but do not
  give more right answers; winner unchanged (A0). Ran on the L40S node `lucas` because the A40 node `avenue` was
  drained, so seconds are not comparable. Not judged (no Haiku spend).
- **A3 and A4D on test (6 Nov, main c184cad, A40; exploratory, never in the decision rule)** [7, 9]: 124 claims
  each, 0 errors, 0 duplicates. Winner unchanged: A0 on both models. Accuracy (wrong-covered):
  Llama A3 0.61 (0.11), A4D 0.58 (0.09) vs A4 0.61 (0.08), A0 0.56 (0.13); gpt-oss A3 0.76 (0.08), A4D 0.73
  (0.06) vs A4 0.71 (0.02), A0 0.69 (0.17). No exploratory McNemar test is below 0.05 (lowest: gpt-oss A3 vs A0,
  p = 0.185). Cost per claim: Llama A3 46k tokens, 7.9 calls, 16.6 s (A4: 6.6k, 3, 9.5 s); gpt-oss A3 8.3k, 3.4
  calls, 11.3 s (A4: 6.5k, 3, 15.2 s). A4D: about 1.1–1.2× A4's tokens, 4 calls.
  A3 behaviour as on dev: Llama 6.3 lookups per claim, hits the 8-lookup limit on 52 of 124, 155 of 778 lookups
  repeat an earlier one, definitions on 33 claims, exclusions on 96. gpt-oss 1.4 lookups, stops by itself (2
  unusable), definitions on 6 claims, exclusions on 15, evidence recall 0.77 (A4 0.84), yet the most accurate
  setup with L0 (0.76): the reasoning model decides well from less evidence. A4D's evidence recall 0.94 / 0.85
  (A4 0.91 / 0.84); it fixes fwd-059 on gpt-oss (covered, A4 said not_covered), not on Llama.
  Judge (7 Nov, Haiku, US$0.076 for the 496 new rows, all judged): faithfulness Llama A3 0.40, A4D 0.35 (A4 0.29,
  A0 0.38); gpt-oss A3 0.72, A4D 0.63 (A4 0.68, A0 0.63). Grounded rate Llama A3 0.27, A4D 0.27 (A4 0.23); gpt-oss
  A3 0.45, A4D 0.48 (A4 0.48).
- **Extra analyses from existing test answers (7 Nov, no new runs; exploratory)** [7, 9]:
  1. *Does skipping definitions hurt?* On needs_definition claims (n = 20) A3 is the weakest agent on both models:
     Llama A3 0.55 vs A4 0.70, A4D 0.65; gpt-oss A3 0.45 vs A4 0.60, A4D 0.65. On single_section claims (n = 65)
     gpt-oss A3 is best (0.82 vs A4 0.69, McNemar p = 0.10). Same direction on both models, fits A3 rarely fetching
     definitions, but no category test is significant (small n).
  2. *Oracle (headroom).* Claims at least one setup gets right: Llama 95/124 (core four) and 103/124 (all seven);
     gpt-oss 113 and 122 of 124. Best single setup: 76 and 94. The setups fail on different claims, so a way to
     choose between them (e.g. safe mode) has room to help; an oracle needs the gold label, so it is an upper bound,
     not a result. Every setup on both models misses fwd-030 (S$800 cash stolen; gold partially_covered because of
     the S$300 sub-limit in the benefit-limits table): the sub-limit sits in a separate table section.
  3. *More lookups do not help A3.* Llama A3 accuracy by lookups: 1–2 (n = 5) 1.00, 3–5 (n = 36) 0.50, 6–8
     (n = 83) 0.64; A4 on the same claims 0.80, 0.56, 0.63. A3 tracks A4 in every group, so the groups reflect how
     hard the claims are, not a gain from looking more. gpt-oss never goes past 5 (1–2: n = 113, 0.76; 3–5: 11, 0.73).
- Engineering [6.4]: two test jobs cannot run side by side from one cluster checkout: run.py's dirty check counts
  the first job's results files as uncommitted changes and refuses the second. Fixed for this run by hiding the
  four results files from git status (`git update-index --assume-unchanged`, undone after); code was main c184cad.
- **A4D added 5 Nov as exploratory (Member B, PR #61)** [4.4, 7]: A4 plus an LLM pick of up to 3 definitions from the
  defined-terms list, on top of the name matches (A4 itself unchanged). Dev: gpt-oss 17/20 vs A4 15/20, Llama 10/20
  both, about 1.2× A4's tokens; evidence recall equals A4 (dev has only 3 gold definitions, all found by name). Found in
  review: A4D was not in EXPLORATORY, so it could have won the decision rule; added there (and to the charts) with a
  test that A3 and A4D never win.

## E. Engineering fixes to add to 6.4 (found by validation before the test run)

- Binary accuracy counted a failed answer (error row) as right when the gold verdict was not_covered or
  insufficient_info; now every error row is wrong in every metric (PR #37).
- The grounded rate stayed blank for any setup with a parse error, because the judge skips error rows; error rows now
  count as not grounded (PR #35, found in Member B's review).
- Two batch jobs on the same node would share one server port; the second job gets its own port (`BATCH_PORT=8483`).

## F. Pending: items from others or from the test run

- [x] Final test runs, both models (30–31 Oct, commit b80d7c3; L0 after each core run, same results folder). Each
      model: 620 rows (124 claims × B0, A0, A2, A4, L0), 0 failed, no duplicates, L0 servers at 131,072 context.
      Error rows: Llama 0; gpt-oss 1 in A2 and **8 of 124 in L0**, all parse_error at the 8,192-token output cap
      (the model reasoned on the 28k–45k-token prompt until the cap, so no JSON answer). Counted as wrong, as for every
      setup; report it with L0 [7.6]. Reasoning tokens are logged on every row that parsed.
- [x] Haiku judge on the test outputs (PR #44: every row judged, 620 Llama, 611 gpt-oss; the 9 error rows are skipped
      by design), then 30 hand-checks per model (Member B). From `judge.py --agreement` [7.9, 5.1]:
      Llama 77% agreement, kappa 0.64; gpt-oss 80%, kappa 0.52. The judge is slightly stricter than the human (gives
      partly / no more often). Verbosity check over all judged rows, mean explanation words per judge label: Llama
      yes 59.8, partly 71.4, no 69.8; gpt-oss yes 67.8, partly 77.4, no 61.5: "yes" is not the longest, so no sign
      the judge rewards longer explanations.
- [x] Trace hand-check: rows 11–20 Member B (PR #44), rows 1–10 Member A (4 Nov): 9 right, 1 over-cautious
      insufficient_info; written into RESULTS 7.7. [7.7]
- **New finding (4 Nov): CRAG's rewrite rarely helps** [7.7, 9]. A2 rewrote on 25 (Llama) / 70 (gpt-oss) of 124
  claims; a rewrite added a needed section only 2 / 5 times, so A2's evidence recall equals A0's. On gpt-oss 42 of 70
  rewrite replies were unusable (most likely reasoning past the 2,048-token reply limit; failed rows take 42 s vs
  28 s; cause not logged). Fits A2 < A0 on gpt-oss (0.62 vs 0.69) and its 27.6 s latency. Discussion: the
  generic self-correction loop costs calls without finding the definitions and exclusions; A4's structured lookups
  do. Future work: raise the reply limit for reasoning models and log why a step failed.
- [x] Error analysis with the error types (Member B, PR #48): all 176 wrong A0/A4 answers labelled, AI drafts kept
      next to the human labels; "other" split by rule (see B). [7.7 / error analysis]
- [x] Prompt-injection questions in the demo (Member B, PR #48, DEMO_SECTION): 4 questions × A0, A4 on gpt-oss;
      no answer said covered or cited the injected text; 5 of 8 matched the expected verdict (misses are cautious:
      2 insufficient_info on the sunglasses claim, 1 not_covered on the kennel claim). [8]
- M3 (4 Nov) met on 3 Nov: leaderboard, McNemar, charts and decision rule (A0 on both models) on main; judge,
  hand-checks, error types and demo on the winner (A0, A4 behind a toggle; 16 cached gpt-oss answers, none for
  Llama) on main. Left: Member A's trace rows 1–10, then section H.
- [x] Commit `results/test/retrieval/` (on the laptop) together with the test results (branch `a/test-results`).
- [x] A3 (ReAct): dev check on both models (does it run, how many lookups, does it use definitions and exclusions),
      then one test run per model from main, judge (print the cost first), report rebuilt. [4.2, 7, 9]
- [x] Safe mode numbers: `report.py` `safe_mode()` adds a table to leaderboard.md (same numbers as D; rebuilt
      with A3). [x] Demo toggle (Member B, PR #60: A4 re-checks every A0 "covered"; fwd-010 cached as the
      catch: gold not_covered, A0 covered, A4 not_covered on gpt-oss test).
- [x] A4D and A3 test runs (6 Nov, c184cad); report rebuilt. [x] Judge on the 248 new rows per model (7 Nov, US$0.076).
- [x] A0K10 test runs (11 Nov, bd31b05, L40S); scores, traces and report rebuilt on branch a/a0-k10.
- [ ] A0 plus structure lookups; A2 gpt-oss rerun with a larger reply limit (if time).

## G. Checks to run when the test results land (before writing any number)

- Before every cluster run, `git log -1 --oneline` on the cluster must show main at b80d7c3 or later.
- Every row in `results/test/<model>/raw.jsonl` has the same commit, without "-dirty", and 124 claims × each setup.
- A0's evidence recall on test (traces) equals dense k = 5 gold recall in R1 (0.66). If not, find out why before use.
- No setup has an unusual number of errors (parse errors, length limits); if one does, report it.
- L0 rows exist for both models and the server log shows the 131k context; L0 never appears as the winner.
- The judge ran on every row before quoting faithfulness or grounded rate (both stay blank otherwise).

## H. Writing the final report (one pass)

1. For each model (`vllm_llama8b`, `vllm_gptoss20b`): `python -m src.eval.score --model <model> --split test` and
   `python -m src.eval.traces --model <model> --split test`; then `python -m src.eval.report --split test`
   (leaderboard, charts) and `python -m src.eval.traces --split test --sample 20` (hand-check sheet).
2. (Done 4 Nov.) Fill every [placeholder] in RESULTS from `results/test/report/leaderboard.md`, the charts, `scores.json`,
   `traces.json`, `results/test/retrieval/retrieval.md` and the judge hand-checks.
3. (First merged draft 4 Nov: `docs/REPORT.md`, about 4,600 words before contributions, 4 figures, 5 tables;
   both members still edit their own parts in their own words.) Merge DATA, METHOD, RESULTS, DEMO into one document with the section numbers above; add every item in R and B–E to its
   section; write Introduction, Discussion (D) and Conclusion.
4. Keep the pre-registered story first (decision rule, Holm-corrected tests); exploratory items (L0, retrieval-only,
   citation checks) are labelled as such.
5. Rubric gaps found 4 Nov (B-level checklist in the course pack), all must be in the final submission. Split agreed
   4 Nov: README Member A; architecture diagram and related work Member B; each writes the other's contributions.
   - **Related work** (short, about half a page): CRAG (Yan et al. 2024), ReAct (Yao et al. 2022), LLM-as-judge,
     long context vs RAG. Not in any section yet.
   - **Architecture diagram**: the shared pipeline (ingest → index → setup → verdict schema → scoring) with B0, A0,
     A2, A4, L0 side by side.
   - **README**: full laptop and cluster setup and how to rerun every result. Done 4 Nov (`a/readme`).
   - **Contributions**: each member documents the other's contributions (course requirement).
   - Keep the report about 10 pages: simple, concise sentences; only the numbers that matter.
6. Final check: every number traces to a results file; dev numbers appear only as development checks; no promise of
   payout anywhere (demo guardrail wording).
7. (8 Nov) REPORT.md: Section 5 now has three "what we measure" tables (answer, process, cost: question, how
   computed, better) and the decision rule as a 3-step table; 7.2 shows the rule step by step per model; 7.3 has a
   cost table vs A0 (calls, tokens ×A0, seconds ×A0, hours per 1,000 claims). A2's gpt-oss latency ratio is 4.7×
   (27.65 / 5.83 s from leaderboard.csv), not 4.8× (the old figure divided rounded numbers).
8. (8 Nov) Demo UI: disclaimer removed at YZ's request (REPORT 8 and DEMO_SECTION now cite the hedged headlines
   instead); redesigned (navy sidebar and title banner with a flight-path drawing, white cards on warm paper, burnt-orange
   button, Fraunces display font) with the verdict as a rubber stamp; theme in .streamlit/config.toml; plus a
   verdict card; example-question pills fill the exact cached text; saved answers are labelled as saved. The search
   model now loads in the background when the app starts (the first new question used to wait about 20 s for it).
   One-command start/stop: scripts/demo_start.ps1 (-Offline for cached only) and scripts/demo_stop.ps1.
   Second pass (impeccable critique): the step trace is now a numbered plain-words list (raw JSON kept below it),
   the verdict card names clauses by title, clause text is readable serif (not monospace), compare columns are
   titled "Simple RAG (A0)" / "Claims workflow (A4)", and an empty-state line says what an answer contains.
9. (8 Nov) Demo live mode: with the model server up, "Run live on the cluster" runs A0 and/or A4 now (Both = at the
   same time, side by side) and redraws each setup's own step trace four times a second, with a running clock and the
   second each step finished. A4 runs B's unchanged graph (build_graph) with a shared steps list; A0 repeats its 3-line
   run() so the search step shows before the model call. Live answers are not written to the demo cache.
10. (9 Nov) REPORT 4.2 now explains every setup: a summary table (how each finds policy text, measured calls per
    claim, pre-registered or exploratory) plus a bullet each, with A3, A4D and safe mode added. Related work no longer
    says the ReAct agent was not built. Demo safe mode now re-checks partially covered as well as covered, matching
    report.py safe_mode (POSITIVE), so the demo and the reported safe-mode numbers use the same trigger.
    Live timing (9 Nov, gpt-oss, 6 new questions): A0 3.2–7.6 s; A4 7.2–19.5 s (1 of 6 over 15 s). On test, A4 is
    over 15 s on 49 of 124 claims (median 13.7 s); the time follows gpt-oss's reasoning tokens. reasoning_effort=low
    cut A4 to 3.0–4.6 s but changed 5 of 6 verdicts, so it is not used.
11. (9 Nov) Demo three-way view: the sidebar's Method radio is now tick boxes for B0, A0 and A4 (all ticked by
    default); ticked methods run at the same time in equal columns (B0 left, A4 right). Each card: name and clock,
    verdict stamp (above the steps, so the verdicts line up), "What it did" step list (live or saved), then the
    explanation and clauses. B0 keeps its own verdict (no citation guard, since it reads no policy) and is labelled a
    guess; made-up clause IDs are still dropped. Safe mode reuses A4's answer when A4 is ticked; the quote check
    skips B0. For the presentation, the Manila example splits the methods (saved: A0 covered, A4 not covered).
    Each verdict stamp lands as soon as its own method finishes. B0 answers saved for all 7 examples (gpt-oss).
    Live Manila, all three at once (9 Nov, 4 runs): B0 insufficient_info every time (3.9–7.1 s); A4 not_covered
    every time, citing the "events that happen before you book" exclusion (15.0–20.0 s); A0 covered in 3 of 4
    (5.7–9.5 s) and insufficient_info once (17.7 s). vLLM is not fully deterministic, so A0's split is not guaranteed.
    Card body shortened for the projector: "Why" shows at most 2 sentences of the model's reasoning (the sentences
    that quote nothing; section IDs replaced by clause titles), "The clauses behind it" shows one line per cited
    clause (the wording the answer quoted from it, else its first sentence, max 150 characters). The full explanation
    and clause text are one click away; nothing is changed in the stored answers.
    "Which one wins?" panel under the cards: left, this claim (agree/disagree, verdict chips, the time on each card's
    clock, clauses only A4 found); right, the test results for the chosen model from leaderboard.csv (accuracy bars,
    wrong "covered" of 53, time) and three takeaways (Best value A0, Safer A4, advice: A0 with A4 checking "covered").
    Live check (9 Nov, gpt-oss, the page end to end): Manila B0 need more detail 6.0 s, A0 covered 11.8 s, A4 not
    covered 13.1 s; Osaka phone theft, all three need more detail (7.4 / 10.1 / 21.0 s). The first question after the
    server starts is slower (about 20 s per method), so ask one warm-up question before presenting.
    Demo fixes (11 Nov): the verdict stamp no longer overlaps the line under it; after "Check my claim" the banner
    shrinks so all three verdicts fit on the first screen; when the claim is word for word a labelled dev or test claim
    (e.g. Manila = fwd-010), each card shows a tick or cross against our gold label and the panel names the correct
    answer. Labels are only displayed, not changed.
    Card badges: "Best value" on A0 (was "Study winner"; renamed 11 Nov to match slide 10) (orange line along the top of its card) and "Safer than A0" on A4 (wrong
    covered 1 vs 9 of 53 on gpt-oss, 4 vs 7 on Llama, so true on both models); B0 has none.
