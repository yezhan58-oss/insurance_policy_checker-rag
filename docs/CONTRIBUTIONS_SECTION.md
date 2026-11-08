# Report draft: Contributions

Course requirement: each member documents the other's contributions. Member A's paragraph is written by Member B;
Member B's paragraph is written by Member A. From the git history (commit subjects on main) and the brief's task split.

## Member A (YZ), written by Member B

YZ set up the shared infrastructure that the whole study ran on. They tested and documented the SMU GPU cluster setup
(vLLM servers and batch scripts), and wrote the repository skeleton and the shared contracts (output schema, model
client, store). They also wrote the ingestion of both policies (FWD and MSIG) into sections with stable IDs, and the
search over them. They switched the study to the two free cluster models when the planned API credits turned out not
to cover API calls. They built three of the five setups: B0 (no retrieval), A0 (simple RAG) and A2 (corrective RAG,
including its dev trials), and tuned the shared base prompt on dev
(PROMPT_TUNING.md). They also added the exploratory long-context baseline L0 and the retrieval-only comparison
(dense, BM25, hybrid). On evaluation, they wrote the run and scoring pipeline: resumable runs, bootstrap confidence
intervals, Holm-corrected McNemar tests, the decision rule, and the trace metrics, including the split between sound
answers and answers that were right without the evidence. They also wrote the leaderboard and charts,
the agreement script (Cohen's kappa between the two label sets), and the rule that splits the human "other" error
type (over-cautious insufficient_info, all-or-nothing partial). They blind-labelled
40 test scenarios for the agreement check (kappa 0.46), submitted the final test runs on both models, and hand-checked
10 agent traces. In the report they wrote the method, evaluation design, development and results sections, kept the
running list of findings for the report, and re-checked every number in Member B's sections and the discussion. They
also wrote the README: laptop and cluster setup, and how to rerun every result.

## Member B, written by Member A

Member B built the data the study rests on. They wrote the labelling guide that defines the four verdicts and how to
choose gold sections, the drafting helpers and the Streamlit review page. They drafted 156 claim scenarios from
specific clauses of both policies and reviewed every draft against the policy text. They removed 12 redundant claims
and made the seeded split (20 dev, 124 test), then resolved the blind-labelling disagreements with Member A and updated
the guide where a rule was unclear. They built the policy look-up tools and A4, the claims-workflow agent that is our
domain-specific setup, including its dev trials, and the exploratory A4D variant, in which the model picks the defined terms to look up. On evaluation, they wrote the Claude Haiku faithfulness judge with a
cost dry-run and an agreement check, and hand-checked 30 judgments per model. They also labelled the error type of all
176 wrong A0 and A4 test answers and hand-checked 10 agent traces. They built the "Am I covered?" demo with its
guardrails, an offline answer cache, a prompt-injection check, and two exploratory
safeguards: a safe mode in which A4 double-checks every "covered" from A0, and a quote check that rejects a
"covered" quoting wording not in the policy. In the report they wrote data and labelling, the A4
design, faithfulness, the demo, the discussion (including the minimum detectable gap and the safety gap in the
decision rule), related work and the architecture diagram.
