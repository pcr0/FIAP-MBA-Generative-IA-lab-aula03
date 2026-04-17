#!/usr/bin/env bash
# Registra o n8n como MCP Server no Claude Code
# O n8n expõe seus workflows como tools MCP via HTTP
#
# Uso:
#   bash scripts/add_n8n_mcp.sh <ACCESS_TOKEN>
#
# O token é gerado no n8n em Settings > Instance-level MCP > Connection details.
# Ele persiste em ~/.n8n entre reinícios do container.
set -e

N8N_MCP_URL="http://localhost:5678/mcp-server/http"

if [ -z "$1" ]; then
  echo "Uso: bash scripts/add_n8n_mcp.sh <ACCESS_TOKEN>"
  echo ""
  echo "O token está em: n8n > Settings > Instance-level MCP > Connection details"
  exit 1
fi

TOKEN="$1"

echo ">> Registrando n8n como MCP Server no Claude Code..."
echo "   URL: $N8N_MCP_URL"
echo ""

# Remove se já existir
claude mcp remove n8n-erp 2>/dev/null || true

claude mcp add n8n-erp "$N8N_MCP_URL" --transport http --header "Authorization:Bearer $TOKEN"

echo ""
echo ">> Verificando conexão..."
claude mcp list

echo ""
echo ">> Reinicie a sessão do Claude Code para as tools ficarem disponíveis."
