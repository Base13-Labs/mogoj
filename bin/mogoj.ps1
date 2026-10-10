#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Cli = Join-Path $RepoRoot "tools/cli.py"

$Python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $Python) {
    Write-Error "Mogoj requires Python 3.9 or newer. Install it from https://python.org and retry."
    exit 4
}

& $Python.Source $Cli @args
exit $LASTEXITCODE
