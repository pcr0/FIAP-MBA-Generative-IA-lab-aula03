# Lab Aula 03 — MCP Server + n8n + Make

Laboratório prático da **Aula 03 do MBA FIAP** — Enterprise Architecture with Generative AI.

Você vai expor um Mini-ERP existente como **MCP Server** para LLMs (Claude Code/Desktop) e orquestrar o mesmo ERP por **n8n** (self-hosted) e **Make.com** (SaaS), comparando 3 padrões de integração: agente conversacional, workflow visual local e workflow visual na nuvem.

---

## Pré-requisitos

| Ferramenta | Para quê | Obrigatório? |
|------------|----------|--------------|
| Python 3.11+ | Rodar o ERP e o MCP Server | Sim |
| Mini-ERP didático | API REST que será orquestrada | Sim — incluso na pasta `erp/` |
| Claude Code **ou** Claude Desktop | Cliente MCP | Sim |
| Podman ou Docker | Rodar o n8n em container | Opcional (só para Demo n8n) |
| `cloudflared` | Expor a API local para o Make.com | Opcional (só para Demo Make) |
| Conta gratuita Make.com | Cenário SaaS | Opcional |
| API Key da Anthropic | Para os nós do Claude no n8n/Make | Opcional |

---

## Setup rápido

```bash
# 1. Instalar dependências do ERP
cd erp && pip install -r requirements.txt && cd ..

# 2. Subir o ERP (Terminal 1)
bash scripts/start_erp.sh

# 3. Validar que o ERP está no ar
bash scripts/test_erp_api.sh

# 4. Subir o MCP Server (Terminal 2) — cria venv e instala dependências automaticamente
bash scripts/start_mcp.sh

# 5. (Opcional) Se for usar n8n MCP, copie e preencha o .env
cp .env.example .env
# Edite .env com os tokens do n8n (instruções dentro do arquivo)
```

Pronto. Configure o MCP no Claude Desktop seguindo `docs/02_como_subir_o_mcp.md`.

---

## Estrutura

```text
lab-aula03/
├── README.md                    # Este arquivo (entrada principal)
├── .env.example                 # Template para tokens do n8n
├── .gitignore                   # Ignora .env, venv, etc.
├── .mcp.json                    # Config do MCP Server n8n no Claude Code
│
├── erp/                         # Mini-ERP Didático (FastAPI + SQLite)
│   ├── app/                     # Código-fonte (main, routes, models, schemas)
│   ├── data/                    # Banco SQLite (criado automaticamente)
│   └── requirements.txt
│
├── mcp_server/
│   ├── main.py                  # MCP Server (FastMCP + httpx, 10 tools)
│   └── requirements.txt
│
├── scripts/
│   ├── start_erp.sh             # Sobe o Mini-ERP
│   ├── start_mcp.sh             # Sobe o MCP Server (stdio)
│   ├── start_mcp_sse.sh         # Sobe o MCP Server em modo SSE/HTTP
│   ├── start_n8n.sh             # Sobe o n8n via Podman
│   ├── add_n8n_mcp.sh           # Registra n8n como MCP no Claude Code
│   ├── expose_api_cloudflare.sh # Tunnel Cloudflare para o Make
│   ├── test_erp_api.sh          # Testa endpoints do ERP via curl
│   └── test_mcp.sh              # Abre o MCP Inspector para teste interativo
│
├── artifacts/
│   ├── n8n/
│   │   └── workflow_erp.json    # Workflow n8n importável (10 nós, com LLM)
│   └── make/
│       └── blueprint_erp.json   # Blueprint Make importável
│
└── docs/                        # Documentação (siga em ordem)
    ├── 01_como_subir_o_erp.md
    ├── 02_como_subir_o_mcp.md
    ├── 03_como_testar_o_mcp.md
    ├── 04_demo_n8n.md
    ├── 05_demo_make.md
    ├── 06_roteiro_da_aula.md    # Para o professor
    │
    └── casos_didaticos/         # Estudo aprofundado (leitura complementar)
        ├── 05_caso_didatico_debug_com_claude_code.md
        ├── 06_caso_didatico_orquestracao_agente_vs_workflow.md
        ├── 07_caso_didatico_make_vs_n8n.md
        └── 08_arquitetura_mcp_server_erp.md
```

---

## Documentação (siga nesta ordem)

| # | Doc | O que ensina |
|---|-----|--------------|
| 1 | [docs/01_como_subir_o_erp.md](docs/01_como_subir_o_erp.md) | Subir o Mini-ERP local (FastAPI + SQLite) |
| 2 | [docs/02_como_subir_o_mcp.md](docs/02_como_subir_o_mcp.md) | Subir o MCP Server e configurar no Claude Desktop/Code |
| 3 | [docs/03_como_testar_o_mcp.md](docs/03_como_testar_o_mcp.md) | Testar as tools via MCP Inspector e via Claude |
| 4 | [docs/04_demo_n8n.md](docs/04_demo_n8n.md) | Workflow visual no n8n + chamada ao Claude Haiku + MCP nativo do n8n |
| 5 | [docs/05_demo_make.md](docs/05_demo_make.md) | Mesmo fluxo no Make.com (SaaS) com tunnel Cloudflare |
| 6 | [docs/06_roteiro_da_aula.md](docs/06_roteiro_da_aula.md) | Roteiro completo da demo ao vivo (para o professor) |

### Casos didáticos (leitura complementar)

Estudos aprofundados sobre decisões arquiteturais — não são pré-requisito para a demo, mas valem a leitura:

- [Debug com Claude Code](docs/casos_didaticos/05_caso_didatico_debug_com_claude_code.md) — usar o Claude Code como assistente para debugar o ERP/MCP
- [Orquestração: Agente vs Workflow](docs/casos_didaticos/06_caso_didatico_orquestracao_agente_vs_workflow.md) — quando usar LLM como orquestrador vs workflow determinístico
- [Make vs n8n](docs/casos_didaticos/07_caso_didatico_make_vs_n8n.md) — comparação SaaS vs self-hosted
- [Arquitetura MCP Server ↔ ERP](docs/casos_didaticos/08_arquitetura_mcp_server_erp.md) — design patterns do wrapper MCP

---

## MCP Tools disponíveis

O MCP Server expõe 10 tools sobre o Mini-ERP:

| Tool | Endpoint ERP | Descrição |
|------|--------------|-----------|
| `listar_produtos` | `GET /produtos` | Lista produtos ativos |
| `buscar_produto` | `GET /produtos/{id}` | Detalhes de um produto |
| `consultar_estoque` | `GET /estoque/{id}` | Quantidade em estoque |
| `criar_pedido` | `POST /pedidos` | Cria pedido com itens (valida estoque) |
| `listar_pedidos` | `GET /pedidos` | Lista pedidos recentes |
| `consultar_pedido` | `GET /pedidos/{id}` | Detalhes do pedido |
| `gerar_fatura_simulada` | `POST /pedidos/{id}/fatura` | Gera fatura |
| `consultar_fatura` | `GET /faturas/{id}` | Detalhes da fatura |
| `enviar_alerta` | `POST /alertas` | Registra alerta no ERP |
| `listar_alertas` | `GET /alertas` | Lista últimos 20 alertas |

---

## Configurar o MCP no Claude Desktop

Edite o `claude_desktop_config.json` (caminhos por OS):

| OS | Caminho |
|----|---------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "mini-erp": {
      "command": "/caminho/absoluto/para/lab-aula03/mcp_server/venv/bin/python",
      "args": ["/caminho/absoluto/para/lab-aula03/mcp_server/main.py"]
    }
  }
}
```

Reinicie o Claude Desktop. Detalhes completos em [docs/02_como_subir_o_mcp.md](docs/02_como_subir_o_mcp.md).

---

## Troubleshooting rápido

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| `start_erp.sh` falha com "Diretório não encontrado" | Pasta `erp/` não existe ou script rodado de outro diretório | Execute a partir da raiz do `lab-aula03/` |
| `start_mcp.sh` falha ao instalar deps | Python < 3.11 | Atualize Python ou use pyenv |
| Claude Desktop não vê as tools | Path absoluto errado no `claude_desktop_config.json` | Use caminhos absolutos (sem `~`) e reinicie o Claude Desktop |
| n8n não acessa o ERP | n8n roda em container, `localhost` não funciona | Use `host.containers.internal:8000` (Podman) ou `host.docker.internal:8000` (Docker) |
| Make retorna 403 | Tunnel Cloudflare caiu | Reexecute `bash scripts/expose_api_cloudflare.sh` e atualize a URL nos módulos |
| n8n MCP "Needs authentication" | Token não foi configurado em `.mcp.json` | Veja `.env.example` e seção 7 de `docs/04_demo_n8n.md` |

---

## Para o professor

Veja [docs/06_roteiro_da_aula.md](docs/06_roteiro_da_aula.md) — roteiro completo com 4 demos, falas sugeridas e fallbacks.

---

## Licença e atribuição

Material didático do MBA Enterprise Architecture with Generative AI — FIAP.
Professor: Francisco Carlos Junqueira Junior.
