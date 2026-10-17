# Insurance policy checker (IS469 agentic RAG)

Given a travel insurance claim scenario, decide the verdict (covered / not_covered /
partially_covered / insufficient_info) and cite the policy clauses that decide it. We compare a
no-retrieval baseline, simple RAG and two agentic RAG setups. Full design: `PROJECT_BRIEF.md`.

## Laptop setup (Windows CMD)

```
git clone https://github.com/yezhan58-oss/insurance_policy_checker-rag insurance-rag
cd insurance-rag
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env` with your own values (never commit it). Do not set `ANTHROPIC_API_KEY` as a Windows
environment variable, or Claude Code will bill the course credits (brief section 3.2).

## Build the index

```
python -m src.ingest
```

Reads the PDFs in `data/policies/` (see `data/policies/SNAPSHOT.md`) and writes the Chroma index
and section files to `data/index/` (git-ignored). Deterministic, so every machine builds the same
index. Prints 10 random sections per policy for a parsing check.

Search it from Python with `src.store` (`search`, `get_section`, `list_sections`, `definitions`).
Run the checks before opening a pull request:

```
pytest -q
```

## Cluster setup

Follow `CLUSTER_SETUP.md` (tested on 17 Oct 2026): SSH key and tunnel, clone, `.env`, uv environment,
`sbatch scripts/install_vllm.sbatch`, then `sbatch scripts/serve_llama.sbatch` (or `serve_gptoss.sbatch`) each work
session. Both tested models, Llama 3.1 8B and gpt-oss-20b, come from the cluster's shared copies, so no Hugging Face
access request is needed. Only the LLM judge (Claude Haiku 5.5) uses the Claude API.
