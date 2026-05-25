$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$python = "$root\.conda-qwen3-asr\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing local Python environment. Run .\scripts\setup_windows.ps1 first."
}

$forwardArgs = @($args)

function Test-HasOption {
    param(
        [string[]]$Arguments,
        [string]$Name
    )
    foreach ($arg in $Arguments) {
        if ($arg -eq $Name -or $arg.StartsWith("$Name=")) {
            return $true
        }
    }
    return $false
}

if (-not (Test-HasOption -Arguments $forwardArgs -Name "--language")) {
    $forwardArgs = @("--language", "auto") + $forwardArgs
}
if (-not (Test-HasOption -Arguments $forwardArgs -Name "--context")) {
    $forwardArgs = @(
        "--context",
        "Mostly Chinese dictation with some English technical terms, product names, and code terms; preserve English words as English."
    ) + $forwardArgs
}
$defaultGlossary = Join-Path $root "glossary.tsv"
if (
    -not (Test-HasOption -Arguments $forwardArgs -Name "--glossary-file") -and
    -not (Test-HasOption -Arguments $forwardArgs -Name "--no-default-glossary") -and
    (Test-Path $defaultGlossary)
) {
    $forwardArgs = @("--glossary-file", $defaultGlossary) + $forwardArgs
}

& $python -m asr_omni.app @forwardArgs
