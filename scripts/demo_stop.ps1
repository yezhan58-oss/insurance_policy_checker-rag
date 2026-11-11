# Stop the live demo: close the tunnel and cancel the GPU server job started by demo_start.ps1.
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
if (Test-Path logs\demo_tunnel_pid.txt) {
    $tpid = Get-Content logs\demo_tunnel_pid.txt
    Stop-Process -Id $tpid -Force -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" | Where-Object { $_.CommandLine -like "*-N -L*origami*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Remove-Item logs\demo_tunnel_pid.txt
    Write-Host "Tunnel closed."
}
if (Test-Path logs\demo_job.txt) {
    $job = Get-Content logs\demo_job.txt
    ssh -o BatchMode=yes origami "scancel $job"
    Remove-Item logs\demo_job.txt
    Write-Host "Server job $job cancelled; the GPU is free."
} else {
    Write-Host "No demo job recorded. Check with: ssh origami squeue --me"
}
