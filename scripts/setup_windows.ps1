$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envDir = Join-Path $root ".conda-qwen3-asr"
$python = Join-Path $envDir "python.exe"
$requirements = Join-Path $root "requirements.txt"

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw "conda was not found on PATH. Install Miniconda or Anaconda first, then rerun this script."
}

if (-not (Test-Path $python)) {
    conda create -y -p $envDir python=3.12 pip
}

& $python -m pip install --upgrade pip
& $python -m pip install -r $requirements

& (Join-Path $root "scripts\download_model.ps1")

Write-Host ""
Write-Host "Setup complete."
Write-Host "Try: .\run_qwen3_asr_prototype.ps1 --no-paste"
