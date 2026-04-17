# Demo n8n — Orquestração Híbrida (Workflow + LLM)

## O que é

Workflow visual que demonstra orquestração híbrida: etapas determinísticas (consultar estoque, criar pedido, gerar fatura) combinadas com chamadas a LLM (Claude gera email de confirmação ou sugere alternativas quando não há estoque). Consome o mesmo ERP via HTTP.

## Pré-requisitos

- Podman instalado (`brew install podman` no macOS)
- ERP rodando em `http://localhost:8000`
- API key da Anthropic

## 1. Subir o n8n

```bash
bash scripts/start_n8n.sh
```

Acesse: http://localhost:5678

Na primeira vez, crie uma conta local (qualquer email/senha — é só local).

## 2. Configurar a credential da Anthropic

Antes de importar o workflow, configure a API key:

1. No n8n, vá em **Settings** (engrenagem) → **Credentials**
2. Clique em **Add Credential**
3. Busque e selecione **Header Auth**
4. Preencha:
   - **Name:** `Anthropic API Key`
   - **Header Name:** `x-api-key`
   - **Header Value:** sua chave da Anthropic (`sk-ant-...`)
5. Clique em **Save**

> **Importante:** o nome da credential deve ser exatamente `Anthropic API Key` — o workflow referencia esse nome.

## 3. Importar o workflow

1. No n8n, clique em **"..."** (menu) → **Import from File**
2. Selecione `artifacts/n8n/workflow_erp.json`
3. O workflow aparece com 10 nós em dois caminhos:

```text
                                                 ┌── Caminho feliz ───────────────────────────────────────────────┐
Start → Consultar Estoque → Estoque > 0? ──yes──→ Criar Pedido → Gerar Fatura → Claude: Email → Email Gerado
                                         │
                                         └──no───→ Alerta Sem Estoque → Claude: Sugerir Alternativas → Sugestão Gerada
```

## 4. Executar

1. Clique em **"Test Workflow"** (botão no canto inferior)
2. O workflow executa nó a nó — clique em cada nó para ver o output
3. **Caminho feliz (com estoque):**
   - Cria pedido, gera fatura, e o Claude escreve um email de confirmação para o cliente
   - O nó **Email Gerado** mostra o email em linguagem natural
4. **Caminho sem estoque:**
   - Registra alerta no ERP (`POST /alertas`), e o Claude sugere produtos alternativos do catálogo
   - O nó **Sugestão Gerada** mostra a mensagem empática com sugestões

## 5. Pontos para destacar na aula

- **Orquestração híbrida:** etapas determinísticas (HTTP) + etapas generativas (LLM) no mesmo workflow
- **Quando usar LLM vs. código:** a decisão de estoque é um IF simples (determinístico); a geração de email exige linguagem natural (LLM)
- **Gestão de secrets:** a API key fica nas Credentials do n8n, nunca no workflow JSON
- **Mesmo ERP, 3 interfaces:** HTTP direto, MCP → Claude Code, e n8n — cada uma com trade-offs diferentes
- **Encadeamento de dados:** output de um nó alimenta o prompt do Claude (`{{ $json.id }}`, `{{ $json.valor_total }}`)
- **Modelo econômico:** usa Claude Haiku (rápido e barato) para tarefas simples de geração de texto

## 6. Variações para demonstrar (opcional)

- Mudar a quantidade do pedido para forçar o caminho "sem estoque" e ver a sugestão do Claude
- Trocar o produto (produto_id 2, 3 ou 4)
- Alterar o prompt do Claude no nó para pedir o email em inglês ou mudar o tom
- Comparar a mesma operação feita via Claude Code (linguagem natural) vs. n8n (visual)

## 7. Executar o workflow via MCP nativo do n8n

O n8n (v2.13+) expõe um **MCP Server HTTP nativo** que permite que LLMs (Claude Code, Claude Desktop) descubram e executem workflows diretamente — sem webhook, sem curl.

### 7.1 Habilitar o MCP no n8n

1. No n8n, vá em **Settings** → **Instance-level MCP** (menu lateral)
2. Ative o toggle **Enabled**
3. Clique em **Enable workflows** → selecione o workflow "Mini-ERP — Orquestração Híbrida"
4. Clique em **Connection details** → copie o **Access Token** e a **Server URL**

A URL será algo como:

```
http://localhost:5678/mcp-server/http
```

### 7.2 Configurar no Claude Code

Execute no terminal:

```bash
claude mcp add \
  --transport http \
  --header "Authorization: Bearer <ACCESS_TOKEN>" \
  --scope project \
  n8n-erp \
  http://localhost:5678/mcp-server/http
```

Isso cria o arquivo `.mcp.json` no projeto com a configuração permanente:

```json
{
  "mcpServers": {
    "n8n-erp": {
      "type": "http",
      "url": "http://localhost:5678/mcp-server/http",
      "headers": {
        "Authorization": "Bearer <ACCESS_TOKEN>"
      }
    }
  }
}
```

**Reinicie o Claude Code** após configurar para que ele conecte ao server.

### 7.3 Configurar no Claude Desktop

Edite o `claude_desktop_config.json` (caminhos por OS na [doc do MCP](02_como_subir_o_mcp.md)):

```json
{
  "mcpServers": {
    "n8n-erp": {
      "type": "http",
      "url": "http://localhost:5678/mcp-server/http",
      "headers": {
        "Authorization": "Bearer <ACCESS_TOKEN>"
      }
    }
  }
}
```

### 7.4 Tools disponíveis via MCP do n8n

Após conectar, o Claude terá acesso a 12 tools do n8n:

| Tool | Descrição |
|------|-----------|
| `search_workflows` | Buscar workflows por nome |
| `get_workflow_details` | Ver detalhes e nós de um workflow |
| `execute_workflow` | Executar workflow por ID |
| `get_execution` | Ver resultado completo da execução |
| `publish_workflow` | Ativar workflow para produção |
| `unpublish_workflow` | Desativar workflow |
| `create_workflow_from_code` | Criar workflow via código |
| `update_workflow` | Atualizar workflow existente |
| `validate_workflow` | Validar código de workflow |
| `search_nodes` | Buscar tipos de nós disponíveis |
| `get_node_types` | Ver definições de tipos de nós |
| `archive_workflow` | Arquivar workflow |

### 7.5 Exemplo de uso no Claude Code

Após configurar, converse normalmente:

1. "Busque o workflow do Mini-ERP" → usa `search_workflows`
2. "Execute o workflow" → usa `execute_workflow` com o ID retornado
3. "Mostre o resultado" → usa `get_execution` para ver o output de cada nó (incluindo o email gerado pelo Claude Haiku)

### 7.6 Sobre o token

- O token JWT **não expira por sessão** do Claude — fica válido enquanto o n8n estiver rodando e os dados persistirem (`~/.n8n`)
- O token só é invalidado se for **regenerado manualmente** no n8n (Settings → Instance-level MCP → Connection details → regenerar)
- Reiniciar o Claude Code ou o container do n8n **não invalida** o token (desde que `~/.n8n` persista via volume)
- Se o token parar de funcionar, regenere no n8n e atualize o `.mcp.json` ou reconfigure via `claude mcp add`

## Troubleshooting

- **"ECONNREFUSED":** o n8n roda em Podman — use `host.containers.internal:8000` (já configurado no workflow)
- **n8n não abre:** verificar se a porta 5678 está livre: `lsof -i :5678`
- **Workflow não importa:** verificar que o JSON está válido
- **Erro 401 nos nós do Claude:** a credential "Anthropic API Key" não foi criada ou o nome não bate — refaça o passo 2
- **Erro 400 nos nós do Claude:** verificar se o model ID está correto no body JSON do nó
