#!/usr/bin/env bash
# Evaluates your twelve queries against the recorded night. Run with: ./verify.sh
cd "$(dirname "$0")" || exit 1
curl -fs http://127.0.0.1:9099/-/ready >/dev/null 2>&1 || { echo "Prometheus is not running. Run ./setup.sh first." >&2; exit 1; }
exec python3 .lab/gymcheck.py
