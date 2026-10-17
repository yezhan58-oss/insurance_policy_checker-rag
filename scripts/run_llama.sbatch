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
