#!/usr/bin/env bash
# Testa o MCP Server usando o MCP Inspector (mcp dev)
# Requisito: ERP rodando em http://localhost:8000
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_DIR="$SCRIPT_DIR/../mcp_server"

cd "$MCP_DIR"

# Ativa venv
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "== Testando MCP Server com MCP Inspector =="
echo ""
echo "O Inspector abre no browser e permite testar cada tool interativamente."
echo "Certifique-se de que o ERP está rodando (bash scripts/start_erp.sh)."
echo ""
echo "Fluxo sugerido para teste:"
echo "  1. listar_produtos        → ver produtos disponíveis"
echo "  2. consultar_estoque(1)   → ver estoque do produto 1"
echo "  3. criar_pedido           → criar pedido com itens"
echo "  4. consultar_pedido       → verificar pedido criado"
echo "  5. gerar_fatura_simulada  → faturar o pedido"
echo "  6. consultar_fatura       → verificar fatura gerada"
echo ""

mcp dev main.py
