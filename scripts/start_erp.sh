#!/usr/bin/env bash
# Sobe o Mini-ERP Didático na porta 8000
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ERP_DIR="${ERP_DIR:-$SCRIPT_DIR/../erp}"

if [ ! -d "$ERP_DIR/app" ]; then
    echo "ERRO: Diretório do ERP não encontrado em: $ERP_DIR"
    echo "Execute a partir da raiz do lab-aula03."
    exit 1
fi

cd "$ERP_DIR"

# Ativa venv se existir
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo ">> Iniciando Mini-ERP em http://localhost:8000 ..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
