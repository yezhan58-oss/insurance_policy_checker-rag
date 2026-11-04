# Report draft: Contributions

Course requirement: each member documents the other's contributions. Member A's paragraph is written by Member B;
Member B's paragraph is written by Member A. From the git history (commit subjects on main) and the brief's task split.

## Member A (YZ), written by Member B

YZ set up the shared infrastructure that the whole study ran on. They tested and documented the SMU GPU cluster setup
(vLLM servers and batch scripts), and wrote the repository skeleton and the shared contracts (output schema, model
client, store). They also wrote the ingestion of both policies (FWD and MSIG) into sections with stable IDs, and the
search over them. They switched the study to the two free cluster models when the planned API credits turned out not
to cover API calls. They built three of the five setups: B0 (no retrieval), A0 (simple RAG) and A2 (corrective RAG,
including its dev trials). They also added the exploratory long-context baseline L0 and the retrieval-only comparison
(dense, BM25, hybrid). On evaluation, they wrote the run and scoring pipeline: resumable runs, bootstrap confidence
intervals, Holm-corrected McNemar tests, the decision rule, and the trace metrics, including the split between sound
answers and answers that were right without the evidence. They also wrote the leaderboard and charts. They blind-labelled
40 test scenarios for the agreement check (kappa 0.46), submitted the final test runs on both models, and hand-checked
10 agent traces. In the report they wrote the method, evaluation design, development and results sections, kept the
running list of findings for the report, and reviewed every number in the discussion.

## Member B, written by Member A

[Member A to write.]
