#!/usr/bin/env bash
# Sobe o MCP Server do Mini-ERP
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_DIR="$SCRIPT_DIR/../mcp_server"

cd "$MCP_DIR"

# Cria venv se não existir
if [ ! -d "venv" ]; then
    echo ">> Criando ambiente virtual..."
    python3 -m venv venv
fi

source venv/bin/activate

echo ">> Instalando dependências..."
pip install -q -r requirements.txt

echo ">> Iniciando MCP Server (stdio)..."
echo "   Para testar: mcp dev main.py"
echo "   Para usar no Claude Desktop: configure o path no claude_desktop_config.json"
python main.py
