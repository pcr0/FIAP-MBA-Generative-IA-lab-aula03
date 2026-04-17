# Roteiro da Demo — Aula 03

Guia objetivo para o professor executar a demonstração ao vivo.

---

## Preparação (antes da aula)

- [ ] Testar ERP: `bash scripts/start_erp.sh` + `bash scripts/test_erp_api.sh`
- [ ] Testar MCP: `bash scripts/test_mcp.sh` (Inspector abre no browser)
- [ ] Configurar Claude Desktop com o MCP server
- [ ] Ter o n8n rodando: `bash scripts/start_n8n.sh`
- [ ] Se for demonstrar Make: `bash scripts/expose_api_cloudflare.sh`
- [ ] Apagar DB para reset dos dados: `rm erp/data/mini_erp.db` e reiniciar ERP

---

## Demo 1 — ERP e API REST (~5 min)

**Objetivo:** Mostrar o ERP que será consumido.

1. Abrir http://localhost:8000 no browser → tela do Mini-ERP
2. Abrir http://localhost:8000/docs → Swagger UI
3. Mostrar endpoints: produtos, estoque, pedidos, faturas
4. Executar um GET /produtos no Swagger → "Essa é a API que vamos expor via MCP"

> **Fala:** "Temos um ERP simples com API REST. Qualquer sistema pode consumir. Agora vamos expor isso para um LLM via MCP."

---

## Demo 2 — MCP Server + Claude (~15 min)

**Objetivo:** Mostrar MCP conectando LLM ao ERP.

### 2a. Mostrar o código do MCP Server (~3 min)

1. Abrir `mcp_server/main.py` no editor
2. Destacar:
   - Decorador `@mcp.tool()` — define uma tool
   - Docstring — vira a descrição que o LLM lê
   - `_erp_request()` — faz HTTP para o ERP
3. "Cada tool é um wrapper fino sobre a API REST"

### 2b. MCP Inspector (~5 min)

1. Rodar `bash scripts/test_mcp.sh` → Inspector no browser
2. Mostrar lista de tools disponíveis
3. Executar `listar_produtos` → mostrar resposta JSON
4. Executar `consultar_estoque(1)` → mostrar quantidade
5. "O Inspector é a ferramenta de debug do MCP"

### 2c. Claude Desktop com MCP (~7 min)

1. Abrir Claude Desktop (já configurado)
2. Mostrar o ícone de ferramentas → tools do Mini-ERP aparecem
3. Pedir ao Claude:
   - "Quais produtos temos no estoque?"
   - "Crie um pedido de 3 Teclados Mecânicos para o cliente FIAP MBA"
   - "Gere a fatura desse pedido"
   - "Mostre o resumo da fatura"
4. O Claude chama as tools automaticamente — mostrar no log

> **Fala:** "O LLM não tem acesso direto ao banco. Ele usa o MCP Server, que faz HTTP para o ERP. Camadas de abstração com controle."

---

## Demo 3 — n8n (~10 min)

**Objetivo:** Mostrar automação sem código usando o mesmo ERP.

1. Abrir http://localhost:5678 (n8n)
2. Importar `artifacts/n8n/workflow_erp.json`
3. Mostrar o workflow: Consultar Estoque → Criar Pedido → Gerar Fatura
4. Executar manualmente → mostrar resultados em cada nó
5. "O mesmo ERP, agora consumido por uma plataforma de automação"

> **Fala:** "MCP para LLMs, n8n para automações. A mesma API serve ambos. Isso é o poder de uma boa API REST."

---

## Demo 4 — Make (~10 min)

**Objetivo:** Mostrar o mesmo fluxo híbrido (determinístico + LLM) em plataforma SaaS e comparar com n8n.

**Pré-requisito:** tunnel Cloudflare ativo (`bash scripts/expose_api_cloudflare.sh`).

### 4a. Setup e tunnel (~2 min)

1. Mostrar o terminal com o Cloudflare Tunnel rodando → URL pública
2. Abrir `https://<tunnel>/health` no browser → "API acessível pela internet"

> **Fala:** "O Make roda na nuvem. Para ele acessar nossa API local, precisamos de um tunnel. Em produção, a API estaria em um endpoint público com auth."

### 4b. Cenário no Make (~5 min)

1. Abrir Make.com → cenário já montado (montar previamente, não ao vivo)
2. Mostrar a estrutura visual: **7 módulos** em duas rotas
3. Destacar:
   - **Módulo 1:** GET estoque (mesmo endpoint do n8n)
   - **Router:** decisão de estoque > 0 (equivalente ao IF do n8n)
   - **Rota 1:** Pedido → Fatura → Claude (email) — caminho feliz
   - **Rota 2:** Alerta → Claude (sugestões) — sem estoque
4. Clicar **Run once** → mostrar execução módulo a módulo
5. Expandir o output do módulo do Claude → mostrar email gerado

> **Fala:** "Mesmo fluxo, mesma API, mesma chamada ao Claude. O que muda é a plataforma: SaaS vs self-hosted."

### 4c. Comparação Make vs n8n (~3 min)

Projetar ou falar sobre as diferenças-chave:

| Aspecto | Make | n8n |
| ------- | ---- | --- |
| Onde roda | Nuvem (SaaS) | Local (container) |
| Acesso ao ERP | Tunnel necessário | localhost direto |
| Decisão | Router com filtros | Nó IF |
| API key do Claude | No módulo HTTP | Credential centralizada |
| MCP / Claude Code | Não suportado | Sim — orquestração via MCP |
| Custo | Por operação (~5 ops/execução) | Gratuito (self-hosted) |

> **Fala:** "Para automações SaaS rápidas, Make é imbatível. Mas se o workflow precisa ser orquestrado por um agente LLM via MCP, n8n é a escolha. A decisão é arquitetural — depende de quem opera, onde os dados estão, e se precisa de MCP."

Referência completa: `docs/07_caso_didatico_make_vs_n8n.md`

---

## Encerramento (~3 min)

Recapitular:

| Camada | Ferramenta | Protocolo |
|--------|-----------|-----------|
| ERP | FastAPI | REST/HTTP |
| LLM | Claude + MCP Server | MCP (stdio) |
| Automação local | n8n | REST/HTTP |
| Automação SaaS | Make | REST/HTTP (via tunnel) |

> **Fala:** "Uma API bem feita serve múltiplos consumidores. O MCP é mais uma camada — conecta LLMs com a mesma elegância."

---

## Fallbacks

- **ERP não sobe:** mostrar Swagger estático ou screenshots
- **MCP não conecta:** usar o Inspector (funciona standalone)
- **n8n falha:** demonstrar via curl no terminal
- **Make/Cloudflare falha:** pular, não é crítico
- **DB inconsistente:** apagar `mini_erp.db` e reiniciar ERP
