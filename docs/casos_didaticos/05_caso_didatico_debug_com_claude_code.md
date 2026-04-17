# Caso Didático — Debugging de Workflows com Claude Code

## Contexto

Este documento registra um caso real ocorrido durante a preparação do laboratório da Aula 03. Demonstra como o Claude Code pode ser usado como ferramenta de debugging e correção de artefatos de automação (n8n, scripts, configurações), mesmo quando os artefatos não são código tradicional.

## O cenário

Tínhamos um workflow n8n (`workflow_erp.json`) que orquestrava chamadas ao Mini-ERP: consultar estoque → criar pedido → gerar fatura. Ao longo da sessão, surgiram **5 problemas reais** que foram diagnosticados e corrigidos com Claude Code.

---

## Problema 1 — MCP Server não conectava

**Sintoma:** `claude mcp list` mostrava `mini-erp: ✗ Failed to connect`

**Causa raiz:** O comando `claude mcp add` foi registrado com `python` (do sistema), mas as dependências (`httpx`, `fastmcp`) só existiam no **venv** do projeto.

**Correção com Claude Code:**

```text
Prompt: "verifique seu acesso ao mcp do mini-erp"
```

O Claude Code diagnosticou o erro, removeu a configuração antiga e recriou com o caminho correto:

```bash
# Antes (errado)
claude mcp add mini-erp -- python /caminho/main.py

# Depois (correto)
claude mcp add mini-erp -- /caminho/mcp_server/venv/bin/python /caminho/main.py
```

**Lição arquitetural:** Em ambientes com múltiplos runtimes Python, o caminho do interpretador importa. O mesmo problema ocorre em produção com containers, virtualenvs e PATH mal configurado.

---

## Problema 2 — Volume do Podman falhava

**Sintoma:** `Error: statfs /Users/.../.n8n: no such file or directory`

**Causa raiz:** O diretório `~/.n8n` não existia. O Podman (diferente do Docker em alguns cenários) não cria o diretório do volume automaticamente.

**Correção com Claude Code:**

```text
Prompt: [colou o erro do terminal]
```

O Claude Code adicionou `mkdir -p ~/.n8n` ao script `start_n8n.sh` antes do `podman run`.

**Lição arquitetural:** Ao migrar Docker → Podman, comportamentos sutis mudam. Scripts de setup devem ser defensivos e idempotentes.

---

## Problema 3 — Nó IF rejeitava comparação de tipos

**Sintoma:** `Wrong type: '0' is a string but was expecting a number [condition 0, item 0]`

**Causa raiz:** No workflow JSON, o `rightValue` do nó IF estava como `"0"` (string) em vez de `0` (número), e o `typeValidation` era `strict`.

**Correção com Claude Code:**

```text
Prompt: [colou o erro do n8n]
```

Duas alterações no JSON:

```json
// Antes
"rightValue": "0",
"typeValidation": "strict"

// Depois
"rightValue": 0,
"typeValidation": "loose"
```

**Lição arquitetural:** Workflows no-code serializam configurações em JSON. Erros de tipo que seriam pegos por um compilador passam silenciosamente até a execução. Claude Code consegue analisar o JSON e identificar a inconsistência.

---

## Problema 4 — Criar Pedido usava produto hardcoded

**Sintoma:** Ao mudar o produto no nó "Consultar Estoque" para `produto_id: 2`, o nó "Criar Pedido" continuava criando pedido do produto 1.

**Causa raiz:** O body do nó "Criar Pedido" tinha `produto_id: 1` fixo em vez de referenciar o output do nó anterior.

**Correção com Claude Code:**

```text
Prompt: "no n8n eu editei o consultar estoque para o produto_id 2 e ele deu erro no criar pedido"
```

O Claude Code identificou o acoplamento e substituiu o valor fixo por expressão dinâmica:

```json
// Antes
"produto_id": 1

// Depois
"produto_id": {{ $('1. Consultar Estoque').item.json.produto_id }}
```

**Lição arquitetural:** Mesmo em ferramentas no-code, o princípio de não hardcodar valores se aplica. O Claude Code entende a sintaxe de expressões do n8n e consegue refatorar.

---

## Problema 5 — host.docker.internal não existe no Podman

**Sintoma:** Identificado proativamente pelo Claude Code ao migrar Docker → Podman.

**Causa raiz:** O Podman no macOS usa `host.containers.internal` em vez de `host.docker.internal`.

**Correção com Claude Code:** Substituiu todas as ocorrências no `workflow_erp.json` automaticamente.

**Lição arquitetural:** Ao migrar entre container runtimes, URLs internas mudam. Claude Code consegue fazer substituições em massa com contexto (sabe que o equivalente Podman é diferente).

---

## Padrão observado

Em todos os 5 casos, o fluxo foi o mesmo:

```text
1. Usuário encontra erro (terminal, n8n, ou comportamento inesperado)
2. Cola o erro ou descreve o sintoma no Claude Code
3. Claude Code lê os artefatos relevantes (JSON, script, config)
4. Diagnostica a causa raiz
5. Aplica a correção diretamente no arquivo
```

O Claude Code não está limitado a "código fonte" — ele opera sobre qualquer artefato textual: workflows JSON, scripts bash, configurações YAML, dockerfiles, etc.

## Comparação: Debug manual vs. com Claude Code

| Aspecto | Manual | Com Claude Code |
| ------- | ------ | --------------- |
| **Identificar causa raiz** | Ler docs, Stack Overflow, tentativa e erro | Diagnóstico direto a partir do erro + contexto do projeto |
| **Conhecimento cross-tool** | Precisa saber n8n + Podman + Python + MCP | Claude Code conhece todas simultaneamente |
| **Correção** | Editar JSON manualmente (propenso a erros) | Edição precisa com validação de contexto |
| **Efeitos colaterais** | Fácil esquecer de atualizar docs, outros arquivos | Claude Code atualiza artefatos relacionados proativamente |

---

## Exercício prático: Debug com Claude Code

### Arquivos disponíveis

| Arquivo | Descrição |
| ------- | --------- |
| `artifacts/n8n/workflow_erp.json` | Versão **com bugs** — usar para o exercício |
| `artifacts/n8n/workflow_erp_corrigido.json` | Versão **corrigida** — gabarito do professor |

### Roteiro

#### Parte 1 — Bug de tipo no nó IF

1. Importe `workflow_erp.json` no n8n
1. Execute o workflow — ele vai falhar no nó "2. Estoque > 0?"
1. Copie o erro e cole no Claude Code com o prompt:

```text
O workflow n8n em artifacts/n8n/workflow_erp.json deu o seguinte erro: [colar erro aqui]. Analise o JSON e corrija.
```

1. O Claude Code deve identificar e corrigir o bug do tipo string/número no nó IF
1. Reimporte e execute novamente — agora funciona

#### Parte 2 — Bug de acoplamento no nó Criar Pedido

1. Mude o produto no nó "Consultar Estoque" para `produto_id: 2` e execute
1. Observe que o pedido é criado para o produto 1 (errado!) — peça ao Claude Code para corrigir:

```text
O nó Criar Pedido está sempre criando pedido do produto 1, mesmo quando consulto o estoque do produto 2. Corrija o workflow.
```

1. Compare o resultado final com `workflow_erp_corrigido.json`

### Bugs intencionais no `workflow_erp.json`

| # | Nó afetado | Bug | Tipo |
| - | ---------- | --- | ---- |
| 1 | 2. Estoque > 0? | `rightValue` é string `"0"` em vez de número `0` | Tipo de dado |
| 2 | 2. Estoque > 0? | `typeValidation` é `strict` (rejeita coerção) | Configuração |
| 3 | 3. Criar Pedido | `produto_id` hardcoded como `1` em vez de dinâmico | Acoplamento |

---

## Conexão com a disciplina

Este caso demonstra três conceitos da Aula 03:

1. **Claude Code como ferramenta de operação** — não apenas para escrever código, mas para operar e debugar infraestrutura de automação
2. **MCP como ponte** — o mesmo ERP é consumido por HTTP (n8n), por MCP (Claude Code), e por API direta — três interfaces, mesma fonte de dados
3. **Orquestração híbrida** — o workflow final combina etapas determinísticas (HTTP) com etapas generativas (Claude API), mostrando o padrão arquitetural que diferencia automação tradicional de automação com IA
