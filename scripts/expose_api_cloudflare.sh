#!/usr/bin/env bash
# Expõe http://localhost:8000 via TryCloudflare (gratuito, sem conta)
# Necessário: cloudflared instalado (brew install cloudflared)
set -e

PORT=${1:-8000}

echo ">> Expondo localhost:$PORT via Cloudflare Tunnel..."
echo "   A URL pública será exibida abaixo (algo como https://xxx.trycloudflare.com)"
echo "   Use essa URL no Make.com como base para os endpoints."
echo "   Ctrl+C para encerrar o tunnel."
echo ""

cloudflared tunnel --url http://localhost:$PORT
