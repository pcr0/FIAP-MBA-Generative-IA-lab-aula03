# Design: Aprovação Automatizada de Pedidos de Alto Valor

## Orquestração n8n

O workflow n8n (`artifacts/n8n/workflow_erp.json`) é o orquestrador determinístico de todo o fluxo. Ele coordena chamadas HTTP ao ERP e chamadas à API Anthropic, sem depender do MCP Server (que serve apenas LLMs interativos).

**Por que n8n?** Já é usado no lab, permite paralelismo nativo, oferece UI visual para debug, e mantém o workflow stateless — cada execução é independente.

**Fluxo de aprovação no n8n:**

```mermaid
graph TD
    START["Webhook POST /erp-pedido"] --> ESTOQUE["1. Consultar Estoque"]
    ESTOQUE --> IF_EST{"2. Estoque > 0?"}
    IF_EST -->|Não| ALERTA["Alerta Sem Estoque"]
    ALERTA --> CLAUDE_ALT["Claude: Sugerir Alternativas"]
    CLAUDE_ALT --> SUG["Sugestão Gerada"]

    IF_EST -->|Sim| PEDIDO["3. Criar Pedido"]
    PEDIDO --> IF_APROV{"4. Total > R$10k?"}

    IF_APROV -->|"≤ R$10k"| FATURA["5. Gerar Fatura"]
    FATURA --> CLAUDE_EMAIL["6. Claude: Email Confirmação"]
    CLAUDE_EMAIL --> SET_EMAIL["7. Email Gerado"]

    IF_APROV -->|"> R$10k"| SUBMETER["8. Submeter Aprovação"]
    SUBMETER --> FETCH_FIN["9a. MCP - consultar_pedidos_cliente + MCP - consultar_historico_aprovacoes_cliente"]
    SUBMETER --> FETCH_OPS["9b. MCP - consultar_estoque_reservado"]

    FETCH_FIN --> AG_FIN["10a. Claude: Agente Financeiro"]
    FETCH_OPS --> AG_OPS["10b. Claude: Agente Operacional"]

    AG_FIN --> REG_FIN["11a. Registrar Parecer Financeiro"]
    AG_OPS --> REG_OPS["11b. Registrar Parecer Operacional"]

    REG_FIN --> MERGE["12. Merge Pareceres"]
    REG_OPS --> MERGE

    MERGE --> CONSULTAR["13. Consultar Aprovação"]
    CONSULTAR --> AG_JUIZ["14. Claude: Agente Juiz"]
    AG_JUIZ --> REG_JUIZ["15. Registrar Decisão Juiz"]
    REG_JUIZ --> CLAUDE_NOTIF["16. Claude: Email Notificação"]
    CLAUDE_NOTIF --> SET_RESULT["17. Resultado Final"]
```

**HITL fora do workflow:** O humano recebe o e-mail de notificação com pedido_id, valor, recomendação e justificativa, e decide via API REST (`POST /aprovacoes/{id}/decisao-humana`). Se não decidir em 24h, um mecanismo externo (cron/alerta) aciona o endpoint de escalonamento.

**Agentes LLM via API Anthropic direta:** Os nós Claude do n8n chamam `api.anthropic.com/v1/messages` com `claude-haiku-4-5-20251001` (análises) e `claude-sonnet-4-5-20251001` (juiz). Não passam pelo MCP Server — os system prompts dos agentes são inline no workflow. A anonimização é feita no MCP Server chamado antes das ações dos LLM para que contexto seja fornecido de forma segura.

## Diagrama de Estados da Aprovação

```mermaid
stateDiagram-v2
    [*] --> ANALISE_EM_ANDAMENTO: POST /aprovacoes
    ANALISE_EM_ANDAMENTO --> PARECERES_COMPLETOS: Ambos pareceres registrados
    PARECERES_COMPLETOS --> AGUARDANDO_HUMANO: Juiz emite recomendação
    AGUARDANDO_HUMANO --> APROVADO: Humano aprova
    AGUARDANDO_HUMANO --> REJEITADO: Humano rejeita
    AGUARDANDO_HUMANO --> ESCALADO: Timeout 24h
    ESCALADO --> [*]
    APROVADO --> [*]
    REJEITADO --> [*]
```

## Modelo de Dados

```mermaid
erDiagram
    Pedido ||--o| Aprovacao : "tem"
    Aprovacao ||--o{ LogAprovacao : "registra"

    Pedido {
        int id PK
        string nome_cliente
        float total
        string status
        datetime criado_em
    }

    Aprovacao {
        int id PK
        int pedido_id FK
        string status
        datetime criado_em
        datetime atualizado_em
    }

    LogAprovacao {
        int id PK
        int aprovacao_id FK
        string etapa
        string agente
        text parecer
        string recomendacao
        text detalhes
        datetime criado_em
    }
```
## Novas MCP Tools

### Tools de Pesquisa para Agente Financeiro

**Tool:** `consultar_pedidos_cliente(nome_cliente: str)`
**Propósito:** Retorna todos os pedidos de um cliente. O agente envia o pseudônimo; a tool desanonimiza para consultar o ERP e reanonimiza a resposta. Usado pelo Agente Financeiro para avaliar histórico de compras.
**Input:** `{ nome_cliente: str }`
**Output:** `{ pedidos: [{ id, cliente_anonimizado, total, status, criado_em, itens[] }] }`
**Erros:** Nenhum pedido encontrado para o cliente (retorna lista vazia)

---

**Tool:** `consultar_historico_aprovacoes_cliente(nome_cliente: str)`
**Propósito:** Retorna o histórico de aprovações anteriores de um cliente. Desanonimiza o nome para consultar e reanonimiza a resposta. Usado pelo Agente Financeiro para avaliar padrão de aprovações.
**Input:** `{ nome_cliente: str }`
**Output:** `{ aprovacoes: [{ id, pedido_id, status, criado_em }] }`
**Erros:** Sem histórico de aprovações (retorna lista vazia)

### Tools de Pesquisa para Agente Operacional

**Tool:** `consultar_estoque_reservado(produto_id: int)`
**Propósito:** Calcula a quantidade de estoque reservada por pedidos ainda não faturados (status CRIADO, PENDENTE_APROVACAO, APROVADO). Usado pelo Agente Operacional para avaliar disponibilidade real.
**Input:** `{ produto_id: int }`
**Output:** `{ produto_id: int, estoque_total: int, estoque_reservado: int, estoque_disponivel: int }`
**Erros:** Produto não encontrado (404)

---