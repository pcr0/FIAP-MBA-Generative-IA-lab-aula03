# ADR-001: Aprovação Automatizada de Pedidos de Alto Valor

## Status

Proposto

## Contexto

A distribuidora de TI que utiliza o Mini-ERP possui um processo manual de aprovação para pedidos acima de R$ 10.000. Hoje, a aprovação é feita via e-mail e planilha, leva em média 2 dias e não possui rastreabilidade — não há registro de quem analisou, quais critérios foram usados nem quando a decisão foi tomada. Isso gera atrasos na operação, risco de aprovações inconsistentes e impossibilidade de auditoria.

O laboratório da Aula 03 já possui um Mini-ERP funcional (FastAPI + SQLite) e um MCP Server (FastMCP + httpx) que expõe 10 tools para LLMs. O cenário é propício para demonstrar uma arquitetura agentic que resolva o problema real com rastreabilidade completa, aproveitando a infraestrutura existente.

Restrições obrigatórias no design:
- **LGPD:** dados de clientes (nome) não podem ser enviados a LLMs públicos sem anonimização.
- **Budget:** custo inferior a R$ 2,00 por execução do workflow de aprovação.
- **SLA:** aprovação humana em até 24 horas, com escalonamento automático em caso de timeout.
- **Auditoria:** toda decisão deve ser rastreável até o input original, com log de cada etapa.

## Decisão

Arquitetura agentic com **3 agentes LLM** operando em padrão **Fan-out / Fan-in (Parallel) + LLM-as-a-judge + HITL**:

1. **Agente Financeiro** — analisa risco de crédito, histórico de compras do cliente, concentração de valor. Trabalha em paralelo com o Agente Operacional. Modelo utilizado será o Claude Haiku, com prompt específico para análise financeira de pedidos.
2. **Agente Operacional** — analisa impacto no estoque, capacidade de entrega, estoque reservado por pedidos pendentes. Trabalha em paralelo com o Agente Financeiro. modelo utilizado será o Claude Haiku, com prompt específico para análise operacional de pedidos. 
3. **Agente Juiz (LLM-as-a-Judge)** — recebe os dois pareceres independentes, pondera e emite recomendação fundamentada (APROVAR ou REJEITAR). Modelo utilizado será o Claude Sonnet, com prompt específico para função de juiz avaliando múltiplos pareceres.

Após o Juiz, um **humano (HITL)** toma a decisão final com base na recomendação e nos pareceres. Se o humano não decidir em 24h, o processo é escalado automaticamente.

**Orquestração:** n8n (self-hosted via Podman). O workflow determinístico do n8n coordena todo o fluxo — verifica se o pedido excede R$ 10k, submete à aprovação via HTTP, dispara os dois agentes LLM em paralelo, coleta os pareceres, aciona o Juiz e gera um e-mail de notificação ao aprovador humano com a recomendação e justificativa. O HITL ocorre fora do workflow (o humano decide pela API REST do ERP). Essa separação mantém o workflow stateless e o SLA de 24h é controlável via mecanismo externo (cron ou alerta).

**Padrão MCP:** Facade — o MCP Server continua sendo a única interface entre LLMs e o ERP, agora com 3 tools adicionais.

**Modelo de dados:** normalizado em duas tabelas (`Aprovacao` + `LogAprovacao` 1-N) para escalabilidade do audit trail.

**Anonimização:** bidirecional no MCP Server — `_anonimizar()` substitui nomes reais por pseudônimos (hash SHA-256 truncado) antes de enviar ao LLM.

**Integração com o lab:** adiciona 8 endpoints REST ao ERP, 3 tools ao MCP Server, e estende o workflow n8n com novos nós (incluindo as chamadas a Claude Haiku/Claude Sonnet e envio de e-mail de notificação ao aprovador). Pedidos ≤ R$ 10.000 não são afetados — seguem o fluxo atual (CRIADO → FATURADO).

## Alternativas consideradas

- **Alternativa A: Pipeline Sequencial (Cadeia de Agentes)** — cada agente recebe o output do anterior (Financeiro → Operacional → Juiz). Descartada porque o contexto cresce a cada etapa (custo maior no Juiz), há risco de viés cascata (se o primeiro agente erra, os seguintes herdam o erro) e não aproveita paralelismo.

- **Alternativa B: Debate Adversarial com Juiz (Dialética)** — um Defensor constrói argumentos a favor, um Opositor constrói argumentos contra, o Juiz avalia. Descartada porque agentes instruídos a argumentar exaustivamente geram textos longos (risco de estourar budget de R$ 2/execução) e a polarização artificial pode não refletir a complexidade real do caso.

- **Alternativa C: Com modelo Opus único orquestrando todo o processo sem uso do n8n** — um único modelo Claude Opus gerenciaria todo o fluxo, delegando as análises financeira e operacional a sub agentes Haiku e depois elaborando a decisão final. Descartada porque embora o paralelismo viabilizado pelo n8n se mantenha, o consumo de tokens se tornaria bastante elevado, o que ultrapassaria o limite de custo por requisição.

- **Alternativa D: Manter o processo manual** — custo de inação: lead time de 2 dias por aprovação, sem rastreabilidade, sem auditoria, dependência de pessoas específicas, risco de aprovações inconsistentes. Inaceitável dado os requisitos de SLA e auditoria.

## Consequências

**Positivas:**
- Aprovação automatizada em minutos (análise dos agentes) + decisão humana informada, reduzindo o lead time de 2 dias para horas.
- Log completo auditável: cada processo gera 5+ entradas de log (SUBMISSAO → PARECER_FINANCEIRO → PARECER_OPERACIONAL → DECISAO_JUIZ → DECISAO_HUMANA), rastreável até o input original.
- Conformidade LGPD: dados pessoais nunca chegam ao LLM — anonimização bidirecional no MCP.

**Negativas / trade-offs aceitos:**
- Complexidade adicional: 3 novos modelos de dados, 8 novos endpoints, 3 novas tools MCP, nós novos no workflow n8n — mais código e configuração para manter.
- Dependência de LLM para análise: se o LLM estiver indisponível, o processo fica em ANALISE_EM_ANDAMENTO até retry manual.
- Mapas de anonimização em memória no MCP Server: não persistem entre restarts. Aceitável para contexto didático; em produção, seria necessário persistir em banco ou cache distribuído.

## NFRs críticos

- **Latência:** análise completa dos 3 agentes em < 30 segundos. Fallback: se qualquer agente não responder em 30s, o processo é marcado como ESCALADO para intervenção manual.
- **Custo:** máximo de R$ 2,00 por execução do workflow completo (soma de tokens dos 3 agentes). Medição: contabilizar tokens de input+output de cada chamada ao LLM. Contextos paralelos e independentes mantêm o custo previsível.
- **Disponibilidade:** o ERP continua funcional mesmo sem o MCP Server. Pedidos ≤ R$ 10k não dependem do fluxo de aprovação. Pedidos > R$ 10k ficam em PENDENTE_APROVACAO até que o processo agentic seja executado.
