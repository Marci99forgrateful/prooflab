#!/usr/bin/env bash
# Repeatable setup. This script never rewrites source files or dependency locks.
set -euo pipefail
PROOFLAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$PROOFLAB_ROOT"
if [[ -d /workspace/.toolchains/elan ]]; then
  export ELAN_HOME="${ELAN_HOME:-/workspace/.toolchains/elan}"
  export PATH="$ELAN_HOME/bin:$PATH"
fi
if ! command -v elan >/dev/null; then
  export ELAN_HOME="${ELAN_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/prooflab-tools/elan}"
  mkdir -p "$ELAN_HOME"
  PROOFLAB_INSTALLER=$(mktemp)
  trap 'rm -f "$PROOFLAB_INSTALLER"' EXIT
  curl --proto '=https' --tlsv1.2 -fLsS \
    https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    -o "$PROOFLAB_INSTALLER"
  sh "$PROOFLAB_INSTALLER" -y --no-modify-path --default-toolchain none
  export PATH="$ELAN_HOME/bin:$PATH"
fi
command -v uv >/dev/null || { echo 'Install uv: https://docs.astral.sh/uv/' >&2; exit 1; }
command -v npm >/dev/null || { echo 'Node.js 20.19+ and npm are required.' >&2; exit 1; }
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$XDG_CACHE_HOME/uv}"
export npm_config_cache="${npm_config_cache:-$XDG_CACHE_HOME/npm}"
mkdir -p "$XDG_CACHE_HOME" "$UV_CACHE_DIR" "$npm_config_cache"
lean --version
uv sync --frozen --extra dev
# Lake uses the committed manifest to restore pinned Git dependencies.
lake exe cache get Mathlib.Data.Set.Basic Mathlib.Algebra.Group.Basic \
  Mathlib.Algebra.Ring.Basic Mathlib.Tactic.Ring
lake build ProofLab
npm --prefix web ci --no-audit --no-fund
uv run --frozen python scripts/export_phase3.py
uv run --frozen python scripts/export_phase4.py
npm --prefix web run build
echo 'ProofLab installed. Start: uv run --frozen prooflab serve'
