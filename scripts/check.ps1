$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing .venv. Install development dependencies before running checks."
}

& $python -m ruff check .
& $python -m pytest -q
& $python -m compileall -q app worker
git diff --check
