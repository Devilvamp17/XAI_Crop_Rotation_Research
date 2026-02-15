#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-llama3.2:3b}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "[error] ollama is not installed. Install from https://ollama.com/download"
  exit 1
fi

if ! pgrep -x ollama >/dev/null 2>&1; then
  echo "[info] starting ollama service"
  ollama serve >/tmp/ollama.log 2>&1 &
  sleep 2
fi

echo "[info] pulling model: ${MODEL}"
ollama pull "${MODEL}"

echo "[ok] local LLM ready: ${MODEL}"
echo "[next] set LOCAL_LLM_MODEL=${MODEL} in .env if different"
