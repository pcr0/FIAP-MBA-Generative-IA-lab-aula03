# Como Subir o MCP Server

## O que é

Servidor MCP (Model Context Protocol) que expõe as funcionalidades do Mini-ERP como tools para LLMs. Usa FastMCP + httpx, transporte stdio.

## Pré-requisito

O ERP deve estar rodando em `http://localhost:8000` (ver [01_como_subir_o_erp.md](01_como_subir_o_erp.md)).

## Subir (modo desenvolvimento)

```bash
bash scripts/start_mcp.sh
```

O script cria um venv, instala dependências e inicia o server.

## Configurar no Claude Desktop

Edite o arquivo `claude_desktop_config.json`. O caminho depende do sistema operacional:

| OS | Caminho |
| ---- | ------- |
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |

Conteúdo:

```json
{
  "mcpServers": {
    "mini-erp": {
      "command": "/caminho/para/lab-aula03/mcp_server/venv/bin/python",
      "args": ["/caminho/para/lab-aula03/mcp_server/main.py"]
    }
  }
}
```

Reinicie o Claude Desktop após editar.

## Configurar no Claude Code

> **Importante:** use o python do **venv** (não o do sistema), caso contrário o server falha por falta de dependências (httpx, fastmcp).

```bash
claude mcp add mini-erp -- /caminho/para/lab-aula03/mcp_server/venv/bin/python /caminho/para/lab-aula03/mcp_server/main.py
```

Para verificar se conectou:

```bash
claude mcp list
```

Reinicie a sessão do Claude Code após adicionar para que as tools fiquem disponíveis.

## Tools disponíveis

Após conectar, o LLM terá acesso a:

1. `listar_produtos` — lista produtos ativos
2. `buscar_produto(produto_id)` — detalhes de um produto
3. `consultar_estoque(produto_id)` — quantidade em estoque
4. `criar_pedido(nome_cliente, itens)` — cria pedido
5. `listar_pedidos(limit)` — pedidos recentes
6. `consultar_pedido(pedido_id)` — detalhes do pedido
7. `gerar_fatura_simulada(pedido_id)` — gera fatura
8. `consultar_fatura(fatura_id)` — detalhes da fatura
9. `enviar_alerta(tipo, mensagem, detalhes)` — envia alerta ao ERP
10. `listar_alertas` — lista os últimos 20 alertas

## Testando o acesso ao MCP

Após configurar e reiniciar a sessão, peça ao Claude para testar o acesso. Exemplo de prompt:

```text
Liste os produtos disponíveis no mini-ERP.
```

Resposta esperada — o Claude deve chamar a tool `listar_produtos` e retornar algo como:

| ID | Produto | Preço |
| -- | ------- | ----- |
| 1 | Notebook Básico | R$ 2.500,00 |
| 2 | Mouse USB | R$ 50,00 |
| 3 | Teclado Mecânico | R$ 350,00 |
| 4 | Monitor 24pol | R$ 1.200,00 |

Se o Claude não reconhecer a tool ou responder que não tem acesso, verifique a seção Troubleshooting abaixo.

## Troubleshooting

- **"Connection refused":** o ERP não está rodando — suba primeiro
- **Dependências:** `cd mcp_server && source venv/bin/activate && pip install -r requirements.txt`
- **`ModuleNotFoundError: No module named 'httpx'`:** o comando está usando o python do sistema em vez do venv — reconfigure com o caminho completo do venv (ver seção "Configurar no Claude Code")
- **Verificar tools:** use `mcp dev main.py` para abrir o Inspector
