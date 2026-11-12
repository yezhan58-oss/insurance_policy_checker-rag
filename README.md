# Insurance policy checker (IS469 agentic RAG)

Given a travel insurance claim ("my flight was delayed 7 hours by a typhoon, can I claim?"), decide the verdict
(covered / not_covered / partially_covered / insufficient_info) and cite the policy sections that decide it. We compare
five methods (two baselines and three agentic RAG setups) on two real policies (FWD, MSIG) and two open models
(Llama 3.1 8B, gpt-oss-20b), then show them side by side in a small Streamlit demo. Full design: `PROJECT_BRIEF.md`;
final report: `docs/REPORT.md`.

| ID | Name in the report | What it does |
|---|---|---|
| B0 | No-RAG (baseline) | No retrieval: the model answers from the claim alone (floor) |
| A0 | Simple RAG (baseline) | One search with the claim, top 5 chunks |
| A2 | Agentic RAG: Corrective (CRAG) | Grade chunks, rewrite the query up to 2 times |
| A4 | Agentic RAG: Workflow agent | Benefits, then definitions, then exclusions, then verdict |
| A3 | Agentic RAG: ReAct | Chooses its own lookups (search, definition, exclusions), max 8; added after the core runs and reported with and without it in the decision rule |
| L0 | Full-context (exploratory) | The whole policy in the prompt |
| A4D | Agent-Pick (exploratory) | A4 plus up to 3 definitions the model picks |
| A0K10 | RAG-10 (exploratory) | A0 with 10 chunks instead of 5 |
| – | Safe mode (exploratory) | A0, with A4 re-checking every covered or partially covered; simulated from stored answers by `src.eval.report` |

**Result (test, 124 claims):** the agents were the most accurate (A4 0.61 Llama / 0.71 gpt-oss, A3 0.61 / 0.76) but
not significantly better than A0 (0.56 / 0.69), so the pre-registered rule picks the cheaper A0 on both models (with A3
included, its tie-break picks A4). A4 was the safest: on gpt-oss it wrongly said "covered" on 1 of 53 not-covered
claims, against 9 for A0 (exploratory, p = 0.021). Our advice to an insurer is therefore A4, with A0 as the budget
option. Details: `results/test/report/leaderboard.md` and `docs/REPORT.md`.

## 1. Laptop setup (Windows; Python 3.11 or 3.12)

```
git clone https://github.com/yezhan58-oss/insurance_policy_checker-rag insurance-rag
cd insurance-rag
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env` (never commit it): `VLLM_API_KEY` (a password you make up for your vLLM servers), `VLLM_PORT` and
`VLLM_GPTOSS_PORT` (Member A 8471 / 8473, Member B 8472 / 8474), and `ANTHROPIC_API_KEY` only if you run the judge.
Do not set `ANTHROPIC_API_KEY` as a Windows environment variable, or Claude Code bills it instead of your subscription.

## 2. Build the index and run the checks

```
python -m src.ingest
pytest -q
```

`src.ingest` reads the PDFs in `data/policies/` (URLs and download dates in `SNAPSHOT.md`), splits them by the
policy's own headings into sections with stable IDs (e.g. `fwd:travel_delay`), embeds the chunks with
`BAAI/bge-small-en-v1.5` on CPU and writes a Chroma index to `data/index/` (git-ignored). It is deterministic, so every
machine builds the same index. It prints 10 random sections per policy for a parsing check.

## 3. Cluster setup (SMU "origami", once per member)

Follow `CLUSTER_SETUP.md` (tested 17 Oct 2026): SSH key, clone, `.env`, uv environment, then
`sbatch scripts/install_vllm.sbatch`. Both models come from the cluster's shared copies, so no Hugging Face access is
needed. Everything that uses a GPU goes through `sbatch` (never on the login node).

For interactive work: `sbatch scripts/serve_llama.sbatch` (or `serve_gptoss.sbatch`), wait for "Application startup
complete" in `logs/`, then open a tunnel in its own window (`ssh -N -L <port>:<node>:<port> origami`). Cancel the job
with `scancel <jobid>` when done.

## 4. Reproduce every result

B0, A0, A2, A4 and L0 ran once per model on `main` at commit b80d7c3; the later runs ran at c184cad (A3, A4D) and
c64d688 / bd31b05 (A0K10 on Llama / gpt-oss). Every row of `results/test/<model>/raw.jsonl` records its commit,
and `scores.json` lists them. Check that the cluster is up to date first (`git log -1 --oneline`).

**Model answers (cluster).** The test runs took about 40 minutes (Llama) and 2 hours (gpt-oss), plus 10 and 35
minutes for L0. From `~/insurance-rag` after `git pull`:

```
MODEL=vllm_llama8b sbatch scripts/run_eval.sbatch
MODEL=vllm_gptoss20b sbatch scripts/run_eval.sbatch
MODEL=vllm_llama8b APPROACHES=L0 MAX_LEN=131072 sbatch scripts/run_eval.sbatch
MODEL=vllm_gptoss20b APPROACHES=L0 MAX_LEN=131072 sbatch scripts/run_eval.sbatch
MODEL=vllm_llama8b APPROACHES=A3 MAX_LEN=131072 sbatch scripts/run_eval.sbatch
MODEL=vllm_gptoss20b APPROACHES=A3 MAX_LEN=131072 sbatch scripts/run_eval.sbatch
MODEL=vllm_llama8b APPROACHES=A4D sbatch scripts/run_eval.sbatch
MODEL=vllm_gptoss20b APPROACHES=A4D sbatch scripts/run_eval.sbatch
MODEL=vllm_llama8b APPROACHES=A0K10 sbatch --gres=gpu:l40s:1 scripts/run_eval.sbatch
MODEL=vllm_gptoss20b APPROACHES=A0K10 sbatch --gres=gpu:l40s:1 scripts/run_eval.sbatch
```

Each job starts a private vLLM server, rebuilds the index, runs `python -m src.eval.run` and writes
`results/test/<model>/raw.jsonl` (resumable: resubmit a cut-off job and it skips finished rows). Run the L0 jobs after
the core run of the same model. L0, A3, A4D and A0K10 were added after the comparisons were fixed. A0K10 ran on an
L40S because the A40 node was drained, so its seconds are not compared.

**Faithfulness judge (laptop, Claude Haiku 5.5, paid from a US$5 budget).** Without `--yes` it only prints the
estimated cost; check it before running.

```
python -m src.eval.judge --model vllm_llama8b --split test
python -m src.eval.judge --model vllm_llama8b --split test --yes
python -m src.eval.judge --model vllm_llama8b --split test --export 30
python -m src.eval.judge --model vllm_llama8b --split test --agreement
```

(Repeat with `vllm_gptoss20b`. `--export` writes 30 random judgments for a human check; `--agreement` compares them
once filled in.)

**Scores, traces and the leaderboard (laptop, no model calls).**

```
python -m src.eval.score --model vllm_llama8b --split test
python -m src.eval.traces --model vllm_llama8b --split test
python -m src.eval.score --model vllm_gptoss20b --split test
python -m src.eval.traces --model vllm_gptoss20b --split test
python -m src.eval.report --split test
python -m src.eval.retrieval --split test
```

| Output | What it holds |
|---|---|
| `results/test/<model>/scores.json` | accuracy, safety, clause recall, faithfulness with bootstrap CIs; McNemar tests; the decision rule |
| `results/test/<model>/traces.json` | evidence recall, step recall and precision, wrong answers split by missing vs had evidence |
| `results/test/<model>/error_types.csv` | human error types on wrong A0 and A4 answers |
| `results/test/report/` | `leaderboard.md`, charts (accuracy vs cost, by category, failures, error types) |
| `results/test/retrieval/` | retrieval only: dense vs BM25 vs hybrid search, no model calls |
| `results/test/trace_sample.csv` | the 20 agentic traces hand-checked by both members (`traces --sample 20`) |

**Gold labels.** Scenarios were drafted by an LLM from specific clauses (`src/scenarios/draft.py`), reviewed by a
human (`streamlit run app/label_app.py`), split 20 dev / 124 test with a fixed seed, and a second member labelled 40
test claims blind. `python -m src.eval.agreement` reports Cohen's kappa. Rules: `data/scenarios/LABELLING_GUIDE.md`.

## 5. Demo

```
powershell -ExecutionPolicy Bypass -File scripts\demo_start.ps1     (gpt-oss server on an L40S, tunnel and app)
powershell -ExecutionPolicy Bypass -File scripts\demo_stop.ps1      (closes the tunnel, frees the GPU)
streamlit run app/streamlit_app.py --server.port 8502             (app only: saved answers, or a server you started)
```

Pick a policy and a model, describe what happened, and tick the methods to compare: no retrieval (B0) and simple RAG
(A0, the winner) as the baselines, the workflow agent (A4) and the ReAct agent (A3) as agentic RAG. Ticked methods
run at the same time in side-by-side cards; with the model server up, each card shows its steps live and its
verdict as soon as it finishes. Each card gives a hedged verdict (with a tick or cross when the claim is one of our
labelled claims), a short "why", the cited clauses with the deciding wording (full text one click away), the policy
limit for a covered verdict, and the step trace. Under the cards, "This claim, side by side" compares the answers,
times and model calls, with the study's test results for the chosen model folded below. Two exploratory toggles,
both off by default: safe mode (A4 re-checks every covered or partially covered from A0) and the quote check (a
covered answer that quotes wording not in the policy becomes insufficient_info). The example questions are cached in
`app/demo_cache.json` (gpt-oss), so they work offline; new questions need the model server and an open tunnel.

## Repository map

| Path | Contents |
|---|---|
| `src/schema.py`, `src/llm.py`, `src/store.py` | shared contracts: output schema, one client for every model, search |
| `src/approaches/` | one file per setup, registered in `__init__.py` |
| `src/eval/` | run, score, traces, judge, report, retrieval, agreement |
| `configs/` | models, per-setup settings, default run |
| `scripts/` | SLURM jobs: install, interactive servers, full runs |
| `data/` | policy PDFs, scenarios and gold labels |
| `docs/` | final report (`REPORT.md`, submitted copy `IS469_Group5_project_report.docx`), running findings (`REPORT_NOTES.md`), section drafts |
| `docs/figures/` | report figures; `make_architecture.py` redraws Figure 1 |
