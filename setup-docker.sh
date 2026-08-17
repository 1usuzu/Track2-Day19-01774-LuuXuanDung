#!/usr/bin/env bash
# Full Docker path: Qdrant server + Redis online store + Postgres offline store.
# Same Python venv as lite + the docker extras. ~3-5 min on first run (image pulls).

set -euo pipefail

echo "[docker] Day 19 full Docker setup"
echo "[docker] Stack: Qdrant (server) + Redis + Postgres + bge-m3 embeddings"
echo

# ── 1. Runtime preflight ────────────────────────────────────────────────
# Three runtimes are plausible now. Apple's `container` has no compose
# implementation, so it gets its own start path (scripts/container-up.sh).
# `bash scripts/runtime-check.sh` prints the full picture.
RUNTIME=""
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 \
   && docker info >/dev/null 2>&1; then
  RUNTIME="docker"
elif command -v container >/dev/null 2>&1; then
  RUNTIME="apple"
fi

case "$RUNTIME" in
  docker)
    echo "[docker] using docker compose"
    docker compose up -d
    echo "[docker] Waiting up to 30s for services to become healthy..."
    for i in $(seq 1 30); do
      if docker compose ps --format json | grep -q '"Health":"healthy"'; then break; fi
      sleep 1
    done
    ;;
  apple)
    echo "[docker] Docker unavailable; using Apple container (github.com/apple/container)"
    bash scripts/container-up.sh
    ;;
  *)
    echo "[docker] No usable container runtime found."
    echo "[docker] Run 'bash scripts/runtime-check.sh' for details, or use the lite path:"
    echo "[docker]   bash setup-lite.sh"
    exit 1
    ;;
esac

# ── 3. Python venv (same as lite) ───────────────────────────────────────
if [ ! -d ".venv" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv .venv
  else
    python3 -m venv .venv
  fi
fi
# shellcheck source=/dev/null
source .venv/bin/activate

# ── 4. Install lite + docker extras ─────────────────────────────────────
NEED_DILL_OVERRIDE=$(python -c 'import sys; print(1 if sys.version_info >= (3,14) else 0)')
if [ "$NEED_DILL_OVERRIDE" = "1" ]; then
  echo "[docker] venv Python >= 3.14 -> applying dill>=0.4 override (see requirements.txt)"
fi
if command -v uv >/dev/null 2>&1; then
  if [ "$NEED_DILL_OVERRIDE" = "1" ]; then
    uv pip install --overrides overrides-py314.txt -r requirements.txt -r requirements-full.txt
  else
    uv pip install -r requirements.txt -r requirements-full.txt
  fi
else
  pip install -q -U pip
  pip install -q -r requirements.txt -r requirements-full.txt
  if [ "$NEED_DILL_OVERRIDE" = "1" ]; then
    pip install -q --upgrade 'dill>=0.4,<1.0'
  fi
fi

# `_setup.py` is a helper module, not a notebook (see setup-lite.sh).
jupytext --to notebook --update notebooks/[0-9]*.py 2>/dev/null || jupytext --to notebook notebooks/[0-9]*.py

# ── 5. .env for docker mode ─────────────────────────────────────────────
if [ ! -f .env ]; then
  cp .env.example .env
  # Flip the lite defaults to docker — the user can edit afterward.
  sed -i.bak \
    -e 's/^QDRANT_MODE=memory/QDRANT_MODE=server/' \
    -e 's/^EMBEDDING_BACKEND=fastembed/EMBEDDING_BACKEND=bge-m3/' \
    -e 's/^FEAST_ONLINE_STORE=sqlite/FEAST_ONLINE_STORE=redis/' \
    -e 's/^FEAST_OFFLINE_STORE=file/FEAST_OFFLINE_STORE=postgres/' \
    .env
  rm -f .env.bak
fi

# ── 6. Seed corpus + smoke test ─────────────────────────────────────────
python scripts/seed_corpus.py
python scripts/verify_docker.py

cat <<EOF

[docker] Done. Services running:

  Qdrant   → http://localhost:6333  (dashboard)
  Redis    → redis://localhost:6379
  Postgres → postgresql://feast:feast@localhost:5432/feast_offline

Activate the venv and continue:

    source .venv/bin/activate
    make api       # start FastAPI on :8000
    make lab       # open Jupyter on :8888

Stop the stack later: docker compose down (state persists)
                  or  docker compose down -v (full reset)
EOF
