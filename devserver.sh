#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ -f .venv/bin/activate ]; then
    . .venv/bin/activate
fi
# Flask loads local .env settings when python-dotenv is installed.
python -m flask --app main run --debug --host 127.0.0.1 --port "${PORT:-5000}"
