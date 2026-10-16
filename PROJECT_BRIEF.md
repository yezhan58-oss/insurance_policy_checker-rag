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
  - Laptops: Windows, Python 3.11 or 3.12, **Windows CMD** for local commands (YZ). No NVIDIA GPU.
  - SMU SCIS GPU cluster "origami" (login node `10.193.104.102`, each member uses their own SMU ID): Linux, **bash**, SLURM. Reachable on campus Wi-Fi or the SMU VPN.
- **Models**
  - Open model: `meta-llama/Llama-3.1-8B-Instruct`, served with vLLM on the cluster (node `avenue`, NVIDIA A40 48 GB, `student` partition). Each member runs their own server on their own port (section 4).
  - Backup open model if Llama access is delayed: `Qwen/Qwen2.5-7B-Instruct` (not gated). If used, change `model:` in models.yaml and serve it with `--tool-call-parser hermes` instead of `llama3_json`.
  - Frontier model: **Claude Sonnet 5.5** via the Anthropic API ($2 in / $10 out per million tokens). Budget: **US$100 of credits that expire on 5 Nov 2026**. All Sonnet runs must finish by 2 Nov, and all judge runs by 4 Nov. Do prompt tuning on Llama (free); spend Claude credits only on the final dev check, the test runs and judge scoring. Log token usage per run and stop to ask the human if projected spend exceeds US$70. Use prompt caching for repeated instructions. Make normal (synchronous) calls only, so latency is measured the same way for every setup.
  - LLM judge: Claude Haiku 5.5 (cheap). It scores both the Llama and the Claude test runs, so it must finish before the credits expire. Note in the report that the judge is from the same family as the frontier model.
  - The demo must not depend on Claude after 5 Nov: run it on Llama, or cache the scripted demo answers.
  - Local Ollama `qwen3.5:4b` is only for quick "does the code run" checks. **Tune prompts on Llama 3.1 8B, not on the 4B model.**
- **One client interface for every model.** `src/llm.py` reads `configs/models.yaml` and builds `langchain_openai.ChatOpenAI` (with `base_url`) for vLLM and Ollama, or `langchain_anthropic.ChatAnthropic` for Claude, based on a `provider` field. Approach code never changes when the model changes.
- **Embeddings:** one embedding model everywhere so every setup searches the same index. Default: `BAAI/bge-small-en-v1.5` via `sentence-transformers` Always load it with `device="cpu"` (on the cluster the GPU is busy with vLLM, and CPU keeps results identical across machines). `src/ingest.py` is deterministic, so each machine rebuilds the same Chroma index with `python -m src.ingest`.
- Libraries: `langchain`, `langchain-openai`, `langchain-anthropic`, `langchain-chroma`, `chromadb`, `langgraph`, `sentence-transformers`, `pymupdf`, `pydantic`, `pandas`, `scipy`, `statsmodels`, `matplotlib`, `streamlit`, `pyyaml`, `python-dotenv`, `pytest`. vLLM is installed only on the cluster.
- Laptop: a `venv` inside the repo and a pinned `requirements.txt`. Cluster: a separate venv at `~/venvs/rag` (Python 3.11, built with `uv`).
- Secrets go in `.env` on each machine, never committed: `ANTHROPIC_API_KEY`, `VLLM_API_KEY`, `VLLM_PORT`, `HF_TOKEN`. `src/llm.py` expands `${VAR}` in models.yaml from `.env`. Commit `.env.example` with empty values.
- Fixed seeds, temperature 0 for all experiment runs. Every run writes its config and git commit hash next to its results.
- Small, reviewable steps. After each task, stop and summarise what was built, how to run it, and how it was verified.

## 3. Team setup (one time, this weekend)

### 3.1 Member A (YZ) does once

1. Create a private GitHub repo `insurance-rag`, invite Member B. Commit this file plus a `CLAUDE.md` with these lines (the `@` line makes Claude Code load the brief automatically at the start of every session):

   ```
   @PROJECT_BRIEF.md

   The human will say "I am Member A" or "I am Member B" at the start of a session. Work only on that member's tasks (section 11) unless told otherwise.
   ```
2. Claude Console (where the credits are): invite Member B to the organisation. Each member creates their own API key. If the Console allows a workspace spend limit, set it to about US$70.
3. Do the cluster setup (section 4) first and note any fixes in the README, so Member B's setup goes quickly.

### 3.2 Both members do on their own laptop

1. Clone the repo, create the venv, `pip install -r requirements.txt`.
2. Install the SMU VPN.
3. Request Llama 3.1 8B access on Hugging Face with your own account. Each member needs their own approval and token, because weights download into each person's own cluster home folder.
4. Do the cluster setup in section 4 with your own SMU ID (about 1 hour, mostly waiting for installs).
5. Create `.env` with your own `ANTHROPIC_API_KEY`, your own made-up `VLLM_API_KEY`, and your `VLLM_PORT` (A: 8471, B: 8472).
6. **Claude Code must run on your normal Claude subscription, not the API key.** Keep `ANTHROPIC_API_KEY` only in the repo's `.env` (read by our Python code). Never set it as a Windows environment variable: the Claude Code command-line tool uses that variable instead of your subscription, and every coding chat would then spend the US$100 of credits. The Claude desktop app signs in with your account and does not read it.

If a member uses macOS or Linux instead of Windows, use the Terminal equivalents of the CMD commands (e.g. `cat ~/.ssh/id_ed25519.pub | ssh ...` instead of `type ... | ssh ...`).

## 4. Cluster setup (each member, one time)

Both members have their own cluster account, and each runs their own copy of the setup and their own model server. This way neither depends on the other being online, and a server dying when one person's session times out does not stop the other.

| | Member A (YZ) | Member B |
| --- | --- | --- |
| SMU ID | `yz.wong.2024` | own ID |
| `VLLM_PORT` (interactive) | 8471 | 8472 |
| Batch job port | 8481 | 8482 |
| `VLLM_API_KEY` | own made-up password | own made-up password |

Different ports matter because both of you may land on the same node (avenue has 4 A40s). Replace `<smu-id>` and `<port>` below with your own values.

Etiquette: hold a GPU only while actively working; avenue's GPUs are shared with other undergrads. If one of you is offline for a long time, the other can still lend their server by sharing the port and password privately.

### 4.1 Laptop: SSH key (Windows CMD, both members)

```
ssh-keygen -t ed25519
type %USERPROFILE%\.ssh\id_ed25519.pub | ssh <smu-id>@10.193.104.102 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
ssh <smu-id>@10.193.104.102
```

The last command should log in without a password.

### 4.2 Cluster: get a GPU session inside tmux (bash)

```bash
tmux new -s work
srun -p student --gres=gpu:1 --nodelist=avenue --time=02:00:00 --pty bash
nvidia-smi
```

`nvidia-smi` should show one NVIDIA A40. If avenue is busy, drop `--nodelist=avenue` (any GPU with at least 24 GB works) and use that node's name in the tunnel. Detach from tmux with Ctrl+B then D; reattach with `tmux attach -t work`.

### 4.3 Cluster: Python 3.11 environment with uv (inside the GPU session)

The system Python is 3.9, too old for vLLM. uv installs its own Python into the home folder.

```bash
rm -rf ~/venvs/rag
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
uv venv --python 3.11 ~/venvs/rag
source ~/venvs/rag/bin/activate
python --version
uv pip install vllm
python -c "import vllm; print(vllm.__version__)"
```

`python --version` must print 3.11.x. vLLM pulls in `huggingface_hub`, which provides the `hf` command used in 4.4. If the install is cut off by the time limit, start a new session, activate the venv and rerun the install line.

### 4.4 Cluster: Hugging Face login

After Llama access is approved, create a **Read** token on Hugging Face (Settings, Access Tokens) and run:

```bash
source ~/venvs/rag/bin/activate
hf auth login
```

(Older versions: `huggingface-cli login`.) Weights download to `~/.cache/huggingface` (about 16 GB; home quota is 120 GB).

### 4.5 Cluster: start your model server (inside a GPU session)

```bash
source ~/venvs/rag/bin/activate
export VLLM_API_KEY=<your password>
vllm serve meta-llama/Llama-3.1-8B-Instruct --host 0.0.0.0 --port <port> --api-key $VLLM_API_KEY --max-model-len 16384 --seed 0 --enable-auto-tool-choice --tool-call-parser llama3_json
```

`--api-key` stops other cluster users from using your server. The tool flags are only needed for the optional ReAct agent but are harmless. Wait for "Application startup complete". Note which node you got (shown in the prompt or via `hostname`), since the tunnel needs it.

### 4.6 Laptop: tunnel (Windows CMD, keep the window open)

```
ssh -N -L <port>:avenue:<port> <smu-id>@10.193.104.102
```

Replace `avenue` if your GPU session landed on another node. Test from another CMD window:

```
curl http://localhost:<port>/v1/models -H "Authorization: Bearer <your password>"
```

### 4.7 Daily routine

1. On campus Wi-Fi or VPN: `ssh` in, `tmux attach -t work` (or `tmux new -s work`).
2. `srun ... --pty bash`, activate the venv, start `vllm serve` (4.5).
3. Open the tunnel (4.6) and work.
4. When finished: Ctrl+C vLLM, `exit` the GPU session to release it.

Never run heavy work on the login node `origami`. Always set `--time`.

### 4.8 Full Llama runs: batch job (no laptop needed)

Code reaches the cluster via GitHub. One-time setup on the cluster (in a GPU session, venv active): `git clone` the repo into `~/insurance-rag`, `cd ~/insurance-rag`, `mkdir -p logs` (git ignores `logs/`, and SLURM cannot create it), `uv pip install -r requirements.txt` (requirements.txt must not pin `torch`, so vLLM's version is kept), then `python -m src.ingest` to build the cluster's index. Before each run: `git pull`. Put a cluster `.env` in `~/insurance-rag/.env` with plain `KEY=value` lines (no spaces around `=`), since bash reads it. It needs `VLLM_API_KEY` and `VLLM_PORT`; no Claude key is needed on the cluster. Save as `scripts/run_llama.sbatch`:

```bash
#!/bin/bash
#SBATCH -p student
#SBATCH --gres=gpu:1
#SBATCH --nodelist=avenue
#SBATCH --time=08:00:00
#SBATCH --output=logs/%j.out

source ~/venvs/rag/bin/activate
cd ~/insurance-rag
set -a; source .env; set +a
export VLLM_PORT=${BATCH_PORT:-8481}     # batch port, so it never clashes with your interactive server
vllm serve meta-llama/Llama-3.1-8B-Instruct --host 127.0.0.1 --port $VLLM_PORT --api-key $VLLM_API_KEY --max-model-len 16384 --seed 0 --enable-auto-tool-choice --tool-call-parser llama3_json > logs/vllm_$SLURM_JOB_ID.log 2>&1 &
VLLM_PID=$!
until curl -sf -H "Authorization: Bearer $VLLM_API_KEY" http://127.0.0.1:$VLLM_PORT/v1/models > /dev/null; do kill -0 $VLLM_PID 2>/dev/null || exit 1; sleep 10; done
python -m src.eval.run --model vllm_llama8b --split ${SPLIT:-test} ${APPROACHES:+--approaches $APPROACHES}
```

Submit from `~/insurance-rag` with `sbatch scripts/run_llama.sbatch`. Member B's dev runs: `BATCH_PORT=8482 SPLIT=dev APPROACHES=A4 sbatch scripts/run_llama.sbatch` (sbatch passes your shell variables to the job; this form also allows commas, e.g. `APPROACHES=B0,A0`). Check with `squeue --me`, cancel with `scancel <jobid>`. `src/eval/run.py` must be resumable so a cut-off job can be resubmitted. Either member can submit batch jobs for development; the **final** test runs are submitted by Member A only, from `main`, so all reported numbers come from one consistent run. Claude runs need no GPU and are run from a laptop.

### 4.9 configs/models.yaml

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
claude_sonnet:
  provider: anthropic
  model: claude-sonnet-5-5
  api_key: ${ANTHROPIC_API_KEY}
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
  requirements.txt
  .env.example
  configs/
    models.yaml             named model endpoints (section 4.9)
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
    run_llama.sbatch        batch job (section 4.8)
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

AI never sets the final gold label, because the study tests Claude and grading Claude against Claude's own answers would bias the results.

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
| latency_s, model_calls, tokens, cost | means from `usage` |

- 95% confidence intervals by bootstrap (1,000 resamples, fixed seed).
- **Paired significance tests (McNemar on per-scenario correctness), pre-registered:** (1) best agent vs A0, (2) A0 vs B0, (3) A2 vs A4. If A1 is run, add best agent vs A1. Holm correction across them.
- `src/eval/judge.py`: Claude Haiku 5.5 judge. Export 30 random judgments to CSV for a human to check agreement.
- `src/eval/report.py`: leaderboard table (markdown + CSV), accuracy vs cost scatter (one point per approach x model), accuracy by category bar chart, error-type counts.
- Error types (assigned by a human with a draft LLM label): missed_exclusion, misread_definition, wrong_section_retrieved, agent_loop_or_stall, accepted_false_assumption, parse_error, other.

**Decision rule for "best" (fixed before looking at test results):** highest verdict_accuracy on test, provided its wrong_covered_rate is no worse than A0's. If McNemar does not separate the top two, pick the cheaper and faster one.

**Data discipline:** tune prompts only on `dev.jsonl` (20), on Llama 3.1 8B. Score `test.jsonl` once, at the end, with frozen configs.

## 10. Demo app (build half)

`app/streamlit_app.py`:

- Pick a policy, type a claim scenario.
- Show the winning approach's verdict, the quoted clauses with section IDs, and an expandable trace of `steps`.
- Optional toggle to show A0's answer side by side.
- Guardrails: never promise a payout amount or approval ("likely covered under Section X, subject to the insurer's assessment"); always show the clause text; return insufficient_info and say what detail is missing when evidence is not found; fixed disclaimer that this is not insurance or legal advice.
- Runs on Llama, with cached responses for the scripted demo questions so it works offline and after the Claude credits expire.

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
| Final runs (Llama batch job + Claude) | 3 | Streamlit demo | 7 |
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
| Mon 2 Nov | Full Llama test run; all Sonnet runs done | Error analysis started | Sonnet deadline |
| Wed 4 Nov | Leaderboard, McNemar, charts; winner picked | All judge runs done (credits expire 5 Nov); judge hand-checks; demo on winner | **M3** |
| Mon 9 Nov | Report sections, README | Report sections, demo polished with cached answers | **M4**: ship, rehearse |

**Suggested first prompt (Member A):** "I am Member A. Read PROJECT_BRIEF.md, then set up the repo skeleton (section 5), requirements.txt, configs/models.yaml and the CONTRACT files with stubs. Then write src/ingest.py for FWD only and stop after printing 10 sample sections with their IDs so I can check the parsing."

**Suggested first prompt (Member B):** "I am Member B. Read PROJECT_BRIEF.md, then draft data/scenarios/LABELLING_GUIDE.md and stop for my review. After that, build src/scenarios/draft.py following section 6."

## 12. Safety rules for the agent (Claude Code)

- Run heavy work only inside a SLURM job, never on `origami`.
- Do not delete anything outside the repo and `~/venvs/rag` without asking.
- Never print, log or commit tokens, passwords or API keys.
- Do not change CONTRACT files without telling the human that the other member must agree.
- Cluster commands from the laptop: use one-off, non-interactive SSH, e.g. `ssh -o BatchMode=yes <smu-id>@10.193.104.102 "squeue --me"`. Never wait on a password prompt.
- Do not start blocking commands yourself: the SSH tunnel (`ssh -N -L ...`), `srun --pty` sessions and `vllm serve` are run by the human in their own windows. For GPU work you start, use `sbatch`.
- Before any run that calls Claude, print the estimated token cost and wait for the human to confirm.

## 13. Things to ask the human about (do not guess)

- Any Claude spend beyond the US$70 working budget, or switching the frontier model.
- Any change to the gold labels, the decision rule, or the dev/test split.
- Adding Singlife, A1, A3 or any other extension before M2 is done.
- Anything that would send policy text or scenarios to a new third-party service.

## 14. References

- CRAG: Yan et al., 2024, https://arxiv.org/abs/2401.15884
- ReAct: Yao et al., 2022, https://arxiv.org/abs/2210.03629
- LangGraph CRAG notebook (starting point for A2): https://github.com/langchain-ai/langgraph/blob/main/examples/rag/langgraph_crag.ipynb
- LangChain blog, "Self-Reflective RAG with LangGraph" (background on CRAG and Self-RAG in LangGraph): https://www.langchain.com/blog/agentic-rag-with-langgraph
- Claude model IDs: https://platform.claude.com/docs/en/about-claude/models/overview ; pricing: https://platform.claude.com/docs/en/about-claude/pricing
- McNemar's test for paired classifier comparison: Dietterich, 1998, "Approximate Statistical Tests for Comparing Supervised Classification Learning Algorithms"
