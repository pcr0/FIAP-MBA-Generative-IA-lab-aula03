#!/usr/bin/env bash
# Sobe o MCP Server em modo SSE (HTTP) na porta 8001
# Necessário para clientes que não suportam stdio (ex: n8n rodando em container)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MCP_DIR="$PROJECT_DIR/mcp_server"
VENV_PYTHON="$MCP_DIR/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
  echo ">> venv não encontrado. Criando..."
  python3 -m venv "$MCP_DIR/venv"
  "$VENV_PYTHON" -m pip install -r "$MCP_DIR/requirements.txt"
fi

echo ">> MCP Server (SSE) em http://localhost:8001/sse"
echo "   Conecte o n8n via Instance-level MCP usando essa URL"
echo ""

cd "$MCP_DIR"
MCP_SSE_PORT=8001 "$VENV_PYTHON" -c "
import uvicorn
from main import mcp
app = mcp.sse_app()
uvicorn.run(app, host='0.0.0.0', port=8001)
"
