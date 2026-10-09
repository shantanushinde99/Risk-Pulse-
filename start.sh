#!/usr/bin/env bash
# Start the RiskPulse backend (:8000) and frontend (:3000). Ctrl+C stops both.
cd "$(dirname "$0")"
(cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000) &
(cd frontend && npm run dev) &
trap 'kill 0' EXIT
wait
