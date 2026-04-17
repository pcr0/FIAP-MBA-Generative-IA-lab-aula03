#!/usr/bin/env bash
# Testa os endpoints do Mini-ERP para verificar que está funcionando
set -e

BASE="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }

echo "== Testando Mini-ERP em $BASE =="
echo ""

# Health
curl -sf "$BASE/health" > /dev/null && pass "GET /health" || fail "GET /health"

# Produtos
curl -sf "$BASE/produtos" > /dev/null && pass "GET /produtos" || fail "GET /produtos"
curl -sf "$BASE/produtos/1" > /dev/null && pass "GET /produtos/1" || fail "GET /produtos/1"

# Estoque
curl -sf "$BASE/estoque/1" > /dev/null && pass "GET /estoque/1" || fail "GET /estoque/1"

# Criar pedido
PEDIDO=$(curl -sf -X POST "$BASE/pedidos" \
  -H "Content-Type: application/json" \
  -d '{"nome_cliente":"Teste Lab","itens":[{"produto_id":1,"quantidade":1}]}')
if [ $? -eq 0 ]; then
    pass "POST /pedidos"
    PEDIDO_ID=$(echo "$PEDIDO" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    echo "  Pedido criado: ID=$PEDIDO_ID"
else
    fail "POST /pedidos"
fi

# Listar pedidos
curl -sf "$BASE/pedidos" > /dev/null && pass "GET /pedidos" || fail "GET /pedidos"

# Consultar pedido
curl -sf "$BASE/pedidos/$PEDIDO_ID" > /dev/null && pass "GET /pedidos/$PEDIDO_ID" || fail "GET /pedidos/$PEDIDO_ID"

# Gerar fatura
FATURA=$(curl -sf -X POST "$BASE/pedidos/$PEDIDO_ID/fatura")
if [ $? -eq 0 ]; then
    pass "POST /pedidos/$PEDIDO_ID/fatura"
    FATURA_ID=$(echo "$FATURA" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    echo "  Fatura gerada: ID=$FATURA_ID"
else
    fail "POST /pedidos/$PEDIDO_ID/fatura"
fi

# Consultar fatura
curl -sf "$BASE/faturas/$FATURA_ID" > /dev/null && pass "GET /faturas/$FATURA_ID" || fail "GET /faturas/$FATURA_ID"

echo ""
echo "== Todos os testes passaram! =="
