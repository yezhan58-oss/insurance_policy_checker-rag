#!/bin/bash
# Interactive work session: serve gpt-oss-20b on your own port (VLLM_GPTOSS_PORT in ~/insurance-rag/.env).
# Submit from ~/insurance-rag:   sbatch scripts/serve_gptoss.sbatch          (shorter: sbatch --time=01:00:00 ...)
# Ready when logs/serve-gptoss-<jobid>.out shows "Application startup complete"; the node name is on its first line.
# Stop it when you finish (scancel <jobid>) so the shared GPU is released.
#SBATCH --job-name=vllm-gptoss
#SBATCH --qos=studentqos
#SBATCH --partition=student
#SBATCH --gres=gpu:a40:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=30G
#SBATCH --time=04:00:00
#SBATCH --output=logs/serve-gptoss-%j.out
set -eo pipefail
source ~/venvs/rag/bin/activate
cd ~/insurance-rag
set -a; source .env; set +a                 # exports VLLM_API_KEY (vLLM reads it itself) and VLLM_GPTOSS_PORT
PORT=${PORT:-$VLLM_GPTOSS_PORT}
export HF_HOME="$HOME/scratchDirectory/hf"
export VLLM_USE_FLASHINFER_SAMPLER=0        # FlashInfer kernels JIT-compile and need nvcc, which compute nodes lack
echo "NODE=$(hostname) PORT=$PORT"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
exec vllm serve /common/public/llm-models/openai/gpt-oss-20b \
  --served-model-name openai/gpt-oss-20b \
  --host 0.0.0.0 --port "$PORT" --max-model-len 16384 --seed 0 \
  --attention-backend TRITON_ATTN
