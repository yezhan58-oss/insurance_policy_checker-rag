# PROJECT_BRIEF.md: Agentic RAG for Insurance Claims (IS469 group project)

Read this whole file before writing any code. It is the source of truth for scope, design, infrastructure, team split and conventions. If something here conflicts with a request in chat, ask before deviating.

## 1. What we are building

A half-study, half-build project for SMU IS469 (Generative and Agentic AI). Team of 2. Due 10 Nov 2026 (G1) or 13 Nov 2026 (G2).

- **Task:** given a travel insurance claim scenario ("my flight was delayed 7 hours by a typhoon, can I claim?"), decide the verdict (covered / not_covered / partially_covered / insufficient_info) and cite the policy clauses that decide it.
- **Study half:** compare 4 core setups (a no-retrieval floor, simple RAG, and 2 agentic RAG approaches of different styles) on the same documents, index, models and test set. Measure accuracy, safety, justification and cost.
- **Build half:** turn the best setup into a small Streamlit "Am I covered?" demo app with guardrails.

**Research question:** Which agentic RAG approach gives the most accurate and best-justified coverage verdicts on real insurance policies, and is the gain worth the extra cost and latency compared with simple RAG?

## 2. Environment and conventions

- **Two machines, two shells.**
  - Laptops: Windows, Python 3.11 or 3.12, **Windows CMD or PowerShell** for local commands (YZ). No NVIDIA GPU.
  - SMU SCIS GPU cluster "origami" (login node `10.193.104.102`, each member uses their own SMU ID): Linux, **bash**, SLURM. Reachable on campus Wi-Fi or the SMU VPN.
- **Models**
  - Open model: `meta-llama/Llama-3.1-8B-Instruct`, served with vLLM on the cluster (node `avenue`, NVIDIA A40 48 GB, `student` partition). Each member runs their own server on their own port (section 4).
  - Backup open model if Llama access is delayed: `Qwen/Qwen2.5-7B-Instruct` (not gated). If used, change `model:` in models.yaml and serve it with `--tool-call-parser hermes` instead of `llama3_json`.
  - Second model: `openai/gpt-oss-20b` (OpenAI open-weight reasoning model, Apache 2.0), from the cluster's shared copy, served with vLLM on an A40 (section 4). It replaces the first draft's Claude Sonnet 5.5: the US$100 thought to be API credits turned out to be Claude Code cloud-session credits, which cannot pay for API calls. The study therefore compares a small standard model with a larger reasoning model, both free on SMU's cluster. (Larger shared models such as Llama 3.3 70B and gpt-oss-120b do not fit in the 48 GB a student job can get.)
  - Make normal (synchronous) calls only, so latency is measured the same way for every setup. gpt-oss-20b also produces reasoning tokens; log them in `usage`.
  - LLM judge: **Claude Haiku 5.5** via the Anthropic API ($0.10 in / $0.50 out per million tokens), paid from US$5 of Claude Console credits bought by Member A. It comes from a different company than both tested models. Print the estimated cost and wait for the human before every judge run; stop and ask if projected spend exceeds US$4.
  - The demo runs on the cluster models (with cached answers for the scripted demo questions) and never needs Claude.
  - Local Ollama `qwen3.5:4b` is only for quick "does the code run" checks. **Tune prompts on Llama 3.1 8B, not on the 4B model.**
- **One client interface for every model.** `src/llm.py` reads `configs/models.yaml` and builds `langchain_openai.ChatOpenAI` (with `base_url`) for vLLM and Ollama, or `langchain_anthropic.ChatAnthropic` for Claude, based on a `provider` field. Approach code never changes when the model changes.
- **Embeddings:** one embedding model everywhere so every setup searches the same index. Default: `BAAI/bge-small-en-v1.5` via `sentence-transformers` Always load it with `device="cpu"` (on the cluster the GPU is busy with vLLM, and CPU keeps results identical across machines). `src/ingest.py` is deterministic, so each machine rebuilds the same Chroma index with `python -m src.ingest`.
- Libraries: `langchain`, `langchain-openai`, `langchain-anthropic`, `langchain-chroma`, `chromadb`, `langgraph`, `sentence-transformers`, `pymupdf`, `pydantic`, `pandas`, `scipy`, `statsmodels`, `matplotlib`, `streamlit`, `pyyaml`, `python-dotenv`, `pytest`. vLLM is installed only on the cluster.
- Laptop: a `venv` inside the repo and a pinned `requirements.txt`. Cluster: a separate venv at `~/venvs/rag` (Python 3.11, built with `uv`).
- Secrets go in `.env` on each machine, never committed: `VLLM_API_KEY`, `VLLM_PORT`, `VLLM_GPTOSS_PORT`, `ANTHROPIC_API_KEY` (only for whoever runs the judge), `HF_TOKEN` (only needed if the Qwen backup has to be downloaded). `src/llm.py` expands `${VAR}` in models.yaml from `.env`. Commit `.env.example` with empty values.
- Fixed seeds, temperature 0 for all experiment runs (the Haiku judge keeps its default temperature: Claude 5.5 models reject any other value). Even at temperature 0, vLLM can give slightly different answers to identical calls; say so in the report. Every run writes its config and git commit hash next to its results.
- Small, reviewable steps. After each task, stop and summarise what was built, how to run it, and how it was verified.

## 3. Team setup (one time, this weekend)

### 3.1 Member A (YZ) does once

1. Create a private GitHub repo `insurance-rag`, invite Member B. Commit this file plus a `CLAUDE.md` with these lines (the `@` line makes Claude Code load the brief automatically at the start of every session):

   ```
   @PROJECT_BRIEF.md

   The human will say "I am Member A" or "I am Member B" at the start of a session. Work only on that member's tasks (section 11) unless told otherwise.
   ```
2. Claude Console: buy US$5 of API credits (only the Haiku judge uses them), set a spend limit if the Console allows it, and create an API key for the repo's `.env`. Member B needs a key only if they run the judge.
3. Do the cluster setup (section 4) first and record the tested steps in `CLUSTER_SETUP.md`, so Member B's setup goes quickly. (Done 17 Oct.)

### 3.2 Both members do on their own laptop

1. Clone the repo, create the venv, `pip install -r requirements.txt`.
2. Install the SMU VPN.
3. (No Hugging Face access request needed: the cluster has a shared copy of Llama 3.1 8B, see section 4.1.)
4. Do the cluster setup in `CLUSTER_SETUP.md` with your own SMU ID (about 30 minutes).
5. Create `.env` from `.env.example`: your own made-up `VLLM_API_KEY`, your `VLLM_PORT` (A: 8471, B: 8472) and `VLLM_GPTOSS_PORT` (A: 8473, B: 8474); `ANTHROPIC_API_KEY` only if you run the judge.
6. **Claude Code must run on your normal Claude subscription, not the API key.** Keep `ANTHROPIC_API_KEY` only in the repo's `.env` (read by our Python code). Never set it as a Windows environment variable: the Claude Code command-line tool uses that variable instead of your subscription, and every coding chat would then be billed to the API credits. The Claude desktop app signs in with your account and does not read it.

If a member uses macOS or Linux instead of Windows, use the Terminal equivalents of the CMD commands (e.g. `cat ~/.ssh/id_ed25519.pub | ssh ...` instead of `type ... | ssh ...`).

## 4. Cluster setup (each member, one time)

Both members have their own cluster account, and each runs their own copy of the setup and their own model server. This way neither depends on the other being online, and a server dying when one person's session times out does not stop the other.

**The tested step-by-step commands are in `CLUSTER_SETUP.md`** (tested end to end by Member A on 17 Oct). This section only records the decisions.

| | Member A (YZ) | Member B |
| --- | --- | --- |
| SMU ID | `yz.wong.2024` | own ID |
| `VLLM_PORT` (interactive Llama server) | 8471 | 8472 |
| `VLLM_GPTOSS_PORT` (interactive gpt-oss server) | 8473 | 8474 |
| Batch job port | 8481 | 8482 |
| `VLLM_API_KEY` | own random password | own random password |

Different ports matter because both of you may land on the same node (avenue has 4 A40s).

Etiquette: hold a GPU only while actively working; the GPUs are shared with other students. If one of you is offline for a long time, the other can still lend their server by sharing the port and password privately.

### 4.1 Decisions (changed from the first draft of this brief)

- **Model weights:** the cluster's shared copies at `/common/public/llm-models/meta-models/LLAMA3.1/Meta-Llama-3.1-8B-Instruct` and `/common/public/llm-models/openai/gpt-oss-20b` (installed by the cluster admins with their original licenses). No Hugging Face access request or download is needed. vLLM serves them under their official names `meta-llama/Llama-3.1-8B-Instruct` and `openai/gpt-oss-20b`, which `configs/models.yaml` and every results file use.
- **Student limits:** 1 GPU, 4 CPUs and 32 GB RAM per job, at most 2 running jobs, 1 day per job. The biggest GPU a job can get is 48 GB (A40 or L40S); the Blackwell node `block` hands out shared ~24 GB slices.
- **Python:** `~/venvs/rag`, Python 3.11 built with `uv` (no `module load`). vLLM plus our `requirements.txt` (no `torch` pin) are installed with `scripts/install_vllm.sbatch`.
- **Everything GPU runs through `sbatch`** (no interactive `srun` sessions): `scripts/serve_llama.sbatch` and `scripts/serve_gptoss.sbatch` for interactive servers (own ports, 4 h default), `scripts/run_eval.sbatch` for full runs of either model. Every job uses `--qos=studentqos --partition=student --gres=gpu:a40:1`; a GPU type is required because a bare `gpu:1` can land on a GTX 1080 Ti.
- **`VLLM_USE_FLASHINFER_SAMPLER=0`** in every job: otherwise vLLM 0.31 tries to compile a FlashInfer kernel at startup, and compute nodes have no `nvcc`. For the same reason gpt-oss-20b is served with `--attention-backend TRITON_ATTN`.
- **Secrets:** `~/insurance-rag/.env` on the cluster (plain `KEY=value` lines, `chmod 600`) holds `VLLM_API_KEY`, `VLLM_PORT` and `VLLM_GPTOSS_PORT`; the laptop `.env` holds the same values. vLLM reads `VLLM_API_KEY` from the environment, so the password never appears on the command line.
- **Caches:** `HF_HOME` and the uv cache live in `~/scratchDirectory`; code, venv, index (`data/index/`) and `results/` stay in the repo paths the code expects.
- **Laptop access:** SSH key plus a `Host origami` entry in `~/.ssh/config`, then a tunnel `ssh -N -L <port>:<node>:<port> origami` opened by the human.

### 4.2 Daily routine

1. On campus Wi-Fi or VPN. Submit `scripts/serve_llama.sbatch` (or `scripts/serve_gptoss.sbatch`) and wait for "Application startup complete" in `logs/serve-<jobid>.out` (first line shows the node).
2. Open the tunnel in its own window and work.
3. When finished: close the tunnel and `scancel` the server job to release the GPU.

Never run heavy work on the login node `origami`. Always set `--time`.

### 4.3 Full runs: batch job (no laptop needed)

Code reaches the cluster via GitHub: `git pull` in `~/insurance-rag` before each run. `scripts/run_eval.sbatch` starts a private vLLM server for one model (`MODEL=vllm_llama8b` or `MODEL=vllm_gptoss20b`) on the batch port, rebuilds the index with `python -m src.ingest` (so it always matches the checked-out code), runs `python -m src.eval.run --model $MODEL --split ${SPLIT:-test}`, then stops the server. Submit from `~/insurance-rag` with `MODEL=vllm_llama8b sbatch scripts/run_eval.sbatch`. Member B's dev runs: `MODEL=vllm_gptoss20b BATCH_PORT=8482 SPLIT=dev APPROACHES=A4 sbatch scripts/run_eval.sbatch` (sbatch passes your shell variables to the job; this form also allows commas, e.g. `APPROACHES=B0,A0`). Check with `squeue --me`, cancel with `scancel <jobid>`. `src/eval/run.py` must be resumable so a cut-off job can be resubmitted. Either member can submit batch jobs for development; the **final** test runs are submitted by Member A only, from `main`, so all reported numbers come from one consistent run. The Haiku judge needs no GPU and runs from a laptop.

### 4.4 configs/models.yaml

```yaml
local_ollama:
  provider: openai
  base_url: http://localhost:11434/v1
  model: qwen3.5:4b
  api_key: ollama
vllm_llama8b:
  provider: openai
  base_url: http://localhost:${VLLM_PORT}/v1   # your own port; laptop via tunnel, or inside a batch job
  model: meta-llama/Llama-3.1-8B-Instruct
  api_key: ${VLLM_API_KEY}
vllm_gptoss20b:
  provider: openai
  base_url: http://localhost:${VLLM_GPTOSS_PORT}/v1   # your own gpt-oss port; laptop via tunnel, or inside a batch job
  model: openai/gpt-oss-20b
  api_key: ${VLLM_API_KEY}
claude_haiku_judge:
  provider: anthropic
  model: claude-haiku-5-5
  api_key: ${ANTHROPIC_API_KEY}
```

## 5. Repository layout

```text
insurance-rag/
  README.md                 setup (laptop + cluster), data download, how to run every experiment
  PROJECT_BRIEF.md          this file
  CLAUDE.md                 "read PROJECT_BRIEF.md first"
  CLUSTER_SETUP.md          tested cluster setup and daily routine (section 4)
  requirements.txt
  .env.example
  configs/
    models.yaml             named model endpoints (section 4.4)
    approaches.yaml         per-approach settings (top_k, max_rewrites, ...)
    run.yaml                seeds, which approaches x models to run, dataset split
  data/
    policies/               policy PDFs + SNAPSHOT.md (download date, URLs)
    scenarios/
      LABELLING_GUIDE.md    rules for the four verdicts, written before labelling
      drafts.jsonl          LLM-drafted scenarios with intended answers (not gold)
      reviewed.jsonl        Member B's accepted/fixed labels for every kept draft
      blind_A.jsonl         Member A's blind labels for 40 test scenarios
      dev.jsonl             20 agreed scenarios for tuning
      test.jsonl            about 120 agreed scenarios, scored once at the end
  scripts/
    install_vllm.sbatch     one-time install of vLLM + requirements into ~/venvs/rag
    serve_llama.sbatch      interactive Llama 3.1 8B server on your own port
    serve_gptoss.sbatch     interactive gpt-oss-20b server on your own port
    run_eval.sbatch         full runs of one model as one batch job (section 4.3)
  src/
    schema.py               CONTRACT: Scenario, Chunk, VerdictOutput
    llm.py                  CONTRACT: get_llm(name) from models.yaml
    store.py                CONTRACT: search(query, policy, k) -> list[Chunk]; get_section(section_id)
    ingest.py               PDF -> sections with IDs -> chunks -> embeddings -> Chroma
    tools.py                get_definition, get_exclusions (built on store.py)
    approaches/
      __init__.py           CONTRACT: REGISTRY = {"B0": run, ...}; each run(scenario, llm, store) -> VerdictOutput
      b0_base.py
      a0_simple.py
      a2_crag.py
      a4_workflow.py
      a1_enhanced.py        optional
      a3_react.py           optional
    eval/
      run.py                run approaches x models over a split, save raw outputs (resumable)
      score.py              metrics, bootstrap CIs, McNemar tests
      agreement.py          Cohen's kappa between reviewed.jsonl and blind_A.jsonl
      judge.py              LLM faithfulness judge
      report.py             leaderboard table + charts
    scenarios/
      draft.py              LLM-draft scenarios from specific policy clauses
  app/
    label_app.py            small Streamlit labelling page (accept / change / delete)
    streamlit_app.py        demo on the winning approach
  logs/                     SLURM and vLLM logs (git-ignored)
  results/                  raw outputs, scores, charts (one folder per run)
  tests/                    small pytest checks for ingest, store, tools, scoring
```

Files marked CONTRACT are written first by Member A (day 1) and changed only with agreement from both members.

## 6. Data

### Policy documents (real, public)

Start with **FWD and MSIG**. Add Singlife only if M1 lands early. Download, save under `data/policies/`, and record URL + download date in `SNAPSHOT.md`.

| Policy | URL |
| --- | --- |
| FWD Travel Insurance (about 43 pages; definitions at the back, general exclusions pp. 29 to 31) | https://www.fwd.com.sg/wp-content/uploads/2024/04/FWD-Travel-Insurance-Policy-Wording.pdf |
| MSIG TravelEasy (about 70 pages; 52 benefit sections; cross-references general exclusions by number) | https://www.msig.com.sg/sites/msig_sg/files/downloads/traveleasy_policy.pdf |
| Singlife Travel (optional; about 53 pages) | https://singlife.com/content/dam/public/sg/documents/lifestyle-insurance/singlife-travel-insurance/policy-documents/travel-policy-document.pdf |

### Ingestion rules

- Split by the policy's own headings into **sections**, each with a stable ID: `{policy}:{section_number_or_slug}` (e.g. `fwd:travel_delay`, `msig:general_exclusion_13`, `fwd:definitions:scheduled_public_transport`).
- Tag each section with `policy`, `section_id`, `title`, `type` (benefit / definition / exclusion / condition / other), `page`.
- Chunk long sections (about 300 to 500 words, small overlap) but keep `section_id` on every chunk.
- Defined terms: build a lookup `{policy: {term_lowercase: section_id}}` so `get_definition` works without search.
- After ingesting, print 10 random sections per policy so a human can check the parsing before anything else is built.

### Scenario format (`data/scenarios/*.jsonl`, one JSON object per line)

```json
{
  "id": "fwd-007",
  "policy": "fwd",
  "scenario": "My flight from Singapore to Tokyo was delayed 7 hours because of a typhoon. Can I claim?",
  "category": "needs_definition",
  "source_clause": "fwd:travel_delay",
  "gold_verdict": "covered",
  "gold_sections": ["fwd:travel_delay", "fwd:definitions:scheduled_public_transport"],
  "notes": "Delay over 6 hours caused by adverse weather.",
  "status": "accepted"
}
```

- `category`: `single_section`, `needs_definition`, `needs_exclusion`, or `tricky` (false assumptions, missing details).
- Target mix: about 40% single_section, 40% needs_definition or needs_exclusion, 20% tricky. Roughly half FWD, half MSIG.
- Draft about 150 to end with about 140 kept (20 dev + about 120 test).

### Labelling workflow: AI drafts, humans decide

AI never sets the final gold label, because the drafts come from an LLM and grading the tested models against an LLM's own answers would bias the results.

1. **Labelling guide (Member B, AI-assisted):** one page in `LABELLING_GUIDE.md` defining the four verdicts with an example each. partially_covered means some costs are covered and some are excluded, or a sub-limit applies. insufficient_info means a fact needed to decide is missing. Also covers how to pick `gold_sections`.
2. **Draft by construction (`src/scenarios/draft.py`, Member B):** pick a clause, then write scenarios designed to land on different verdicts. Illustrative example from FWD Travel delay, which pays for delays of 6 continuous hours or more: 7 hours = covered; 4 hours = not covered; a cause listed in the exclusions = not covered; "my flight was delayed" = insufficient_info. Every intended answer must be confirmed against the actual policy text during review. Each draft stores `source_clause` and an intended answer. Drafting can be done by Claude Code directly at no API cost.
3. **Review (Member B, about 1 to 2 minutes each):** in `app/label_app.py`, read the scenario and the clause text, then accept, change the verdict or sections, or delete. Output: `reviewed.jsonl`.
4. **Split:** randomly assign 20 to dev and the rest to test (fixed seed).
5. **Blind check (Member A, about 2 hours):** label 40 random test scenarios without seeing the drafts or B's labels. Output: `blind_A.jsonl`. `src/eval/agreement.py` reports Cohen's kappa (4-way and binary covered vs not).
6. **Resolve disagreements together (about 30 minutes)**, update the guide if a rule was unclear, log the decision in `notes`.
7. **Freeze `test.jsonl` by 29 Oct.** No edits and no prompt tuning on it after that.

Report wording: "Scenarios were drafted by an LLM from specific policy clauses and verified by a human; a second member labelled a 40-scenario subset blind (Cohen's kappa = X)."

## 7. Output schema (every setup must return this)

```python
class VerdictOutput(BaseModel):
    verdict: Literal["covered", "not_covered", "partially_covered", "insufficient_info"]
    cited_sections: list[str]      # section_ids
    explanation: str               # plain English, quotes the deciding clause text
    steps: list[dict] = []         # trace: each retrieval / tool call / grade, for the demo and error analysis
    usage: dict = {}               # model_calls, prompt_tokens, completion_tokens, latency_s
```

Use structured output (pydantic / JSON mode). If parsing fails, retry once, then record a `parse_error` (counts as wrong).

## 8. The setups

Same model, embeddings, chunks and base prompt for all. Only the retrieval and reasoning strategy differs.

### Core (must be done by M2)

| ID | Name | Owner | Behaviour |
| --- | --- | --- | --- |
| B0 | Base LLM, no retrieval | A | Same prompt, no policy text. The floor. |
| A0 | Simple RAG | A | One search with the scenario text, top_k=5 chunks from that policy, answer. |
| A2 | Corrective RAG (CRAG-style) | A | Search top_k=5; LLM grades each chunk relevant / irrelevant; if fewer than 2 relevant, rewrite the query and search again (max 2 rewrites); answer from relevant chunks only. Adapted from Yan et al. 2024: no web search (closed corpus), LLM grader instead of the fine-tuned T5 evaluator. Start from the LangGraph CRAG notebook (section 14). |
| A4 | Claims-workflow agent | B | Fixed LangGraph graph: (1) identify relevant benefit section(s); (2) extract defined terms used in them and fetch definitions; (3) fetch general exclusions plus section-specific exclusions and conditions; (4) decide verdict and cite. Each node logs to `steps`. Our domain-specific contribution. |

A2 and A4 are two different agentic styles: a generic self-correcting retriever vs a domain workflow that follows how a claims assessor reads a policy.

### Optional (only if M2 is met on time)

| ID | Name | Behaviour |
| --- | --- | --- |
| A1 | Enhanced single-pass | One search, top_k=15, always append Definitions and General Exclusions. Control for "is it just more context?". About 10 lines on top of A0. |
| A3 | ReAct tool agent | LangGraph prebuilt ReAct agent with `search_policy`, `get_definition`, `get_exclusions`. Max 8 tool calls. Risky: Llama 8B tool calling can be unreliable. |

## 9. Evaluation

`src/eval/run.py` (flags: `--model`, `--split dev|test`, optional `--approaches B0,A0,...`) runs `approaches x models x split` and saves one JSONL row per (scenario, approach, model) with the full `VerdictOutput`, the config and the commit hash. It must be resumable (skip rows already done).

`src/eval/score.py` computes, per approach x model, overall and per `category`:

| Metric | Definition |
| --- | --- |
| verdict_accuracy | verdict == gold_verdict (main metric) |
| binary_accuracy | covered/partially_covered vs not_covered/insufficient_info matches gold (secondary) |
| wrong_covered_rate | predicted covered (or partially) when gold is not_covered (safety) |
| clause_recall | share of gold_sections present in cited_sections |
| faithfulness | LLM judge: explanation supported by cited text (yes / partly / no) |
| latency_s, model_calls, tokens | means from `usage` (incl. reasoning tokens). Both models run free on the cluster, so cost is measured as tokens, calls and latency rather than dollars |

- 95% confidence intervals by bootstrap (1,000 resamples, fixed seed).
- **Paired significance tests (McNemar on per-scenario correctness), pre-registered:** (1) best agent vs A0, (2) A0 vs B0, (3) A2 vs A4. If A1 is run, add best agent vs A1. Holm correction across them.
- `src/eval/judge.py`: Claude Haiku 5.5 judge. Export 30 random judgments to CSV for a human to check agreement.
- `src/eval/report.py`: leaderboard table (markdown + CSV), accuracy vs latency and tokens scatter (one point per approach x model), accuracy by category bar chart, error-type counts.
- **Trace evaluation** (added 23 Oct after the prof's feedback: evaluate the agent's tool calls, not only its verdicts). `src/eval/traces.py` scores each approach's `steps` against `gold_sections`: per-step recall and precision (e.g. A4's exclusions step vs gold exclusions), evidence recall (did the needed sections reach the model), wrong answers split into missing_evidence (retrieval failure) vs had_evidence (reasoning failure), and efficiency (calls, tokens, latency, context size, share of context not needed, parse retries). A step that decides the answer's context lists its section IDs under `context`. Each member also hand-checks 10 agentic traces (A2, A4) from the test runs with the error types below.
- Error types (assigned by a human with a draft LLM label): missed_exclusion, misread_definition, wrong_section_retrieved, agent_loop_or_stall, accepted_false_assumption, parse_error, other.

**Decision rule for "best" (fixed before looking at test results):** highest verdict_accuracy on test, provided its wrong_covered_rate is no worse than A0's. If McNemar does not separate the top two, pick the cheaper and faster one.

**Data discipline:** tune prompts only on `dev.jsonl` (20), on Llama 3.1 8B. Score `test.jsonl` once, at the end, with frozen configs.

## 10. Demo app (build half)

`app/streamlit_app.py`:

- Pick a policy, type a claim scenario.
- Show the winning approach's verdict, the quoted clauses with section IDs, and an expandable trace of `steps`.
- Optional toggle to show A0's answer side by side.
- Guardrails: never promise a payout amount or approval ("likely covered under Section X, subject to the insurer's assessment"); always show the clause text; return insufficient_info and say what detail is missing when evidence is not found; fixed disclaimer that this is not insurance or legal advice.
- Runs on the cluster models, with cached responses for the scripted demo questions so it works offline.

## 11. Team split and integration

Member A = YZ. Member B = teammate. The split is even at about 34 hours each (estimates assume Claude Code); report and presentation are shared equally on top.

| Member A (YZ) | Hours | Member B | Hours |
| --- | --- | --- | --- |
| Cluster setup first, README notes for B | 4 | Labelling guide | 2 |
| Repo setup and contracts (day 1) | 2 | `draft.py` and `label_app.py` | 4 |
| `ingest.py`, `store.py` (FWD + MSIG) | 7 | Review about 150 drafts | 4 |
| B0 and A0 | 3 | `tools.py` | 3 |
| A2 CRAG | 5 | A4 workflow agent | 7 |
| `run.py`, `score.py` (CIs, McNemar), `agreement.py` | 6 | `judge.py` and 30 hand-checks | 3 |
| `report.py` charts and leaderboard | 2 | Error analysis | 4 |
| Final runs (batch jobs, both models) | 3 | Streamlit demo | 7 |
| Blind-label 40 test scenarios | 2 | | |
| **Total** | **34** | **Total** | **34** |

Report sections: A writes method, setups and results; B writes data and labelling, the A4 agent, error analysis and the demo; both write the intro and discussion, and do one joint pass for flow. Presentation (no slides): A explains the comparison and results, B explains the agent and runs the live demo.

**Critical-path rule:** if FWD ingest and `store.search` are not working by Tue 20 Oct, Member B pauses drafting and pairs with A for a day.

### How the work combines

- **Contracts first.** On day 1, Member A writes and merges the CONTRACT files (section 5) with stub implementations. Both members then build against them.
- **Plug-in methods.** Each approach is one file registered in `approaches/__init__.py`. Once merged, `run.py` picks it up automatically. No separate integration week.
- **Git workflow.** One branch per task, pull request, merge to `main` the same or next day. `git pull` before every session. Each member mostly edits their own files. Never commit `.env`, `logs/` or the Chroma folder.
- **Check-ins.** Two 15-minute check-ins a week (e.g. Mon and Thu): what's merged, what's blocked, is the milestone on track.
- **Final runs.** Member A runs all final experiments from `main` with frozen configs and commits `results/`, so every number comes from one consistent run.

### Timeline

| By | Member A (YZ) | Member B | Milestone |
| --- | --- | --- | --- |
| Sun 18 Oct | Repo, contracts, own cluster server working | Labelling guide, HF request, laptop setup | |
| Tue 20 Oct | FWD ingested, `store.search` working | Own cluster server working (following A's README notes) | Critical-path check |
| Thu 22 Oct | FWD + MSIG ingested and checked; B0, A0 run on dev | About 150 drafts; `label_app.py`; review started | **M1** |
| Mon 26 Oct | | Review done; dev/test split made, so A can start blind labelling | |
| Thu 29 Oct | A2 CRAG; `run.py`, `score.py`; blind 40 done; kappa | A4 agent; `tools.py`; `judge.py`; disagreements resolved; test frozen | **M2**: all 4 core setups valid on dev on Llama |
| Mon 2 Nov | Full test runs on both models | Error analysis started | |
| Wed 4 Nov | Leaderboard, McNemar, charts; winner picked | All judge runs done (Haiku, about US$1); judge hand-checks; demo on winner | **M3** |
| Mon 9 Nov | Report sections, README | Report sections, demo polished with cached answers | **M4**: ship, rehearse |

**Suggested first prompt (Member A):** "I am Member A. Read PROJECT_BRIEF.md, then set up the repo skeleton (section 5), requirements.txt, configs/models.yaml and the CONTRACT files with stubs. Then write src/ingest.py for FWD only and stop after printing 10 sample sections with their IDs so I can check the parsing."

**Suggested first prompt (Member B):** "I am Member B. Read PROJECT_BRIEF.md, then draft data/scenarios/LABELLING_GUIDE.md and stop for my review. After that, build src/scenarios/draft.py following section 6."

## 12. Safety rules for the agent (Claude Code)

- Run heavy work only inside a SLURM job, never on `origami`.
- Do not delete anything outside the repo and `~/venvs/rag` without asking.
- Never print, log or commit tokens, passwords or API keys.
- Do not change CONTRACT files without telling the human that the other member must agree.
- Cluster commands from the laptop: use one-off, non-interactive SSH, e.g. `ssh -o BatchMode=yes <smu-id>@10.193.104.102 "squeue --me"`. Never wait on a password prompt.
- Do not start blocking commands yourself: the SSH tunnel (`ssh -N -L ...`) is opened by the human in their own window, and there are no `srun --pty` sessions or foreground `vllm serve`. GPU work (including the model server) goes through the `sbatch` scripts in `scripts/`. Cancel a server job you started once the human is done with it.
- Before any run that calls Claude, print the estimated token cost and wait for the human to confirm.

## 13. Things to ask the human about (do not guess)

- Any Claude spend beyond the US$5 judge budget, or changing the tested models or the judge.
- Any change to the gold labels, the decision rule, or the dev/test split.
- Adding Singlife, A1, A3 or any other extension before M2 is done.
- Anything that would send policy text or scenarios to a new third-party service.

## 14. References

- CRAG: Yan et al., 2024, https://arxiv.org/abs/2401.15884
- ReAct: Yao et al., 2022, https://arxiv.org/abs/2210.03629
- LangGraph CRAG notebook (starting point for A2): https://github.com/langchain-ai/langgraph/blob/main/examples/rag/langgraph_crag.ipynb
- LangChain blog, "Self-Reflective RAG with LangGraph" (background on CRAG and Self-RAG in LangGraph): https://www.langchain.com/blog/agentic-rag-with-langgraph
- Claude model IDs: https://platform.claude.com/docs/en/about-claude/models/overview ; pricing: https://platform.claude.com/docs/en/about-claude/pricing
- gpt-oss-20b model card: https://huggingface.co/openai/gpt-oss-20b ; Llama 3.1 license: https://www.llama.com/llama3_1/license/
- McNemar's test for paired classifier comparison: Dietterich, 1998, "Approximate Statistical Tests for Comparing Supervised Classification Learning Algorithms"
