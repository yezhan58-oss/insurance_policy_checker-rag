#!/bin/bash
# Interactive work session: serve Llama 3.1 8B on your own port (VLLM_PORT in ~/insurance-rag/.env).
# Submit from ~/insurance-rag:   sbatch scripts/serve_llama.sbatch          (shorter: sbatch --time=01:00:00 ...)
# Ready when logs/serve-<jobid>.out shows "Application startup complete"; the node name is on its first line.
# Stop it when you finish (scancel <jobid>) so the shared GPU is released.
#SBATCH --job-name=vllm-serve
#SBATCH --qos=studentqos
#SBATCH --partition=student
#SBATCH --gres=gpu:a40:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=30G
#SBATCH --time=04:00:00
#SBATCH --output=logs/serve-%j.out
set -eo pipefail
source ~/venvs/rag/bin/activate
cd ~/insurance-rag
set -a; source .env; set +a                 # exports VLLM_API_KEY (vLLM reads it itself) and VLLM_PORT
PORT=${PORT:-$VLLM_PORT}
export HF_HOME="$HOME/scratchDirectory/hf"
export VLLM_USE_FLASHINFER_SAMPLER=0        # FlashInfer's sampler JIT-compiles and needs nvcc, which compute nodes lack
echo "NODE=$(hostname) PORT=$PORT"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
exec vllm serve /common/public/llm-models/meta-models/LLAMA3.1/Meta-Llama-3.1-8B-Instruct \
  --served-model-name meta-llama/Llama-3.1-8B-Instruct \
  --host 0.0.0.0 --port "$PORT" --max-model-len 16384 --seed 0 \
  --enable-auto-tool-choice --tool-call-parser llama3_json
