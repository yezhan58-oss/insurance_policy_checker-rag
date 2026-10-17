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

## Cluster setup

TODO (Member A): notes and fixes from the first cluster setup (brief section 4).
