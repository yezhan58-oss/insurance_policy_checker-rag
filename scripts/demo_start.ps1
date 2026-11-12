# One command to start the "Am I covered?" demo from the laptop (Windows PowerShell).
#
#   .\scripts\demo_start.ps1            live: GPU server on the cluster + tunnel + app (campus Wi-Fi or VPN)
#   .\scripts\demo_start.ps1 -Offline   cached questions only: just the app, no cluster needed
#   .\scripts\demo_start.ps1 -Gpu a40   another GPU type (default l40s: the A40 node avenue has been drained since 11 Nov)
#
# The app opens at http://localhost:8502, the address in docs/PRESENTATION_SCRIPT.md.
# Stop everything afterwards with .\scripts\demo_stop.ps1 (frees the shared GPU).
param([switch]$Offline, [string]$Hours = "02:00:00", [string]$Gpu = "l40s")
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
New-Item -ItemType Directory -Force logs | Out-Null
$streamlit = Join-Path $repo ".venv\Scripts\streamlit.exe"

if (-not $Offline) {
    $port = (Select-String -Path .env -Pattern '^VLLM_GPTOSS_PORT=(\d+)').Matches[0].Groups[1].Value
    Write-Host "1/4 Submitting the gpt-oss server job (port $port, GPU $Gpu, time $Hours)..."
    # --gres here overrides the script's own #SBATCH line (gpu:a40:1)
    $out = ssh -o BatchMode=yes origami "cd ~/insurance-rag && sbatch --time=$Hours --gres=gpu:${Gpu}:1 scripts/serve_gptoss.sbatch"
    if ($out -notmatch 'Submitted batch job (\d+)') { throw "Could not submit the job: $out" }
    $job = $Matches[1]
    Set-Content logs\demo_job.txt $job
    Write-Host "    job $job"

    Write-Host "2/4 Waiting for the model to load (usually 2-5 minutes)..."
    $node = $null
    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep 10
        $state = ssh -o BatchMode=yes origami "squeue -h -j $job -o '%T %N'; grep -c 'Application startup complete' ~/insurance-rag/logs/serve-gptoss-$job.out 2>/dev/null || true"
        $lines = @($state)
        if (-not $lines[0] -or $lines[0].Trim() -eq "") {
            ssh -o BatchMode=yes origami "tail -20 ~/insurance-rag/logs/serve-gptoss-$job.out"
            throw "The job ended before the server was ready (log above)."
        }
        $parts = $lines[0].Trim() -split '\s+'
        if ($parts[0] -eq "PENDING") { Write-Host "    waiting for a free GPU..."; continue }
        $node = $parts[1]
        if ($lines.Count -gt 1 -and [int]$lines[-1] -ge 1) { break }
        Write-Host "    loading on $node..."
        $node = $null
    }
    if (-not $node) { throw "Server not ready after 15 minutes. Check: ssh origami ""tail ~/insurance-rag/logs/serve-gptoss-$job.out""" }
    Write-Host "    ready on $node"

    Write-Host "3/4 Opening the tunnel in a new window (leave it open)..."
    $tunnel = Start-Process powershell -PassThru -ArgumentList "-NoExit", "-Command",
        "Write-Host 'Tunnel to $node`:$port - leave this window open'; ssh -N -L ${port}:${node}:${port} origami"
    Set-Content logs\demo_tunnel_pid.txt $tunnel.Id
}

Write-Host "4/4 Starting the app at http://localhost:8502 (Ctrl+C here to stop the app)"
& $streamlit run app\streamlit_app.py --server.port 8502
