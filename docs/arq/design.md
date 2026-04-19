# Design: Aprovação Automatizada de Pedidos de Alto Valor

## Diagrama de Arquitetura

```mermaid
graph TD
    subgraph ERP["Mini-ERP (FastAPI + SQLite)"]
        PEDIDO["POST /pedidos<br/>cria pedido"] -->|"total > R$10k"| STATUS_PEND["status = PENDENTE_APROVACAO"]
        PEDIDO -->|"total ≤ R$10k"| STATUS_CRIADO["status = CRIADO<br/>(fluxo atual)"]

        subgraph DADOS["Modelo de Dados"]
            TB_APROV["Aprovacao<br/>id, pedido_id, status,<br/>criado_em, atualizado_em"]
            TB_LOG["LogAprovacao<br/>id, aprovacao_id, etapa,<br/>agente, parecer,<br/>recomendacao, detalhes,<br/>criado_em"]
            TB_APROV -->|"1 — N"| TB_LOG
        end

        subgraph ENDPOINTS_APROV["Endpoints de Aprovação"]
            EP_CRIAR["POST /aprovacoes"]
            EP_CONSULTAR["GET /aprovacoes/{pedido_id}"]
            EP_PENDENTES["GET /aprovacoes/pendentes"]
            EP_PARECER["POST /aprovacoes/{id}/parecer"]
            EP_JUIZ["POST /aprovacoes/{id}/decisao-juiz"]
            EP_HUMANO["POST /aprovacoes/{id}/decisao-humana"]
            EP_ESCALAR["POST /aprovacoes/{id}/escalar"]
            EP_HISTORICO["GET /aprovacoes/historico?cliente="]
        end

        subgraph ENDPOINTS_CONSULTA["Endpoints de Consulta (Agentes)"]
            EP_PED_CLI["GET /pedidos?cliente={nome}"]
            EP_EST_RES["GET /estoque/{id}/reservado"]
            EP_NAO_FAT["GET /pedidos/nao-faturados/{produto_id}"]
        end
    end

    subgraph MCP["MCP Server (FastMCP + httpx)"]
        ANON["Anonimização Bidirecional<br/>_anonimizar() ↔ _desanonimizar()<br/>mapa em memória SHA-256"]

        subgraph TOOLS_FLUXO["Tools de Fluxo (5)"]
            T_SUB["submeter_para_aprovacao"]
            T_PAR["registrar_parecer"]
            T_CONS["consultar_aprovacao"]
            T_JUIZ["decidir_aprovacao_juiz"]
            T_HUM["decidir_aprovacao_humana"]
        end

        subgraph TOOLS_PESQ["Tools de Pesquisa (4)"]
            T_PED_CLI["consultar_pedidos_cliente"]
            T_HIST["consultar_historico_aprovacoes_cliente"]
            T_EST_RES["consultar_estoque_reservado"]
            T_NAO_FAT["consultar_pedidos_nao_faturados_produto"]
        end
    end

    subgraph AGENTES["Agentes LLM (Paralelo + Juiz)"]
        AG_FIN["Agente Financeiro<br/>Risco, crédito, histórico"]
        AG_OPS["Agente Operacional<br/>Estoque, entrega, reservas"]
        AG_JUIZ["Agente Juiz<br/>LLM-as-a-Judge<br/>Pondera pareceres"]
    end

    HUMANO["Humano (HITL)<br/>Decisão final em até 24h"]
    ESCALONAMENTO["Escalonamento<br/>Timeout 24h"]

    %% Fluxo principal
    STATUS_PEND --> T_SUB
    T_SUB --> ANON
    ANON -->|"dados anonimizados"| AG_FIN
    ANON -->|"dados anonimizados"| AG_OPS

    %% Agentes pesquisam
    AG_FIN -->|"pesquisa"| T_PED_CLI --> EP_PED_CLI
    AG_FIN -->|"pesquisa"| T_HIST --> EP_HISTORICO
    AG_OPS -->|"pesquisa"| T_EST_RES --> EP_EST_RES
    AG_OPS -->|"pesquisa"| T_NAO_FAT --> EP_NAO_FAT

    %% Pareceres
    AG_FIN -->|"parecer"| T_PAR --> EP_PARECER
    AG_OPS -->|"parecer"| T_PAR

    %% Juiz
    T_PAR -->|"ambos completos"| AG_JUIZ
    AG_JUIZ --> T_JUIZ --> EP_JUIZ

    %% HITL
    T_JUIZ -->|"AGUARDANDO_HUMANO"| HUMANO
    HUMANO -->|"aprova/rejeita"| T_HUM --> EP_HUMANO
    HUMANO -->|"timeout 24h"| ESCALONAMENTO --> EP_ESCALAR

    %% Endpoints de aprovação conectam ao modelo
    EP_CRIAR --> TB_APROV
    EP_PARECER --> TB_LOG
    EP_JUIZ --> TB_LOG
    EP_HUMANO --> TB_LOG
    EP_ESCALAR --> TB_LOG
```

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

### Tools de Fluxo de Aprovação

**Tool:** `submeter_para_aprovacao(pedido_id: int)`
**Propósito:** Inicia o processo de aprovação para um pedido > R$10k. Cria o registro de Aprovacao no ERP e retorna os dados do pedido anonimizados para os agentes analisarem.
**Input:** `{ pedido_id: int }`
**Output:** `{ aprovacao_id: int, pedido_id: int, status: str, pedido: { id, cliente_anonimizado, total, itens[] } }`
**Erros:** Pedido não encontrado (404); Pedido com total ≤ R$10.000 (400)

---

**Tool:** `registrar_parecer(pedido_id: int, agente: str, parecer: str, recomendacao: str)`
**Propósito:** Registra o parecer de um agente (financeiro ou operacional). Quando ambos estão registrados, transiciona o status para PARECERES_COMPLETOS. O parecer é desanonimizado antes de salvar no banco.
**Input:** `{ pedido_id: int, agente: "financeiro" | "operacional", parecer: str, recomendacao: "APROVAR" | "REJEITAR" }`
**Output:** `{ log_id: int, etapa: str, status_aprovacao: str }`
**Erros:** Aprovação não encontrada (404); Parecer duplicado para o mesmo agente (400)

---

**Tool:** `consultar_aprovacao(pedido_id: int)`
**Propósito:** Retorna o status completo de uma aprovação com todos os logs de cada etapa. Dados de cliente são anonimizados na resposta.
**Input:** `{ pedido_id: int }`
**Output:** `{ aprovacao: { id, pedido_id, status, criado_em, atualizado_em }, logs: [{ etapa, agente, parecer, recomendacao, criado_em }] }`
**Erros:** Aprovação não encontrada (404)

---

**Tool:** `decidir_aprovacao_juiz(pedido_id: int, decisao: str, justificativa: str)`
**Propósito:** Registra a decisão do Juiz (LLM-as-a-Judge) após avaliar os pareceres dos dois agentes. Transiciona para AGUARDANDO_HUMANO. A justificativa é desanonimizada antes de salvar.
**Input:** `{ pedido_id: int, decisao: "APROVAR" | "REJEITAR", justificativa: str }`
**Output:** `{ log_id: int, status_aprovacao: "AGUARDANDO_HUMANO" }`
**Erros:** Pareceres ainda incompletos (400); Aprovação não encontrada (404)

---

**Tool:** `decidir_aprovacao_humana(pedido_id: int, decisao: str, responsavel: str, comentario: str)`
**Propósito:** Registra a decisão final do humano (HITL). Transiciona a aprovação e o pedido para APROVADO ou REJEITADO. Não aplica anonimização — o humano trabalha com dados reais.
**Input:** `{ pedido_id: int, decisao: "APROVAR" | "REJEITAR", responsavel: str, comentario: str }`
**Output:** `{ log_id: int, status_aprovacao: "APROVADO" | "REJEITADO", status_pedido: str }`
**Erros:** Aprovação não está em AGUARDANDO_HUMANO (400); Aprovação não encontrada (404)

### Tools de Pesquisa para Agentes

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

---

**Tool:** `consultar_estoque_reservado(produto_id: int)`
**Propósito:** Calcula a quantidade de estoque reservada por pedidos ainda não faturados (status CRIADO, PENDENTE_APROVACAO, APROVADO). Usado pelo Agente Operacional para avaliar disponibilidade real.
**Input:** `{ produto_id: int }`
**Output:** `{ produto_id: int, estoque_total: int, estoque_reservado: int, estoque_disponivel: int }`
**Erros:** Produto não encontrado (404)

---

**Tool:** `consultar_pedidos_nao_faturados_produto(produto_id: int)`
**Propósito:** Lista pedidos não faturados que contêm um produto específico. Nomes de clientes são anonimizados. Usado pelo Agente Operacional para detalhar as reservas de estoque.
**Input:** `{ produto_id: int }`
**Output:** `{ pedidos: [{ id, cliente_anonimizado, total, status, quantidade_produto: int }] }`
**Erros:** Produto não encontrado (404)