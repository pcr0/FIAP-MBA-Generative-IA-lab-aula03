# Caso Didático — Orquestração por Agente vs. Workflow

## Contexto

Este documento registra uma demonstração real do laboratório da Aula 03, comparando dois modos de orquestrar o mesmo processo de negócio (consultar estoque → criar pedido → gerar fatura) usando o mesmo ERP e os mesmos endpoints.

## O cenário

O professor pede: **"Rode a automação para um pedido de teclado."**

Dois caminhos possíveis:

- **Caminho A — Workflow (n8n):** o `produto_id` precisa estar hardcoded na URL do nó. Para mudar o produto, o operador edita o workflow.
- **Caminho B — Agente (Claude Code + MCP):** o LLM recebe "teclado", descobre o ID consultando o catálogo, verifica estoque e executa o fluxo completo.

---

## Caminho A — n8n (workflow determinístico)

O workflow tem o produto fixo na URL:

```text
GET http://host.containers.internal:8000/estoque/2   ← hardcoded
```

Para trocar o produto, o operador precisa:

1. Abrir o n8n no browser
2. Editar o nó "Consultar Estoque"
3. Alterar a URL para `/estoque/3`
4. Executar novamente

**Resultado:** funciona, mas exige intervenção manual a cada mudança.

## Caminho B — Claude Code + MCP (agente)

O prompt do usuário:

```text
Rode a automação para um pedido de teclado.
```

O que o Claude Code faz internamente:

```text
1. listar_produtos()         → encontra "Teclado Mecânico" = ID 3
2. consultar_estoque(3)      → 28 unidades disponíveis
3. criar_pedido("Demo", [{"produto_id": 3, "quantidade": 1}])
                              → Pedido #18, R$ 350,00
4. gerar_fatura_simulada(18) → Fatura #17, R$ 350,00, GERADA
```

**Resultado:** o LLM resolveu "teclado" → `produto_id: 3` sem nenhum hardcode.

---

## Execução real registrada

### Via Claude Code (MCP mini-erp)

```text
Prompt: "rode a automação para um pedido de teclado"

1. listar_produtos → "Teclado Mecânico" = ID 3, R$ 350,00
2. consultar_estoque(3) → 28 unidades
3. criar_pedido("Demo Claude Code - Aula 03", [{"produto_id": 3, "quantidade": 1}])
   → Pedido #18 | R$ 350,00 | CRIADO
4. gerar_fatura_simulada(18)
   → Fatura #17 | R$ 350,00 | GERADA
```

### Via n8n (executado pelo Claude Code via MCP n8n)

Na mesma sessão, o Claude Code também executou o workflow do n8n remotamente via MCP:

```text
1. search_workflows → "Mini-ERP — Orquestração Híbrida" = ID ZPNHJbzy0Iy7Ujme
2. execute_workflow(ZPNHJbzy0Iy7Ujme) → Execution #50, status: success
3. get_execution(50) → resultado nó a nó, incluindo email gerado pelo Claude Haiku
```

---

## Comparação detalhada

| Aspecto | n8n (workflow) | Claude Code (agente) |
| ------- | -------------- | -------------------- |
| **Input** | `produto_id: 2` (fixo na URL) | "teclado" (linguagem natural) |
| **Resolução de entidade** | Não tem — operador fornece o ID | LLM consulta catálogo e resolve |
| **Decisão de estoque** | Nó IF (> 0, determinístico) | LLM verifica e decide contextualmente |
| **Flexibilidade** | Editar workflow para mudar produto | Adapta em tempo real pelo prompt |
| **Previsibilidade** | 100% determinístico | Variável (LLM pode interpretar diferente) |
| **Auditoria** | Log nó a nó no n8n | Log de tool calls no Claude Code |
| **Velocidade** | ~2s (HTTP direto) | ~5s (raciocínio + múltiplas chamadas) |
| **Custo** | Zero (sem LLM nos nós básicos) | Tokens consumidos a cada execução |
| **Erro humano** | Pode errar o ID ao editar | Pode interpretar "teclado" errado |

## Não-determinismo do LLM

O workflow do n8n inclui um nó que chama o Claude Haiku para gerar email de confirmação. Em 3 execuções consecutivas com os mesmos dados de entrada, o email gerado foi diferente:

| Execução | Abertura | Fechamento |
| -------- | -------- | ---------- |
| #48 | "Confirmamos o recebimento de sua solicitação" | "[Sua Empresa]" |
| #49 | "Confirmamos o recebimento de seu pedido com sucesso" | "[Seu Nome/Empresa]" |
| #50 | "Confirmamos o recebimento de seu pedido com sucesso!" | "Equipe de Atendimento" |

**Ponto arquitetural:** as etapas determinísticas (estoque, pedido, fatura) produzem resultados idênticos. A etapa generativa (email) varia. O arquiteto deve decidir **onde no fluxo a variabilidade é aceitável**.

---

## Quando usar cada abordagem

| Cenário | Recomendação | Por quê |
| ------- | ------------ | ------- |
| Processo fixo e repetitivo (ex: faturamento noturno) | **Workflow (n8n)** | Previsível, auditável, sem custo de tokens |
| Interação ad-hoc com dados (ex: "quanto vendemos de teclado?") | **Agente (Claude Code)** | Flexível, resolve ambiguidade, linguagem natural |
| Processo fixo com etapa criativa (ex: fatura + email personalizado) | **Híbrido (n8n + LLM)** | Determinístico onde importa, generativo onde agrega |
| Operação/debug de automações (ex: "por que o workflow falhou?") | **Agente (Claude Code)** | Lê logs, diagnostica, corrige artefatos |

---

## Arquitetura demonstrada

```text
┌─────────────────────────────────────────────────────────┐
│                    Claude Code (Agente)                  │
│         "rode a automação para um pedido de teclado"     │
│                                                         │
│  Raciocínio:                                            │
│  1. "teclado" → preciso descobrir o ID → listar_produtos│
│  2. ID 3, preço 350 → verificar estoque → 28 unidades  │
│  3. Tem estoque → criar_pedido                          │
│  4. Pedido criado → gerar_fatura_simulada               │
└────────┬──────────────────────────────┬─────────────────┘
         │ MCP (stdio)                  │ MCP (HTTP)
         ▼                              ▼
┌─────────────────┐           ┌──────────────────┐
│  MCP mini-erp   │           │   MCP n8n-erp    │
│                 │           │                  │
│ · listar_produtos│          │ · search_workflows│
│ · consultar_estoque│        │ · execute_workflow│
│ · criar_pedido  │           │ · get_execution  │
│ · gerar_fatura  │           │ · create_workflow │
│ · enviar_alerta │           │ · update_workflow │
└────────┬────────┘           └────────┬─────────┘
         │ HTTP                        │ HTTP
         ▼                             ▼
┌─────────────────┐           ┌──────────────────┐
│   Mini-ERP      │           │      n8n         │
│  (FastAPI)      │◄──────────│  (workflows)     │
│  :8000          │  HTTP     │  :5678           │
└─────────────────┘           └──────────────────┘
```

---

## Demonstração avançada: Dois MCPs + Webhook parametrizado

Após alterar o workflow do n8n para usar **webhook trigger** (em vez de trigger manual), o fluxo completo ficou parametrizável. O Claude Code agora pode:

1. Resolver linguagem natural via MCP mini-erp
2. Passar os parâmetros resolvidos para o n8n via MCP n8n

### Alteração no workflow

O trigger manual foi substituído por webhook, e todas as referências ao produto passaram a ser dinâmicas:

| Nó | Antes (hardcoded) | Depois (dinâmico) |
| -- | ------------------ | ----------------- |
| Start | `manualTrigger` | `webhook` (POST, path: `erp-pedido`) |
| Consultar Estoque | `/estoque/2` | `/estoque/{{ $json.body.produto_id }}` |
| Criar Pedido | `produto_id: 1`, `nome_cliente` fixo | `{{ $('Start').item.json.body.* }}` |

### Execução real

```text
Prompt: "crie um pedido via mcp n8n de um teclado"
```

O Claude Code executou:

```text
1. MCP mini-erp → listar_produtos → "Teclado Mecânico" = ID 3, R$ 350
2. MCP n8n → execute_workflow com parâmetros:
   {
     "type": "webhook",
     "webhookData": {
       "method": "POST",
       "body": {
         "produto_id": 3,
         "quantidade": 1,
         "nome_cliente": "Demo Teclado via MCP"
       }
     }
   }
```

Resultado nó a nó:

| Nó | Output |
| -- | ------ |
| 1. Consultar Estoque | Teclado Mecânico (ID 3) — 26 unidades |
| 3. Criar Pedido | Pedido #21 — Cliente: Demo Teclado via MCP — R$ 350,00 |
| 4. Gerar Fatura | Fatura #20 — R$ 350,00 — GERADA |

### O que isso prova

O workflow do n8n agora é **parametrizável** — não importa qual produto, o Claude Code resolve pelo nome e injeta o ID correto. São **3 camadas** trabalhando juntas:

```text
┌──────────────────────────────────────────────────────┐
│           Camada 1: Linguagem Natural                │
│  "crie um pedido de teclado"                         │
│           ↓ Claude Code (agente)                     │
├──────────────────────────────────────────────────────┤
│           Camada 2: Resolução de Entidade            │
│  MCP mini-erp: "teclado" → produto_id: 3            │
│           ↓ parâmetros resolvidos                    │
├──────────────────────────────────────────────────────┤
│           Camada 3: Execução Determinística          │
│  MCP n8n: execute_workflow(webhook, body={id:3,...}) │
│           ↓ n8n: Estoque → Pedido → Fatura          │
└──────────────────────────────────────────────────────┘
```

### Como reproduzir na aula

**Pré-requisitos:** ERP rodando (:8000), n8n rodando (:5678), ambos MCPs configurados no Claude Code.

1. Importe `artifacts/n8n/workflow_erp_corrigido.json` no n8n
2. Configure a credential "Anthropic API Key" nos nós do Claude (se quiser os nós de email/sugestão)
3. Habilite o workflow no Instance-level MCP
4. No Claude Code, peça: `Crie um pedido via n8n de 2 monitores para o cliente João Silva.`
5. O Claude Code deve:
   - Consultar o catálogo via MCP mini-erp → Monitor 24pol = ID 4
   - Executar o workflow via MCP n8n com `produto_id: 4, quantidade: 2, nome_cliente: "João Silva"`
   - Retornar o resultado da execução

6. Varie os pedidos para demonstrar a flexibilidade:

```text
Faça um pedido de 3 mouses para a empresa FIAP.
Peça um notebook para Maria.
```

---

## Conexão com a disciplina

Este caso demonstra conceitos centrais da Aula 03:

1. **MCP como camada universal** — o mesmo ERP é consumido por agente (Claude Code) e por workflow (n8n) através de MCPs diferentes, cada um otimizado para seu caso de uso
2. **Orquestração determinística vs. por agente** — trade-offs claros entre previsibilidade (workflow) e flexibilidade (LLM)
3. **Onde colocar o LLM no fluxo** — o LLM não precisa estar em todo lugar; ele agrega valor onde há ambiguidade (resolver "teclado" → ID 3) ou criatividade (gerar email), não onde há regra fixa (verificar estoque > 0)
4. **Claude Code como meta-orquestrador** — capaz de executar workflows do n8n remotamente via MCP, combinando ambas as abordagens em uma única sessão
