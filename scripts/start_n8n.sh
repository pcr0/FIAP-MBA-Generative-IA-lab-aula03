#!/usr/bin/env bash
# Sobe o n8n via Podman na porta 5678
set -e

echo ">> Verificando Podman machine..."

# Verifica se a machine existe e está rodando; caso contrário, inicializa e/ou inicia
if ! podman machine info &>/dev/null; then
  echo "   Podman machine não encontrada. Inicializando..."
  podman machine init
fi

if ! podman machine inspect --format '{{.State}}' 2>/dev/null | grep -qi "running"; then
  echo "   Podman machine parada. Iniciando..."
  podman machine start
fi

echo ">> Podman machine rodando."
echo ""
mkdir -p ~/.n8n

echo ">> Iniciando n8n em http://localhost:5678 ..."
echo "   Dados persistidos em ~/.n8n (volume Podman)"
echo ""

podman run -it --rm \
  --name n8n-lab \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
