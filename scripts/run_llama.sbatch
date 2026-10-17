#!/bin/bash
# Full Llama runs with no laptop needed: start a private vLLM server inside the job, rebuild the
# index from the current code, run the evaluation, stop the server.
# Submit from ~/insurance-rag after `git pull`:
#   sbatch scripts/run_llama.sbatch                                   (Member A, test split)
#   BATCH_PORT=8482 SPLIT=dev APPROACHES=A4 sbatch scripts/run_llama.sbatch   (Member B, dev)
#SBATCH --job-name=run-llama
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
export VLLM_PORT=${BATCH_PORT:-8481}     # batch port, so it never clashes with your interactive server
export HF_HOME="$HOME/scratchDirectory/hf"
export VLLM_USE_FLASHINFER_SAMPLER=0     # see scripts/serve_llama.sbatch
vllm serve /common/public/llm-models/meta-models/LLAMA3.1/Meta-Llama-3.1-8B-Instruct \
  --served-model-name meta-llama/Llama-3.1-8B-Instruct \
  --host 127.0.0.1 --port $VLLM_PORT --max-model-len 16384 --seed 0 \
  --enable-auto-tool-choice --tool-call-parser llama3_json > logs/vllm_$SLURM_JOB_ID.log 2>&1 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null' EXIT
python -m src.ingest --samples 0         # index always matches the checked-out code (CPU, about a minute)
until curl -sf -H "Authorization: Bearer $VLLM_API_KEY" http://127.0.0.1:$VLLM_PORT/v1/models > /dev/null; do kill -0 $VLLM_PID 2>/dev/null || exit 1; sleep 10; done
python -m src.eval.run --model vllm_llama8b --split ${SPLIT:-test} ${APPROACHES:+--approaches $APPROACHES}
