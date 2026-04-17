# Demo Make.com — Orquestração Híbrida (Workflow + LLM)

## O que é

Cenário visual no Make.com que demonstra o mesmo fluxo híbrido do n8n: etapas determinísticas (consultar estoque, criar pedido, gerar fatura) com decisão condicional (Router) e chamada a LLM (Claude Haiku gera email de confirmação ou sugere alternativas). Consome o mesmo Mini-ERP via HTTP através de tunnel Cloudflare.

## Diferença do n8n

O Make é **SaaS** — roda na nuvem da Make.com. Para acessar `localhost:8000`, precisamos expor a API via tunnel. O n8n roda local em container Podman.

## Pré-requisitos

- ERP rodando em `http://localhost:8000`
- `cloudflared` instalado (`brew install cloudflared`)
- Conta gratuita no Make.com (2 cenários, 1000 ops/mês)
- API key da Anthropic (para o módulo que chama o Claude)

## 1. Expor a API com Cloudflare Tunnel

```bash
bash scripts/expose_api_cloudflare.sh
```

O script usa TryCloudflare (gratuito, sem conta). Ele vai mostrar uma URL tipo:

```
https://abc-xyz-123.trycloudflare.com
```

Teste: abra `https://<tunnel>/health` no browser.

> **A URL muda a cada execução.** Copie e use como `<TUNNEL>` em todos os módulos do Make.

---

## 2. Criar conta e importar o cenário no Make.com

### 2.1 Criar conta gratuita

1. Acesse https://www.make.com e clique em **Get started free**
2. Cadastre-se com email ou conta Google/GitHub
3. Na tela de onboarding, pule as perguntas (Skip) — elas não afetam a funcionalidade
4. Você cai no dashboard. O plano free inclui **2 cenários ativos** e **1.000 operações/mês**

### 2.2 Importar o blueprint

O cenário completo está em `artifacts/make/blueprint_erp.json`. Para importar:

1. No menu lateral, clique em **Scenarios**
2. Clique em **+ Create a new scenario**
3. Na tela do editor visual (área vazia com "+"), clique no **"..."** (menu de 3 pontos, canto inferior da tela)
4. Selecione **Import Blueprint**
5. Selecione o arquivo `artifacts/make/blueprint_erp.json`
6. O cenário aparece com 7 módulos já conectados em duas rotas

### 2.3 Configurar a URL do tunnel (obrigatório)

O blueprint vem com `TUNNEL_URL_AQUI` como placeholder. Substitua pela URL real do seu tunnel:

1. Abra cada módulo HTTP que chama o ERP (módulos 1, 3, 4 e 6) — são os que **não** chamam `api.anthropic.com`
2. No campo **URL**, substitua `TUNNEL_URL_AQUI` pela URL do seu tunnel (ex: `abc-xyz-123.trycloudflare.com`)
3. Clique **OK** em cada módulo

> **Atenção:** são 4 módulos para atualizar. Os módulos 5 e 7 (Claude API) não precisam de alteração na URL.

### 2.4 Configurar a API key da Anthropic (obrigatório)

O blueprint vem com `SUA_API_KEY_AQUI` como placeholder nos módulos do Claude:

1. Abra o **Módulo 5** (Claude: Email) → em **Headers**, encontre `x-api-key` → substitua `SUA_API_KEY_AQUI` pela sua chave (`sk-ant-...`)
2. Repita para o **Módulo 7** (Claude: Sugestões)
3. Clique **OK** em cada módulo

> **Segurança:** a API key fica no header do módulo HTTP. Diferente do n8n (que usa Credentials centralizadas), no Make a key fica inline. Para ambientes reais, use **Scenario Variables** do Make.

### 2.5 Verificar e renomear

1. Clique no nome "Mini-ERP — Orquestração Híbrida (Workflow + LLM)" no topo para confirmar que importou corretamente
2. Verifique visualmente que o cenário tem a estrutura esperada (ver diagrama abaixo)

---

### Visão geral do fluxo

```text
                                                    ┌── Caminho feliz ──────────────────────────────────────────────────┐
Módulo 1 (GET estoque) → Router ──── estoque > 0 ──→ Módulo 3 (POST pedido) → Módulo 4 (POST fatura) → Módulo 5 (Claude: Email)
                                  │
                                  └── estoque = 0 ──→ Módulo 6 (POST alerta) → Módulo 7 (Claude: Sugestões)
```

Este fluxo é equivalente ao workflow do n8n documentado em `04_demo_n8n.md`.

---

### Módulo 1 — Consultar Estoque

- Tipo: **HTTP → Make a request**
- URL: `https://<TUNNEL>/estoque/1`
- Método: **GET**
- Parse response: **Yes**

> O módulo retorna JSON com `produto_id`, `nome_produto`, `quantidade_disponivel`.

---

### Módulo 2 — Router (decisão de estoque)

- Tipo: **Flow Control → Router**

O Router divide o fluxo em duas rotas (branches). Arraste do Módulo 1 para o Router.

**Rota 1 — Caminho feliz (há estoque):**
- Label: `Com estoque`
- Filter condition: `{{1.data.quantidade_disponivel}}` **Greater than** `0`

**Rota 2 — Sem estoque:**
- Label: `Sem estoque`
- Filter condition: `{{1.data.quantidade_disponivel}}` **Equal to** `0`

> **Equivalente no n8n:** nó IF com condição `estoque > 0`.
>
> **Diferença prática:** no Make, o Router é um módulo visual com rotas nomeadas e filtros inline. No n8n, o IF é um nó separado com true/false outputs. O Router do Make permite mais de 2 rotas sem encadear múltiplos IFs.

---

### Rota 1 — Caminho Feliz (com estoque)

#### Módulo 3 — Criar Pedido

- Tipo: **HTTP → Make a request**
- URL: `https://<TUNNEL>/pedidos`
- Método: **POST**
- Body type: **Raw (application/json)**
- Request content:
```json
{
  "nome_cliente": "Demo Make - Aula 03",
  "itens": [
    {"produto_id": 1, "quantidade": 1}
  ]
}
```
- Headers: `Content-Type: application/json`
- Parse response: **Yes**

#### Módulo 4 — Gerar Fatura

- Tipo: **HTTP → Make a request**
- URL: `https://<TUNNEL>/pedidos/{{3.data.id}}/fatura`
  - `{{3.data.id}}` referencia o ID do pedido retornado pelo Módulo 3
- Método: **POST**
- Parse response: **Yes**

#### Módulo 5 — Claude: Gerar Email de Confirmação

- Tipo: **HTTP → Make a request**
- URL: `https://api.anthropic.com/v1/messages`
- Método: **POST**
- Headers:
  - `x-api-key`: *sua chave Anthropic* (`sk-ant-...`)
  - `anthropic-version`: `2023-06-01`
  - `Content-Type`: `application/json`
- Body type: **Raw (application/json)**
- Request content:
```json
{
  "model": "claude-haiku-4-5-20251001",
  "max_tokens": 512,
  "messages": [
    {
      "role": "user",
      "content": "Gere um email profissional de confirmação de pedido para o cliente. Dados: Pedido #{{3.data.id}}, Produto: {{1.data.nome_produto}}, Valor: R$ {{4.data.valor_total}}, Status da fatura: {{4.data.status}}. O email deve ser cordial e incluir um resumo do pedido."
    }
  ]
}
```
- Parse response: **Yes**

> **Equivalente no n8n:** nó HTTP Request chamando a mesma API do Claude.
>
> **Ponto didático:** tanto no Make quanto no n8n, o Claude é consumido via HTTP REST — não há módulo nativo "Claude" no Make (diferente do OpenAI, que tem módulo dedicado). Isso ilustra que qualquer API pode ser consumida via módulo HTTP genérico.

---

### Rota 2 — Sem Estoque

#### Módulo 6 — Registrar Alerta

- Tipo: **HTTP → Make a request**
- URL: `https://<TUNNEL>/alertas`
- Método: **POST**
- Body type: **Raw (application/json)**
- Request content:
```json
{
  "tipo": "estoque_zerado",
  "mensagem": "Produto {{1.data.nome_produto}} (ID {{1.data.produto_id}}) sem estoque. Cliente Demo Make tentou comprar.",
  "dados": {
    "produto_id": {{1.data.produto_id}},
    "produto_nome": "{{1.data.nome_produto}}"
  }
}
```
- Headers: `Content-Type: application/json`
- Parse response: **Yes**

#### Módulo 7 — Claude: Sugerir Alternativas

- Tipo: **HTTP → Make a request**
- URL: `https://api.anthropic.com/v1/messages`
- Método: **POST**
- Headers:
  - `x-api-key`: *sua chave Anthropic* (`sk-ant-...`)
  - `anthropic-version`: `2023-06-01`
  - `Content-Type`: `application/json`
- Body type: **Raw (application/json)**
- Request content:
```json
{
  "model": "claude-haiku-4-5-20251001",
  "max_tokens": 512,
  "messages": [
    {
      "role": "user",
      "content": "O produto '{{1.data.nome_produto}}' está sem estoque. Sugira alternativas de forma empática para o cliente. Mencione que registramos um alerta e que ele será notificado quando houver reposição. Seja cordial e profissional."
    }
  ]
}
```
- Parse response: **Yes**

> **Equivalente no n8n:** nó HTTP Request no caminho `false` do IF, com prompt similar.

---

## 3. Executar

1. Clique **Run once** (canto inferior esquerdo)
2. Cada módulo mostra um balão com o número de operações — clique para ver input/output
3. O Router mostra qual rota foi ativada (a outra aparece cinza)
4. No caminho feliz, o Módulo 5 retorna o email gerado pelo Claude
5. Para testar o caminho sem estoque: altere o `produto_id` no Módulo 1 para um produto com estoque zerado, ou consuma todo o estoque via API antes de executar

### Como forçar o caminho sem estoque

```bash
# Verificar qual produto tem menos estoque
curl https://<TUNNEL>/estoque/1
curl https://<TUNNEL>/estoque/2
curl https://<TUNNEL>/estoque/3
curl https://<TUNNEL>/estoque/4

# Criar pedidos até zerar o estoque do produto escolhido
curl -X POST https://<TUNNEL>/pedidos \
  -H "Content-Type: application/json" \
  -d '{"nome_cliente": "Esgotando Estoque", "itens": [{"produto_id": 1, "quantidade": 50}]}'
```

---

## 4. Referência entre módulos no Make

No Make, a sintaxe para referenciar dados de módulos anteriores é `{{N.campo}}`:

| Referência | Significado |
|-----------|-------------|
| `{{1.data.quantidade_disponivel}}` | Campo `quantidade_disponivel` do response do Módulo 1 |
| `{{3.data.id}}` | Campo `id` do response do Módulo 3 (pedido criado) |
| `{{4.data.valor_total}}` | Campo `valor_total` do response do Módulo 4 (fatura) |

> **Diferença do n8n:** no n8n, a referência é `{{ $json.campo }}` (nó anterior) ou `{{ $('NomeDoNó').item.json.campo }}` (nó específico). No Make, é sempre pelo número do módulo.

---

## 5. Pontos para destacar na aula

### Comparação direta com o n8n

| Aspecto | Make | n8n |
|---------|------|-----|
| **Decisão condicional** | Router com filtros inline | Nó IF separado |
| **Chamada ao Claude** | HTTP module genérico | HTTP Request node (mesmo padrão) |
| **Referência entre nós** | `{{N.campo}}` (por número) | `{{ $json.campo }}` ou `{{ $('Nome') }}` |
| **Secrets (API key)** | Header no módulo HTTP | Credential centralizada |
| **Onde roda** | Nuvem Make.com | Local (Podman container) |
| **Acesso ao ERP** | Precisa de tunnel | HTTP direto (localhost) |
| **Debug** | Balões por módulo | Painel por nó com JSON |

### Pontos arquiteturais

- **SaaS vs self-hosted:** Make roda na nuvem — zero infra, mas depende de internet e tunnel para APIs locais
- **Custo:** cada módulo executado conta como 1 operação. O cenário completo (caminho feliz) consome 5 operações por execução. No plano free (1000 ops/mês), são ~200 execuções
- **Segurança:** a API key do Claude fica exposta no módulo HTTP (não há credential vault como no n8n). Em produção, usar variáveis de cenário (Scenario Variables)
- **Modelo LLM:** usa Claude Haiku via HTTP — mesmo modelo e prompt que o n8n. A comparação é justa
- **Tunnel temporário:** ok para demo/lab. Em produção, API pública com autenticação

---

## 6. Variações para demonstrar (opcional)

- Trocar o produto (produto_id 2, 3 ou 4) e re-executar
- Alterar o prompt do Claude no Módulo 5 para pedir email em inglês
- Adicionar um Módulo 8 (HTTP GET) para listar todos os pedidos ao final
- Comparar a mesma operação feita via Claude Code (linguagem natural) — demo mais rica
- Executar 3 vezes seguidas e comparar os emails gerados (não-determinismo do LLM)

---

## 7. MCP Toolboxes — Make também tem MCP!

O Make lançou **MCP Toolboxes** (março 2026) — permite expor cenários como tools para AI clients (Claude, ChatGPT, Cursor). Funciona no plano free.

### Como configurar

1. No Make, vá em **MCP Toolboxes** (menu lateral)
2. Clique em **+ Create toolbox**
3. Nomeie (ex: "Mini-ERP Lab") e selecione o cenário (deve estar **ativo** e com scheduling **On demand**)
4. Copie a **key** gerada e a **MCP Server URL**

### Conectar ao Claude Code

```bash
claude mcp add --transport http make-toolbox "<MCP_TOOLBOX_URL>/t/<TOOLBOX_KEY>/stateless"
```

### Comparação MCP: Make vs n8n

| Aspecto | Make (MCP Toolboxes) | n8n (Instance-level MCP) |
|---------|---------------------|-------------------------|
| **Expõe cenários como tools** | Sim — cenários selecionados por toolbox | Sim — workflows habilitados |
| **Auth** | Token/key por toolbox | OAuth ou config local |
| **Escopo** | Granular — escolhe quais cenários expor | Todos os workflows habilitados |
| **Timeout** | 40 segundos (limitação) | Sem limite prático |
| **Gerenciamento via MCP** | Somente execução (free); visualizar/editar (pago) | Completo — search, execute, get_execution, create, update |
| **Monitoramento** | Dashboard de uso por toolbox | Log de execuções por workflow |
| **Claude Code** | Sim — executa cenários | Sim — executa + lê resultados + cria workflows |

### Diferença-chave

O MCP do n8n é **mais rico**: permite buscar workflows, ler resultados detalhados nó a nó, e criar/editar workflows programaticamente. O MCP do Make é **mais controlado**: escopo por toolbox, keys granulares, mas limitado a executar cenários sem visibilidade interna.

---

## 8. Limitações do Make vs n8n (para a discussão)

| Limitação | Make | n8n |
|-----------|------|-----|
| **MCP support** | Sim — MCP Toolboxes (execução de cenários) | Sim — Instance-level MCP (execução + gestão completa) |
| **Claude Code integration** | Executa cenários via MCP Toolboxes | Executa + lê resultados + cria workflows via MCP |
| **Self-hosting** | Impossível (SaaS-only) | Docker, K8s, npm |
| **Credential vault** | Básico (variáveis de cenário) | Credentials centralizadas com encryption |
| **Code execution** | JavaScript limitado em módulos específicos | JS/Python em qualquer nó, nodes custom |

> **Conclusão arquitetural:** Ambas as plataformas suportam MCP, mas com profundidades diferentes. Make é excelente para expor automações SaaS como tools com controle de acesso granular. n8n oferece integração MCP mais profunda (gestão programática de workflows), além de controle total sobre infra e compliance.

---

## Troubleshooting

- **Tunnel caiu:** rodar `bash scripts/expose_api_cloudflare.sh` novamente (URL nova — atualizar todos os módulos)
- **403 no Make:** verificar que o tunnel está ativo e a URL está correta
- **Make pede upgrade:** usar conta free — 2 cenários e 1000 operações/mês é suficiente para o lab
- **Erro 401 no módulo do Claude:** verificar API key no header `x-api-key`
- **Erro 400 no módulo do Claude:** verificar se o `model` está correto e o JSON é válido
- **Referência entre módulos:** no Make, `{{N.campo}}` referencia o output do módulo N. Se o campo não aparece no autocomplete, execute o módulo anterior primeiro (Run once) para popular o schema
- **Router não ativa rota:** verificar os filtros — o campo pode estar em `{{1.data.campo}}` ou `{{1.body.campo}}` dependendo de como o parse response interpreta o JSON
