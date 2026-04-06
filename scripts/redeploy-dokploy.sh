#!/usr/bin/env bash
# =============================================================================
# redeploy-dokploy.sh — Dispara redeploy de um compose via Dokploy API
#
# REQUISITOS:
#   - curl e jq instalados
#   - .env preenchido com DOKPLOY_API_TOKEN e DOKPLOY_URL
#
# USO:
#   bash scripts/redeploy-dokploy.sh              # lista composes e pergunta
#   bash scripts/redeploy-dokploy.sh <composeId>  # redeploy direto
#   DOKPLOY_COMPOSE_ID=abc123 bash scripts/redeploy-dokploy.sh
#
# VARIÁVEIS OPCIONAIS:
#   DEPLOY_TIMEOUT_SECS  — timeout em segundos (padrão: 1800 = 30 min)
#   POLL_INTERVAL_SECS   — intervalo de polling (padrão: 5)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

DEPLOY_TIMEOUT_SECS="${DEPLOY_TIMEOUT_SECS:-1800}"
POLL_INTERVAL_SECS="${POLL_INTERVAL_SECS:-5}"

# Cores
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${BLUE}⏳${NC} $1"; }
ok()   { echo -e "${GREEN}✅${NC} $1"; }
warn() { echo -e "${YELLOW}⚠️${NC}  $1"; }
fail() { echo -e "${RED}❌${NC} $1"; exit 1; }
info() { echo -e "${CYAN}ℹ${NC}  $1"; }

# ---------------------------------------------------------------------------
# Dependências
# ---------------------------------------------------------------------------
command -v curl &>/dev/null || fail "curl não instalado. Instale com: apt-get install curl"
command -v jq   &>/dev/null || fail "jq não instalado. Instale com: apt-get install jq"

# ---------------------------------------------------------------------------
# Carregar .env
# ---------------------------------------------------------------------------
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  warn "Arquivo .env não encontrado em $ENV_FILE"
  warn "As variáveis devem estar exportadas no ambiente."
fi

# ---------------------------------------------------------------------------
# Validar variáveis obrigatórias
# ---------------------------------------------------------------------------
DOKPLOY_URL="${DOKPLOY_URL:-http://46.202.150.132:3000}"
DOKPLOY_API_TOKEN="${DOKPLOY_API_TOKEN:-}"

if [ -z "$DOKPLOY_API_TOKEN" ]; then
  fail "DOKPLOY_API_TOKEN não definido. Adicione ao .env ou exporte antes de executar."
fi

# Remover barra final da URL
DOKPLOY_URL="${DOKPLOY_URL%/}"
API_BASE="$DOKPLOY_URL/api"

# ---------------------------------------------------------------------------
# Funções auxiliares de API
# ---------------------------------------------------------------------------
api_get() {
  local endpoint="$1"
  curl -sf \
    -H "x-api-key: $DOKPLOY_API_TOKEN" \
    -H "Content-Type: application/json" \
    "$API_BASE/$endpoint"
}

api_post() {
  local endpoint="$1"
  local body="$2"
  curl -sf \
    -X POST \
    -H "x-api-key: $DOKPLOY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$body" \
    "$API_BASE/$endpoint"
}

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo ""
echo "============================================="
echo " Kreativ TDS — Dokploy Redeploy"
echo " Servidor: $DOKPLOY_URL"
echo "============================================="
echo ""

# ---------------------------------------------------------------------------
# Determinar composeId
# ---------------------------------------------------------------------------
COMPOSE_ID="${1:-${DOKPLOY_COMPOSE_ID:-}}"

if [ -z "$COMPOSE_ID" ]; then
  log "Buscando composes disponíveis em $API_BASE/compose.all ..."

  COMPOSES_JSON=$(api_get "compose.all" 2>/dev/null) || \
    fail "Falha ao conectar na API do Dokploy. Verifique DOKPLOY_URL e DOKPLOY_API_TOKEN."

  COMPOSE_COUNT=$(echo "$COMPOSES_JSON" | jq 'length' 2>/dev/null) || \
    fail "Resposta inesperada da API. Resposta: $COMPOSES_JSON"

  if [ "$COMPOSE_COUNT" -eq 0 ]; then
    fail "Nenhum compose encontrado no Dokploy."
  fi

  echo ""
  echo " Composes disponíveis:"
  echo " ─────────────────────"
  # Exibe lista numerada com nome e status
  while IFS= read -r line; do
    echo " $line"
  done < <(echo "$COMPOSES_JSON" | jq -r 'to_entries[] | "  \(.key + 1)) \(.value.name // "sem-nome") [\(.value.composeId)] — status: \(.value.composeStatus // "desconhecido")"')
  echo ""

  read -rp " Escolha o número do compose para redeploiar: " CHOICE
  echo ""

  # Validar escolha (1-indexed)
  if ! [[ "$CHOICE" =~ ^[0-9]+$ ]] || [ "$CHOICE" -lt 1 ] || [ "$CHOICE" -gt "$COMPOSE_COUNT" ]; then
    fail "Escolha inválida: $CHOICE (esperado 1-$COMPOSE_COUNT)"
  fi

  INDEX=$(( CHOICE - 1 ))
  COMPOSE_ID=$(echo "$COMPOSES_JSON" | jq -r ".[$INDEX].composeId")
  COMPOSE_NAME=$(echo "$COMPOSES_JSON" | jq -r ".[$INDEX].name // \"sem-nome\"")
  info "Compose selecionado: $COMPOSE_NAME ($COMPOSE_ID)"
else
  # Verifica se o ID existe
  COMPOSE_INFO=$(api_get "compose.one?composeId=$COMPOSE_ID" 2>/dev/null) || \
    fail "Compose '$COMPOSE_ID' não encontrado. Verifique DOKPLOY_COMPOSE_ID."
  COMPOSE_NAME=$(echo "$COMPOSE_INFO" | jq -r '.name // "sem-nome"')
  info "Compose: $COMPOSE_NAME ($COMPOSE_ID)"
fi

echo ""

# ---------------------------------------------------------------------------
# Disparar redeploy
# ---------------------------------------------------------------------------
log "Disparando redeploy de '$COMPOSE_NAME'..."

REDEPLOY_RESPONSE=$(api_post "compose.redeploy" "{\"composeId\":\"$COMPOSE_ID\"}" 2>/dev/null) || \
  fail "Falha ao disparar redeploy. Verifique permissões do token."

ok "Redeploy iniciado!"
echo ""

# ---------------------------------------------------------------------------
# Polling de status
# ---------------------------------------------------------------------------
log "Monitorando deploy (timeout: ${DEPLOY_TIMEOUT_SECS}s, intervalo: ${POLL_INTERVAL_SECS}s)..."
log "Pressione Ctrl+C para parar o monitoramento sem cancelar o deploy."
echo ""

ELAPSED=0
LAST_STATUS=""

while [ $ELAPSED -lt $DEPLOY_TIMEOUT_SECS ]; do
  sleep "$POLL_INTERVAL_SECS"
  ELAPSED=$(( ELAPSED + POLL_INTERVAL_SECS ))

  DEPLOYMENTS=$(api_get "deployment.allByCompose?composeId=$COMPOSE_ID" 2>/dev/null) || {
    warn "Falha ao obter status (${ELAPSED}s) — tentando novamente..."
    continue
  }

  # Pega o deployment mais recente (índice 0)
  CURRENT_STATUS=$(echo "$DEPLOYMENTS" | jq -r '.[0].status // "unknown"' 2>/dev/null)
  DEPLOYMENT_ID=$(echo "$DEPLOYMENTS"  | jq -r '.[0].deploymentId // ""' 2>/dev/null)

  if [ "$CURRENT_STATUS" != "$LAST_STATUS" ]; then
    TIMESTAMP=$(date '+%H:%M:%S')
    case "$CURRENT_STATUS" in
      "running")  echo -e "  [${TIMESTAMP}] ${BLUE}🔄 Rodando...${NC}" ;;
      "done")     ;;  # Tratado abaixo
      "error")    ;;  # Tratado abaixo
      *)          echo -e "  [${TIMESTAMP}] ${YELLOW}⏳ ${CURRENT_STATUS}${NC}" ;;
    esac
    LAST_STATUS="$CURRENT_STATUS"
  fi

  if [ "$CURRENT_STATUS" = "done" ]; then
    echo ""
    ok "Deploy concluído com sucesso! (${ELAPSED}s)"
    echo ""
    echo " 🌐 Verifique os serviços:"
    echo "    https://lms.ipexdesenvolvimento.cloud"
    echo "    https://n8n.ipexdesenvolvimento.cloud"
    echo "    https://evolution.ipexdesenvolvimento.cloud"
    echo "    https://rag.ipexdesenvolvimento.cloud"
    echo "    https://chat.ipexdesenvolvimento.cloud"
    echo ""
    exit 0
  fi

  if [ "$CURRENT_STATUS" = "error" ]; then
    echo ""
    fail "Deploy falhou (${ELAPSED}s). Deployment ID: $DEPLOYMENT_ID\n   Verifique os logs no painel: $DOKPLOY_URL"
  fi

done

echo ""
warn "Timeout atingido (${DEPLOY_TIMEOUT_SECS}s). O deploy pode ainda estar em progresso."
warn "Verifique o painel: $DOKPLOY_URL"
exit 1
