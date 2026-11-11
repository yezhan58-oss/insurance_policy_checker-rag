# Insurance policy checker (IS469 agentic RAG)

Given a travel insurance claim ("my flight was delayed 7 hours by a typhoon, can I claim?"), decide the verdict
(covered / not_covered / partially_covered / insufficient_info) and cite the policy sections that decide it. We compare
four setups on two real policies (FWD, MSIG) and two open models (Llama 3.1 8B, gpt-oss-20b), then ship the winner as
a small Streamlit demo. Full design: `PROJECT_BRIEF.md`; report drafts: `docs/`.

| Setup | What it does |
|---|---|
| B0 | No retrieval: the model answers from the claim alone (floor) |
| A0 | Simple RAG: one search with the claim, top 5 chunks |
| A2 | Corrective RAG: grade chunks, rewrite the query up to 2 times |
| A4 | Claims workflow: benefits, then definitions, then exclusions, then verdict |
| L0 | Exploratory: the whole policy in the prompt (not in the decision rule) |
| A3 | Exploratory: ReAct agent that chooses its own lookups (search, definition, exclusions); not in the decision rule |

**Result (test, 124 claims):** A4 was the most accurate pre-registered setup (0.61 Llama, 0.71 gpt-oss) but not
significantly better than A0 (0.56, 0.69), so the pre-registered rule picks the cheaper A0 on both models. Details:
`results/test/report/leaderboard.md`.

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

All reported numbers come from one run per model on `main` at commit b80d7c3 (`results/test/`). Check that the
cluster is up to date first (`git log -1 --oneline`).

**Model answers (cluster).** The test runs took about 40 minutes (Llama) and 2 hours (gpt-oss), plus 10 and 35
minutes for L0. From `~/insurance-rag` after `git pull`:

```
MODEL=vllm_llama8b sbatch scripts/run_eval.sbatch
MODEL=vllm_gptoss20b sbatch scripts/run_eval.sbatch
MODEL=vllm_llama8b APPROACHES=L0 MAX_LEN=131072 sbatch scripts/run_eval.sbatch
MODEL=vllm_gptoss20b APPROACHES=L0 MAX_LEN=131072 sbatch scripts/run_eval.sbatch
MODEL=vllm_llama8b APPROACHES=A3 MAX_LEN=131072 sbatch scripts/run_eval.sbatch
MODEL=vllm_gptoss20b APPROACHES=A3 MAX_LEN=131072 sbatch scripts/run_eval.sbatch
```

Each job starts a private vLLM server, rebuilds the index, runs `python -m src.eval.run` and writes
`results/test/<model>/raw.jsonl` (resumable: resubmit a cut-off job and it skips finished rows). Run the L0 jobs after
the core run of the same model. L0 and A3 are exploratory (added after the comparisons were fixed).

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
powershell -ExecutionPolicy Bypass -File scripts\demo_start.ps1     (starts the gpt-oss server, tunnel and app)
powershell -ExecutionPolicy Bypass -File scripts\demo_stop.ps1      (closes the tunnel, frees the GPU)
streamlit run app/streamlit_app.py                                  (app only: saved answers, or a server you started)
```

Pick a policy and a model, describe what happened, and tick the methods to compare: no retrieval (B0), simple RAG
(A0, the winner) and the workflow agent (A4). Ticked methods run at the same time, side by side; with the model server
up, each card shows its steps live and its verdict as soon as it finishes. Each card gives a hedged verdict, a short
"why", one line per cited clause (full wording one click away) and the step trace. Under the cards, "Which one wins?"
says what differed on this claim and shows the study's test results for the chosen model. Two exploratory toggles,
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
| `docs/` | report drafts and `REPORT_NOTES.md` |
