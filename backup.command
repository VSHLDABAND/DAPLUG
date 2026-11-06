#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then echo "Run run.command once to set up the environment first."; exit 1; fi
source .venv/bin/activate
python scripts/backup_db.py
