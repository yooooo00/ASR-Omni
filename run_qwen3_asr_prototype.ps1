$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$python = "$root\.conda-qwen3-asr\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing local Python environment. Run .\scripts\setup_windows.ps1 first."
}
& $python -m asr_omni.app @args
