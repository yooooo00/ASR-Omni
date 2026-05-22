$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = Join-Path $root ".conda-qwen3-asr\python.exe"
$modelscope = Join-Path $root ".conda-qwen3-asr\Scripts\modelscope.exe"
$modelDir = Join-Path $root "models\Qwen3-ASR-0.6B"

if (-not (Test-Path $python)) {
    throw "Python environment not found: $python. Run scripts\setup_windows.ps1 first."
}
if (-not (Test-Path $modelscope)) {
    throw "ModelScope CLI not found: $modelscope. Run scripts\setup_windows.ps1 first."
}

New-Item -ItemType Directory -Force $modelDir | Out-Null

& $modelscope download `
    --model Qwen/Qwen3-ASR-0.6B `
    --local_dir $modelDir `
    --max-workers 1 `
    --endpoint https://modelscope.cn

Write-Host "Model downloaded to $modelDir"
