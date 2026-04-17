# Mini-ERP Didático

API REST simples de distribuição/vendas para laboratório de aula.
Demonstra consulta de dados, criação de transações e consumo por automação (n8n/Make).

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

```bash
uvicorn app.main:app --reload
```

O servidor inicia em `http://localhost:8000`.
Dados iniciais (5 produtos + estoque) são criados automaticamente no primeiro uso.

Acesse a documentação interativa (Swagger): `http://localhost:8000/docs`

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Health check |
| GET | `/produtos` | Lista produtos ativos |
| GET | `/produtos/{id}` | Detalhe de um produto |
| GET | `/estoque/{produto_id}` | Estoque de um produto |
| POST | `/pedidos` | Cria pedido (valida e abate estoque) |
| GET | `/pedidos/{id}` | Detalhe do pedido com itens |
| POST | `/pedidos/{id}/fatura` | Gera fatura simulada |
| GET | `/faturas/{id}` | Detalhe da fatura |

## Fluxo de Demonstração

```bash
# 1. Verificar saúde da API
curl http://localhost:8000/health

# 2. Listar produtos disponíveis
curl http://localhost:8000/produtos

# 3. Consultar estoque de um produto
curl http://localhost:8000/estoque/1

# 4. Criar pedido
curl -X POST http://localhost:8000/pedidos \
  -H "Content-Type: application/json" \
  -d '{
    "nome_cliente": "Empresa Exemplo Ltda",
    "itens": [
      {"produto_id": 1, "quantidade": 2},
      {"produto_id": 3, "quantidade": 1}
    ]
  }'

# 5. Consultar pedido criado
curl http://localhost:8000/pedidos/1

# 6. Gerar fatura
curl -X POST http://localhost:8000/pedidos/1/fatura

# 7. Consultar fatura
curl http://localhost:8000/faturas/1

# 8. Verificar que estoque foi abatido
curl http://localhost:8000/estoque/1
```

## Dados Iniciais

| Produto | Preço | Estoque | Ativo |
|---------|-------|---------|-------|
| Notebook Básico | R$ 2.500 | 10 | Sim |
| Mouse USB | R$ 50 | 100 | Sim |
| Teclado Mecânico | R$ 350 | 30 | Sim |
| Monitor 24pol | R$ 1.200 | 15 | Sim |
| Webcam HD | R$ 200 | 50 | **Não** |

## Uso com n8n / Make

Esta API é consumível por qualquer ferramenta de automação:

**n8n:**
- Use o nó **HTTP Request** apontando para `http://localhost:8000`
- Exemplo de workflow: consultar produtos → criar pedido → gerar fatura
- Configure os nós com os endpoints acima (GET/POST conforme a tabela)

**Make (Integromat):**
- Use o módulo **HTTP > Make a request**
- URL base: `http://localhost:8000`
- Para POST, configure Body type como JSON

## Evolução para MCP Server

Esta API pode ser exposta como um **MCP Server** (Model Context Protocol), permitindo que LLMs interajam diretamente com o ERP:

```python
# Exemplo conceitual — cada endpoint vira uma "tool" MCP:
# - listar_produtos → GET /produtos
# - consultar_estoque → GET /estoque/{id}
# - criar_pedido → POST /pedidos
# - gerar_fatura → POST /pedidos/{id}/fatura
```

Cada endpoint se transforma em uma tool que o LLM pode invocar via MCP,
com schema de parâmetros derivado dos Pydantic models já existentes.
