#!/bin/bash
# Full runs of one model with no laptop needed: start a private vLLM server inside the job, rebuild the
# index from the current code, run the evaluation, stop the server.
# Submit from ~/insurance-rag after `git pull`:
#   MODEL=vllm_llama8b sbatch scripts/run_eval.sbatch                     (Member A, test split)
#   MODEL=vllm_gptoss20b sbatch scripts/run_eval.sbatch
#   MODEL=vllm_gptoss20b BATCH_PORT=8482 SPLIT=dev APPROACHES=A4 sbatch scripts/run_eval.sbatch   (Member B, dev)
#   MODEL=vllm_llama8b APPROACHES=L0 MAX_LEN=131072 sbatch scripts/run_eval.sbatch   (exploratory long-context L0:
#   the whole policy is about 28k (FWD) to 45k (MSIG) tokens; run it after the core run of that model has finished, same results folder)
#SBATCH --job-name=run-eval
#SBATCH --qos=studentqos
#SBATCH --partition=student
#SBATCH --gres=gpu:a40:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=30G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%j.out
set -eo pipefail
source ~/venvs/rag/bin/activate
cd ~/insurance-rag
set -a; source .env; set +a
MODEL=${MODEL:-vllm_llama8b}
PORT=${BATCH_PORT:-8481}                   # batch port, so it never clashes with your interactive servers
case $MODEL in
  vllm_llama8b)
    export VLLM_PORT=$PORT                 # configs/models.yaml reads the Llama port from VLLM_PORT
    WEIGHTS=/common/public/llm-models/meta-models/LLAMA3.1/Meta-Llama-3.1-8B-Instruct
    NAME=meta-llama/Llama-3.1-8B-Instruct
    EXTRA="--enable-auto-tool-choice --tool-call-parser llama3_json" ;;
  vllm_gptoss20b)
    export VLLM_GPTOSS_PORT=$PORT          # ... and the gpt-oss port from VLLM_GPTOSS_PORT
    WEIGHTS=/common/public/llm-models/openai/gpt-oss-20b
    NAME=openai/gpt-oss-20b
    EXTRA="--attention-backend TRITON_ATTN" ;;
  *) echo "Unknown MODEL=$MODEL (use vllm_llama8b or vllm_gptoss20b)"; exit 1 ;;
esac
export HF_HOME="$HOME/scratchDirectory/hf"
export VLLM_USE_FLASHINFER_SAMPLER=0       # see scripts/serve_llama.sbatch
export VLLM_CACHE_ROOT="$HOME/scratchDirectory/vllm-cache" TRITON_CACHE_DIR="$HOME/scratchDirectory/triton-cache"   # home has a 100k file+folder limit
# Private index on the node's local disk: concurrent jobs must not rebuild one shared index, and Chroma's
# SQLite is unreliable on the network home filesystem.
export RAG_INDEX_DIR="${TMPDIR:-/tmp}/rag-index-$SLURM_JOB_ID"
echo "MODEL=$MODEL NODE=$(hostname) PORT=$PORT"
vllm serve $WEIGHTS --served-model-name $NAME --host 127.0.0.1 --port $PORT \
  --max-model-len ${MAX_LEN:-16384} --seed 0 $EXTRA > logs/vllm_$SLURM_JOB_ID.log 2>&1 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null; rm -rf "$RAG_INDEX_DIR"' EXIT
python -m src.ingest --samples 0           # index always matches the checked-out code (CPU, about a minute)
until curl -sf -H "Authorization: Bearer $VLLM_API_KEY" http://127.0.0.1:$PORT/v1/models > /dev/null; do kill -0 $VLLM_PID 2>/dev/null || exit 1; sleep 10; done
python -m src.eval.run --model $MODEL --split ${SPLIT:-test} ${APPROACHES:+--approaches $APPROACHES} ${OUT:+--out $OUT}
