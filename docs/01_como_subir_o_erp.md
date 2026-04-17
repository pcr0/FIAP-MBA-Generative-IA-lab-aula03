# Como Subir o ERP

## O que é

Mini-ERP Didático — API REST em FastAPI com SQLite. Gerencia produtos, estoque, pedidos e faturas.

## Localização

O Mini-ERP já vem incluído neste lab, na pasta `erp/`:

```
lab-aula03/
├── erp/           ← Mini-ERP (FastAPI + SQLite)
├── mcp_server/
├── scripts/
└── ...
```

## Subir

```bash
bash scripts/start_erp.sh
```

O script detecta automaticamente o diretório `erp/` dentro do lab.

Ou manualmente:

```bash
cd erp
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Verificar

- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs
- Listar produtos: http://localhost:8000/produtos

## Dados iniciais

O ERP já vem com seed data (5 produtos):

| ID | Produto | Preço | Estoque | Ativo |
|----|---------|-------|---------|-------|
| 1 | Notebook Básico | R$ 2.500 | 10 | Sim |
| 2 | Mouse USB | R$ 50 | 100 | Sim |
| 3 | Teclado Mecânico | R$ 350 | 30 | Sim |
| 4 | Monitor 24pol | R$ 1.200 | 15 | Sim |
| 5 | Webcam HD | R$ 200 | 50 | Não |

## Troubleshooting

- **Porta ocupada:** `lsof -i :8000` para ver quem está usando
- **DB corrompido:** apagar `erp/data/mini_erp.db` e reiniciar (o seed recria)
- **Dependências:** `cd erp && pip install -r requirements.txt`
