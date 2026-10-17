# Cluster setup (SMU SCIS "origami")

Tested end to end on 17 Oct 2026 on Member A's account: vLLM 0.31.0, torch 2.13 (CUDA 13.0), Llama 3.1 8B
on an A40 on `avenue`, reached from a Windows laptop through an SSH tunnel. Based on Member B's draft.

Claude Code can do every step marked **(agent)** once step 1 works. Steps marked **(human)** need you.

| | Member A (YZ) | Member B |
| --- | --- | --- |
| SMU ID | `yz.wong.2024` | own ID |
| `VLLM_PORT` (interactive server) | 8471 | 8472 |
| Batch job port (`BATCH_PORT`) | 8481 | 8482 |

## Rules

- Never run `srun --pty`, `vllm serve` or `ssh -N -L` in the foreground from an agent: they block. GPU work goes
  through `sbatch`; the human opens tunnels.
- The login node `origami` is only for `sbatch`, `squeue`, `scancel`, reading logs and small edits. No installs,
  no Python workloads.
- Every job needs `--qos=studentqos --partition=student` and a GPU **type** (`gpu:a40:1`). A bare `gpu:1` can land
  on a GTX 1080 Ti, which vLLM cannot use. Alternatives with enough memory: `l40s`, `3090` (24 GB).
- Limits: 1 GPU per job, at most 2 running jobs, at most 1 day per job. Release the GPU when you stop working.
- Secrets live only in `.env` files (`chmod 600` on the cluster). Never in git, logs or chat.

## 1. Laptop: SSH key and shortcut (human, once)

Needs campus Wi-Fi or the SMU VPN. Run in **PowerShell on the laptop** (the prompt must show `C:\Users\...`, not
`[...@origami ~]$`).

```powershell
ssh-keygen -t ed25519
```

Press Enter three times (default file, no passphrase; an agent cannot use a key with a passphrase). Then copy the
public key to the cluster (asks for your SMU password one last time):

```powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh <smu-id>@10.193.104.102 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
```

Add this block to the end of `C:\Users\<you>\.ssh\config` (create the file if needed, and make sure it is saved):

```
Host origami
  HostName 10.193.104.102
  User <smu-id>
  IdentityFile ~/.ssh/id_ed25519
```

Check: `ssh origami hostname` prints `origami` without a password prompt.

## 2. Cluster: clone the repo (human, once)

The repo is private, so HTTPS needs a GitHub fine-grained token: Settings > Developer settings > Fine-grained
tokens, repository access = only this repo, permission **Contents: Read-only** (without it, cloning fails with a
misleading "Write access ... not granted" 403). Copy the token when it is shown; GitHub shows it only once.

```bash
ssh origami
git config --global credential.helper store          # saves the token after the next successful login
git clone https://github.com/yezhan58-oss/insurance_policy_checker-rag ~/insurance-rag
mkdir -p ~/insurance-rag/logs ~/scratchDirectory/hf ~/scratchDirectory/uv-cache
```

Clone **before** creating `~/insurance-rag/logs`: git refuses to clone into a folder that already exists. The
trailing `~/insurance-rag` matters, because every script expects that path. Username = your GitHub username,
password = the token.

## 3. Cluster: `.env` (agent or human, once)

Generate a random server password and store it with your port (use 8472 for Member B):

```bash
ssh origami 'umask 077; printf "VLLM_API_KEY=%s\nVLLM_PORT=8471\n" "$(openssl rand -hex 16)" > ~/insurance-rag/.env'
```

Put the **same** `VLLM_API_KEY` and `VLLM_PORT` into the laptop's `insurance-rag\.env` (copy `.env.example` first).
The cluster needs no Claude key and no Hugging Face token.

## 4. Cluster: Python environment (agent, once)

uv brings its own Python 3.11, so no `module load` is needed anywhere.

```bash
ssh origami 'curl -LsSf https://astral.sh/uv/install.sh | sh'                 # skip if ~/.local/bin/uv exists
ssh origami '~/.local/bin/uv venv --python 3.11 ~/venvs/rag'
```

## 5. Install vLLM and our requirements (agent, once; again after requirements.txt changes)

```bash
ssh origami 'cd ~/insurance-rag && sbatch scripts/install_vllm.sbatch'
```

Takes about 3 minutes once running. Done when `logs/install-<jobid>.out` ends with `vllm 0.31.0 torch ... cuda True`
and `INSTALL_DONE`. If A40s are busy, any 24 GB+ GPU works for the install:
`sbatch --gres=gpu:3090:1 scripts/install_vllm.sbatch`.

## 6. Model

Use the cluster's shared copy. **No Hugging Face access request or download is needed:**

```
/common/public/llm-models/meta-models/LLAMA3.1/Meta-Llama-3.1-8B-Instruct
```

The scripts serve it under the name `meta-llama/Llama-3.1-8B-Instruct`, so `configs/models.yaml` works unchanged.

## 7. Daily routine

1. **Start the server (agent):** `ssh origami 'cd ~/insurance-rag && sbatch scripts/serve_llama.sbatch'`
   (4 h limit; `sbatch --time=01:00:00 scripts/serve_llama.sbatch` for less). "ReqNodeNotAvail" right after
   submitting is normal; check `squeue --me` again a few seconds later.
2. **Wait until ready (agent):** `logs/serve-<jobid>.out` shows `Application startup complete` (1 to 3 minutes).
   Its first line says `NODE=<node> PORT=<port>`.
3. **Open the tunnel (human),** in its own PowerShell window, left open while you work (no output = working):
   ```powershell
   ssh -N -L 8471:avenue:8471 origami
   ```
   Use your own port, and replace `avenue` if the job landed on another node.
4. **Check (agent):** from the repo on the laptop,
   ```powershell
   .venv\Scripts\python -c "from src.llm import get_llm; print(get_llm('vllm_llama8b').invoke('Say hi').content)"
   ```
5. **Finish:** close the tunnel window (Ctrl+C) and release the GPU: `ssh origami "scancel <jobid>"`.

## 8. Full Llama runs without the laptop

```bash
ssh origami 'cd ~/insurance-rag && git pull && sbatch scripts/run_llama.sbatch'
```

The job starts a private server on the batch port, rebuilds the index from the checked-out code, runs
`src.eval.run` and stops the server. Member B's dev runs:
`BATCH_PORT=8482 SPLIT=dev APPROACHES=A4 sbatch scripts/run_llama.sbatch`. Final test runs: Member A, from `main`.
Check with `squeue --me`; cancel with `scancel <jobid>`.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `ssh: Could not resolve hostname origami` | The `Host origami` block is not in `~/.ssh/config` (file not saved?). |
| `ssh` times out | Off campus without the SMU VPN. |
| Clone: 403 "Write access to repository not granted" | Token lacks **Contents: Read-only**. Edit the token, retry; delete `~/.git-credentials` if a bad token was saved. |
| Clone: "destination path already exists" | `~/insurance-rag` was created first. `rm -rf ~/insurance-rag` (only if it holds nothing but `logs/`), then clone. |
| Server log: `Could not find nvcc and default cuda_home='/usr/local/cuda' doesn't exist` | FlashInfer tried to compile. Make sure `VLLM_USE_FLASHINFER_SAMPLER=0` is exported (the scripts do this). |
| Job pending for a long time | A40s busy (`sinfo -p student -o "%N %G %t"`). For the server, `sbatch --gres=gpu:l40s:1 ...` or `gpu:3090:1`. |
| Job rejected for QOS/account | Missing `--qos=studentqos --partition=student`. Never use the `project` partition. |
| vLLM "compute capability" error | Landed on a 1080 Ti: the job has no GPU type. |
| CUDA out of memory on a 3090 | Add `--max-model-len 8192` or `--gpu-memory-utilization 0.92` to the `vllm serve` line. |
| `curl localhost:<port>` gives HTTP 000 | Tunnel not open, wrong node name in the tunnel, or the server job ended. |
| HTTP 401 | Wrong or missing `VLLM_API_KEY`; laptop and cluster `.env` must match. |
| `scipy` "requires Python>=3.12" during install | Old `requirements.txt`; `git pull` (scipy is pinned to a 3.11-compatible version). |
