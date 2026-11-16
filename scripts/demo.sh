#!/usr/bin/env bash
# Run every Module 8 scenario and refresh evidence/*.txt
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Running full simulation"
python3 simulation.py --scenario all

echo
echo "==> Writing evidence files"
python3 simulation.py --write-evidence

echo
echo "Done. See evidence/ and run: python3 simulation.py --scenario <replication|stale|recovery|all>"
