# Caso Didático — Make vs n8n: Mesmo Fluxo, Duas Ferramentas

## Contexto

Este documento compara a experiência prática de implementar o **mesmo fluxo de negócio** (consultar estoque → decidir → criar pedido → gerar fatura → email via LLM) em duas plataformas de automação: Make.com (SaaS) e n8n (self-hosted). Ambas consomem o mesmo Mini-ERP via HTTP.

O objetivo é dar ao arquiteto de soluções critérios concretos para decidir entre as plataformas, indo além da tabela teórica da Seção 5 do conteúdo programático.

---

## O fluxo implementado

```text
Consultar Estoque → Tem estoque? ──sim──→ Criar Pedido → Gerar Fatura → Claude: Email
                                  │
                                  └──não──→ Registrar Alerta → Claude: Sugestões
```

Ambas as implementações usam:

- **4 chamadas HTTP** ao Mini-ERP (GET estoque, POST pedido, POST fatura, POST alerta)
- **1 chamada HTTP** à API da Anthropic (Claude Haiku para gerar email ou sugestões)
- **1 decisão condicional** (estoque > 0)

---

## Comparação: Construção

### Tempo de setup

| Etapa | Make | n8n |
| ----- | ---- | --- |
| Instalar plataforma | 0 min (SaaS, browser) | ~5 min (Podman + start script) |
| Expor API local | ~2 min (Cloudflare tunnel) | 0 min (localhost direto) |
| Configurar credential | Inline no módulo HTTP | Credential centralizada (Header Auth) |
| Montar fluxo (7 módulos/nós) | ~15 min | ~15 min |
| **Total** | ~17 min | ~20 min |

### Experiência de construção

| Aspecto | Make | n8n |
| ------- | ---- | --- |
| **Adicionar módulo** | Clique no "+" → busca por tipo → configura | Clique no "+" → busca por tipo → configura |
| **Decisão condicional** | Router com filtros inline (intuitivo) | Nó IF separado (mais explícito) |
| **Referência entre módulos** | `{{N.campo}}` — por número do módulo | `{{ $json.campo }}` ou `{{ $('Nome') }}` — por nome |
| **Autocompletar campos** | Excelente — mostra schema após 1ª execução | Bom — mostra JSON do nó anterior |
| **Visualização** | Horizontal, módulos circulares | Horizontal, nós retangulares com rótulos |
| **Teste parcial** | Run once → todos executam em sequência | Test Workflow → executa nó a nó (clicável) |

### Veredito: construção

Empate técnico. Make é ligeiramente mais intuitivo para quem nunca usou automação. n8n é mais explícito e mostra mais detalhes do JSON, o que agrada desenvolvedores.

---

## Comparação: Debug

| Aspecto | Make | n8n |
| ------- | ---- | --- |
| **Visualizar output de cada passo** | Balão com número de operações → clique para expandir | Clique no nó → painel lateral com JSON completo |
| **Identificar qual rota foi ativada** | Rota ativa fica colorida, inativa fica cinza | Output do IF mostra `true` ou `false` |
| **Erro em módulo** | Módulo fica vermelho, mensagem de erro inline | Nó fica vermelho, erro no painel + log |
| **Histórico de execuções** | Sim (limitado no plano free) | Sim (completo, self-hosted) |
| **Re-executar com dados fixos** | Sim (replay) | Sim (pin data + re-execute) |
| **Error handling** | Error routes, break/continue, retry | Error workflow dedicado, retry, dead letter |
| **Claude Code como debugger** | Não (sem MCP) | Sim — Claude Code lê execuções via MCP n8n |

### Veredito: debug

n8n leva vantagem. O JSON é mais acessível, o histórico é completo (sem limites de plano), e o Claude Code pode diagnosticar execuções remotamente via MCP — recurso inexistente no Make.

Referência: ver `05_caso_didatico_debug_com_claude_code.md` para o caso de debug com Claude Code + n8n.

---

## Comparação: Manutenção e Operação

| Aspecto | Make | n8n |
| ------- | ---- | --- |
| **Atualização da plataforma** | Automática (SaaS) | Manual (docker pull ou npm update) |
| **Backup de workflows** | Export JSON manual ou API | Export JSON, git, ou API |
| **Versionamento** | Não nativo (plano Enterprise tem "versões") | Git-friendly (JSON exportável, CI/CD possível) |
| **Monitoramento** | Dashboard no Make.com | Self-hosted: precisa de observabilidade externa |
| **Escalabilidade** | Automática (mais ops = mais custo) | Manual (mais workers, mais containers) |
| **Disponibilidade** | SLA do Make (99.9%) | Depende da sua infra |

---

## Comparação: Custo

### Cenário do lab (baixo volume)

| Métrica | Make (Free) | n8n (Self-hosted) |
| ------- | ----------- | ----------------- |
| Custo da plataforma | R$ 0 | R$ 0 |
| Limite | 1.000 ops/mês, 2 cenários | Ilimitado |
| Operações por execução | 5-7 (cada módulo = 1 op) | N/A |
| Execuções possíveis/mês | ~140-200 | Ilimitadas |
| Custo LLM (Claude Haiku) | ~$0.001/execução | ~$0.001/execução |

### Cenário corporativo (alto volume: 10.000 execuções/mês)

| Métrica | Make (Teams) | n8n (Self-hosted) |
| ------- | ------------ | ----------------- |
| Custo da plataforma | ~$200/mês (10K ops × $0.02) | ~$50/mês (VM/container) |
| Custo LLM | ~$10/mês | ~$10/mês |
| **Total** | ~$210/mês | ~$60/mês |
| Custo por execução | ~$0.021 | ~$0.006 |

> **Ponto arquitetural:** Make é mais barato para iniciar (zero setup), mas mais caro em escala. n8n inverte: mais caro para iniciar (infra), mais barato em volume. O crossover point típico está em ~5.000 operações/mês.

---

## Comparação: Integração com LLM e Agentes

Esta é a **diferença mais relevante** para o contexto da disciplina.

| Capacidade | Make | n8n |
| ---------- | ---- | --- |
| **Chamar LLM via HTTP** | Sim (módulo HTTP genérico) | Sim (HTTP Request node) |
| **Módulo nativo Claude** | Não (tem OpenAI nativo) | Não (tem AI Agent node com LangChain) |
| **AI Agent node** | Não | Sim — agente autônomo com tools, memory, LangChain |
| **MCP Server** | Sim — MCP Toolboxes (expõe cenários selecionados) | Sim — Instance-level MCP (expõe workflows habilitados) |
| **Gestão via MCP** | Somente execução (free); visualizar/editar (pago) | Completa — search, execute, get_execution, create, update |
| **Claude Code integration** | Sim — executa cenários via MCP Toolboxes | Completa via MCP n8n (search, execute, get_execution, create) |
| **Webhook parametrizável** | Sim | Sim |
| **Controle de acesso MCP** | Granular — toolbox com keys por client | Por workflow habilitado |

### O que isso significa na prática

Com **n8n**, o Claude Code pode:

1. Buscar workflows (`search_workflows`)
2. Executar workflows com parâmetros (`execute_workflow`)
3. Ler resultados detalhados nó a nó (`get_execution`)
4. Criar e atualizar workflows programaticamente (`create_workflow_from_code`)
5. Combinar MCP mini-erp + MCP n8n em uma única orquestração

Com **Make** (via MCP Toolboxes), o Claude Code pode:

1. Executar cenários expostos no toolbox como tools
2. Receber o resultado da execução (output do cenário)

Mas **não** pode:

1. Listar ou buscar cenários dinamicamente
2. Ler resultados detalhados módulo a módulo
3. Criar ou editar cenários programaticamente
4. Executar cenários que demorem mais de 40 segundos (timeout do MCP Toolboxes)

> **Conclusão:** ambas as plataformas suportam MCP, mas com profundidades diferentes. n8n oferece **gestão programática completa** de workflows (buscar, executar, inspecionar, criar). Make oferece **execução controlada** de cenários com controle de acesso granular (toolbox + keys), mas sem visibilidade interna ou gestão programática. Para orquestração rica com agentes, n8n é mais capaz. Para expor automações SaaS como tools com governança de acesso, Make é competitivo.

---

## Matriz de Decisão (referência: Seção 5 do conteúdo slides)

| Critério | Peso | Make | n8n | Notas do lab |
| -------- | ---- | ---- | --- | ------------ |
| Interface intuitiva | Médio | 5 | 4 | Make mais visual para business users |
| Custo em escala | Alto | 2 | 5 | Make cobra por operação, escala cara |
| Self-hosting/LGPD | Alto | 1 | 5 | Make é SaaS-only, sem data sovereignty |
| Código custom | Médio | 2 | 5 | n8n permite JS/Python em qualquer nó |
| Integrações SaaS | Médio | 5 | 3 | Make tem 3000+ módulos prontos |
| Suporte a LLM/Agents | Alto | 3 | 5 | Ambos têm MCP; n8n mais profundo (AI Agent, LangChain, gestão programática) |
| Curva de aprendizado | Baixo | 5 | 3 | Make produtivo em horas |
| Enterprise features | Médio | 4 | 4 | Paridade, n8n com mais controle |
| Error handling | Médio | 3 | 4 | n8n mais granular (dead letter, error workflow) |
| Comunidade | Baixo | 4 | 4 | Públicos diferentes |

### Recomendação por perfil

| Perfil do time | Recomendação | Justificativa |
| -------------- | ------------ | ------------- |
| Business ops / marketing | **Make** | Intuitivo, integrações SaaS, sem código |
| Devs / SREs / architects | **n8n** | Controle, código, MCP, compliance |
| Equipe mista (negócio + tech) | **Ambos** | Make para automações simples, n8n para orquestração com LLM |
| Projeto com LLM/agents | **n8n** (Make viável) | n8n com gestão MCP completa; Make com MCP Toolboxes para execução |
| MVP rápido sem infra | **Make** | Zero setup, funciona no browser |

---

## Experiência prática: o que cada aluno deve levar

1. **Mesmo fluxo, duas ferramentas:** a lógica de negócio é a mesma — o que muda é a plataforma. APIs REST bem feitas servem qualquer consumidor.

2. **Decisão é arquitetural, não técnica:** ambas "funcionam". A escolha depende de quem vai operar, onde os dados precisam estar, quanto custa em escala, e se o workflow precisa ser orquestrado por agentes.

3. **MCP como nível de maturidade:** ambas expõem workflows como tools via MCP, mas com profundidades diferentes. n8n permite gestão programática completa (buscar, executar, inspecionar, criar). Make permite execução controlada com governança de acesso (toolbox + keys). A escolha depende do nível de integração que o agente precisa.

4. **Custo por operação vs custo fixo:** o modelo de pricing define a economia do workflow. Arquitetos precisam calcular o TCO antes de escolher.

5. **Não existe "melhor" — existe "mais adequado":** a resposta certa depende do contexto. A matriz de decisão é a ferramenta do arquiteto para justificar a escolha.

---

## Conexão com a disciplina

Este caso cobre diretamente os objetivos da Aula 03:

- **Objetivo 3:** Comparar e selecionar ferramentas de orquestração usando matriz de decisão estruturada
- **Atividade Avaliativa 1:** MCP Server e Orquestração de Agentes (entrega na Aula 4) — o aluno pode escolher Make, n8n, ou ambos, mas precisa justificar a escolha com critérios arquiteturais
- **Seção 5 do conteúdo:** Make vs n8n em 10 critérios — este caso aplica a teoria na prática do lab

### Ponte com aulas anteriores e posteriores

- **Aula 02 (RAG):** o conhecimento corporativo que alimenta prompts dos agentes vem de RAG. Neste lab, o prompt do Claude usa dados do ERP (pedido, fatura) — em produção, usaria também contexto de RAG.
- **Aula 04 (Avaliação):** como avaliar se o email gerado pelo Claude é bom o suficiente? LLM-as-a-Judge pode validar outputs de workflows híbridos.
- **Aula 05 (Segurança):** API keys no Make ficam no módulo HTTP. No n8n, ficam em credentials encriptadas. Em produção, ambas precisam de vault externo (HashiCorp Vault, AWS Secrets Manager).
