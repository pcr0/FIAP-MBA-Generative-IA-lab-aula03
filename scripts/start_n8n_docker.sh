#!/usr/bin/env bash
# Sobe o n8n via Docker na porta 5678

mkdir -p .n8n

echo ">> Iniciando n8n em http://localhost:5678 ..."
echo "   Dados persistidos em .n8n (volume Docker)"
echo ""

docker run -it --rm \
  --name n8n-lab \
  --add-host=host.docker.internal:host-gateway \
  -p 5678:5678 \
  -v .n8n:/home/node/.n8n \
  n8nio/n8n
