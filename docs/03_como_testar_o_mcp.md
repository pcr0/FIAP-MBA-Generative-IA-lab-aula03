# Como Testar o MCP Server

## Opção 1: MCP Inspector (recomendado para demo)

O Inspector é uma UI web que permite testar cada tool interativamente.

```bash
bash scripts/test_mcp.sh
```

Isso executa `mcp dev main.py` e abre o browser com o Inspector.

### Fluxo de teste sugerido

1. **listar_produtos** → confirmar que retorna 4 produtos ativos
2. **consultar_estoque** → `produto_id: 1` → ver 10 unidades de Notebook
3. **criar_pedido** → usar:
   ```json
   {
     "nome_cliente": "Aluno FIAP",
     "itens": [
       {"produto_id": 1, "quantidade": 2},
       {"produto_id": 2, "quantidade": 5}
     ]
   }
   ```
4. **consultar_pedido** → usar o ID retornado → status "CRIADO"
5. **gerar_fatura_simulada** → usar o mesmo ID do pedido
6. **consultar_pedido** → mesmo ID → status agora "FATURADO"
7. **consultar_fatura** → usar o ID da fatura retornado

## Opção 2: Claude Desktop

1. Configure o MCP no Claude Desktop (ver [02_como_subir_o_mcp.md](02_como_subir_o_mcp.md))
2. Abra uma conversa e peça:
   - "Quais produtos temos disponíveis?"
   - "Qual o estoque do Notebook Básico?"
   - "Crie um pedido de 2 Notebooks para o cliente João"
   - "Gere a fatura desse pedido"

O Claude vai usar as tools automaticamente.

## Opção 3: Claude Code

```bash
claude mcp add mini-erp -- python /caminho/para/mcp_server/main.py
claude
```

Depois converse normalmente — o Claude Code chama as tools do MCP.

## Opção 4: Testar só o ERP (sem MCP)

```bash
bash scripts/test_erp_api.sh
```

Testa todos os endpoints via curl e mostra ✓/✗ para cada um.
