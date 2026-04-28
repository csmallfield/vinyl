# Convenience: activate venv (if not already) and start dev server
if (-not $env:VIRTUAL_ENV) {
    & .\.venv\Scripts\Activate.ps1
}
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
