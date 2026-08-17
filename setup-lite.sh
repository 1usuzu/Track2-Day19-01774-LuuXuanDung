#!/usr/bin/env bash
# Lite path: pure Python, in-process Qdrant, SQLite Feast online store.
# No Docker, no GPU, no external services. ~60s on a clean machine.

set -euo pipefail

echo "[lite] Day 19 lightweight setup"
echo "[lite] Stack: fastembed + qdrant-client[memory] + rank-bm25 + feast(sqlite) + FastAPI"
echo

# ── 1. Python ───────────────────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || { echo "[lite] python3 not found. Install Python 3.10+."; exit 1; }
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[lite] Python $PY_VER detected"

# ── 2. venv ─────────────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  if command -v uv >/dev/null 2>&1; then
    echo "[lite] Creating venv with uv (faster)"
    uv venv .venv
  else
    echo "[lite] Creating venv with python -m venv"
    python3 -m venv .venv
  fi
fi
# shellcheck source=/dev/null
source .venv/bin/activate

# ── 3. Install deps ─────────────────────────────────────────────────────
if command -v uv >/dev/null 2>&1; then
  uv pip install -r requirements.txt
else
  pip install -q -U pip
  pip install -q -r requirements.txt
fi

# ── 4. Convert Jupytext sources to .ipynb ───────────────────────────────
# `_setup.py` is a helper module, not a notebook -- converting it produces
# a _setup.ipynb that fails on execute. Only convert numbered notebooks.
jupytext --to notebook --update notebooks/[0-9]*.py 2>/dev/null || jupytext --to notebook notebooks/[0-9]*.py

# ── 5. .env scaffold ────────────────────────────────────────────────────
[ -f .env ] || cp .env.example .env

# ── 6. Seed corpus + golden set ─────────────────────────────────────────
python scripts/seed_corpus.py

# Data for the advanced missions (NB6 compound queries, NB8 spend parquet).
# gen_agent_queries embeds the corpus once to build brute-force ground truth,
# so this adds ~20 s -- worth it: the alternative is students hand-labelling.
echo "  · seeding advanced-mission data (NB6 + NB8)…"
python scripts/gen_agent_queries.py
python scripts/gen_spend.py

# ── 7. Smoke test ───────────────────────────────────────────────────────
python scripts/verify_lite.py

cat <<EOF

[lite] Done. Activate the venv and start working:

    source .venv/bin/activate
    make api       # start FastAPI on :8000
    make lab       # open Jupyter on :8888
    make benchmark # Precision@10 + latency table

Tip: read VIBE-CODING.md before starting NB1 — it tells you what to delegate
to your AI assistant and what to think through yourself.
EOF
