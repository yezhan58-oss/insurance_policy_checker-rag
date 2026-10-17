#!/bin/bash
# One-time (or after requirements.txt changes): install vLLM + our requirements into ~/venvs/rag.
# Submit from ~/insurance-rag:   sbatch scripts/install_vllm.sbatch
# Any modern GPU works for this (it only checks CUDA); if A40s are busy: sbatch --gres=gpu:3090:1 scripts/install_vllm.sbatch
#SBATCH --job-name=install-vllm
#SBATCH --qos=studentqos
#SBATCH --partition=student
#SBATCH --gres=gpu:a40:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=30G
#SBATCH --time=00:45:00
#SBATCH --output=logs/install-%j.out
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export UV_CACHE_DIR="$HOME/scratchDirectory/uv-cache" UV_LINK_MODE=copy   # keep the big download cache off home
source ~/venvs/rag/bin/activate
cd ~/insurance-rag
echo "node=$(hostname)"; python --version
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
uv pip install vllm
uv pip install -r requirements.txt      # no torch pin, so vLLM's torch is kept
python -c "import vllm, torch, langchain_openai, chromadb, sentence_transformers; print('vllm', vllm.__version__, 'torch', torch.__version__, 'cuda', torch.cuda.is_available())"
echo INSTALL_DONE
