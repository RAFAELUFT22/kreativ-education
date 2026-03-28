#!/usr/bin/env bash
# query_openclaw.sh - Query the Qwen2.5-Coder model on the remote Ollama instance.
# Usage: ./query_openclaw.sh "Your prompt here"

set -euo pipefail

PROMPT="$1"
OLLAMA_URL="http://46.202.150.132:11434"
MODEL="qwen2.5-coder:7b"

# Inject TDS context
SYSTEM_CONTEXT="Você é o especialista Antigravity para o projeto Kreativ Education (TDS). 
Regra: Tudo via Dokploy Panel/API. Evitar hardcoded root.
Frappe LMS version: latest.
Language: pt-BR."

RESPONSE=$(curl -s "$OLLAMA_URL/api/generate" -d "{
  \"model\": \"$MODEL\",
  \"prompt\": \"$SYSTEM_CONTEXT\n\nPergunta: $PROMPT\",
  \"stream\": false
}" | jq -r '.response')

echo "$RESPONSE"
