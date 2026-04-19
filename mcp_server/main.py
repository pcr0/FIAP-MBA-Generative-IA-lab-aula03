"""
MCP Server — Mini-ERP Didático
Expõe tools para consumir a API REST do Mini-ERP (http://localhost:8000).
Transporte: stdio (para uso com Claude Desktop / Claude Code).
"""

import hashlib
import json
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

ERP_BASE_URL = "http://localhost:8000"

mcp = FastMCP(
    "Mini-ERP",
    instructions=(
        "Servidor MCP para o Mini-ERP Didático. "
        "Use as tools disponíveis para consultar produtos, estoque, "
        "criar pedidos e gerar faturas. "
        "Para pedidos acima de R$10.000, use o fluxo de aprovação: "
        "submeter_para_aprovacao → registrar_parecer (financeiro + operacional) → "
        "decidir_aprovacao_juiz → decidir_aprovacao_humana. "
        "Use as tools de pesquisa (consultar_pedidos_cliente, consultar_estoque_reservado, etc.) "
        "para embasar os pareceres dos agentes."
    ),
)


async def _erp_request(method: str, path: str, body: dict | None = None, params: dict | None = None) -> dict | list:
    """Faz requisição HTTP ao ERP e retorna o JSON de resposta."""
    async with httpx.AsyncClient(base_url=ERP_BASE_URL, timeout=10) as client:
        if method == "GET":
            resp = await client.get(path, params=params)
        else:
            resp = await client.post(path, json=body, params=params)
        resp.raise_for_status()
        return resp.json()


def _fmt(data: Any) -> str:
    """Formata dados como JSON legível."""
    return json.dumps(data, ensure_ascii=False, indent=2)


# ── Anonimização Bidirecional (LGPD) ────────────────────────────────────

_mapa_anonimizacao: dict[str, str] = {}      # nome_real → pseudônimo
_mapa_desanonimizacao: dict[str, str] = {}   # pseudônimo → nome_real


def _registrar_cliente(nome: str) -> str:
    """Registra um nome de cliente e retorna seu pseudônimo. Idempotente."""
    if nome in _mapa_anonimizacao:
        return _mapa_anonimizacao[nome]
    pseudo = "CLIENTE_" + hashlib.sha256(nome.encode()).hexdigest()[:6]
    _mapa_anonimizacao[nome] = pseudo
    _mapa_desanonimizacao[pseudo] = nome
    return pseudo


def _anonimizar(dados: Any) -> Any:
    """Substitui nomes reais de clientes por pseudônimos (recursivo)."""
    if isinstance(dados, str):
        for nome_real, pseudo in _mapa_anonimizacao.items():
            dados = dados.replace(nome_real, pseudo)
        return dados
    if isinstance(dados, dict):
        resultado = {}
        for k, v in dados.items():
            if k == "nome_cliente" and isinstance(v, str):
                _registrar_cliente(v)
                resultado[k] = _mapa_anonimizacao[v]
            else:
                resultado[k] = _anonimizar(v)
        return resultado
    if isinstance(dados, list):
        return [_anonimizar(item) for item in dados]
    return dados


def _desanonimizar(dados: Any) -> Any:
    """Substitui pseudônimos por nomes reais de clientes (recursivo)."""
    if isinstance(dados, str):
        for pseudo, nome_real in _mapa_desanonimizacao.items():
            dados = dados.replace(pseudo, nome_real)
        return dados
    if isinstance(dados, dict):
        resultado = {}
        for k, v in dados.items():
            if k == "nome_cliente" and isinstance(v, str) and v in _mapa_desanonimizacao:
                resultado[k] = _mapa_desanonimizacao[v]
            else:
                resultado[k] = _desanonimizar(v)
        return resultado
    if isinstance(dados, list):
        return [_desanonimizar(item) for item in dados]
    return dados


# ── Tools ────────────────────────────────────────────────────────────────


@mcp.tool()
async def listar_produtos() -> str:
    """Lista todos os produtos ativos do ERP.

    Retorna nome, preço, descrição e status de cada produto.
    Use para descobrir quais produtos estão disponíveis antes de criar pedidos.
    """
    data = await _erp_request("GET", "/produtos")
    return _fmt(data)


@mcp.tool()
async def buscar_produto(produto_id: int) -> str:
    """Busca detalhes de um produto específico pelo ID.

    Args:
        produto_id: ID do produto no ERP.
    """
    data = await _erp_request("GET", f"/produtos/{produto_id}")
    return _fmt(data)


@mcp.tool()
async def consultar_estoque(produto_id: int) -> str:
    """Consulta a quantidade em estoque de um produto.

    Args:
        produto_id: ID do produto para verificar estoque.
    """
    data = await _erp_request("GET", f"/estoque/{produto_id}")
    return _fmt(data)


@mcp.tool()
async def criar_pedido(nome_cliente: str, itens: list[dict]) -> str:
    """Cria um novo pedido no ERP.

    Valida estoque disponível e reduz automaticamente as quantidades.

    Args:
        nome_cliente: Nome do cliente que está fazendo o pedido.
        itens: Lista de itens. Cada item é um dict com 'produto_id' (int) e 'quantidade' (int).
              Exemplo: [{"produto_id": 1, "quantidade": 2}, {"produto_id": 3, "quantidade": 1}]
    """
    body = {"nome_cliente": nome_cliente, "itens": itens}
    data = await _erp_request("POST", "/pedidos", body)
    return _fmt(data)


@mcp.tool()
async def listar_pedidos(limit: int = 10) -> str:
    """Lista os pedidos mais recentes do ERP.

    Args:
        limit: Número máximo de pedidos a retornar (padrão: 10).
    """
    data = await _erp_request("GET", f"/pedidos?limit={limit}")
    return _fmt(data)


@mcp.tool()
async def consultar_pedido(pedido_id: int) -> str:
    """Consulta detalhes de um pedido específico, incluindo itens e status.

    Args:
        pedido_id: ID do pedido no ERP.
    """
    data = await _erp_request("GET", f"/pedidos/{pedido_id}")
    return _fmt(data)


@mcp.tool()
async def gerar_fatura_simulada(pedido_id: int) -> str:
    """Gera uma fatura para um pedido existente.

    O pedido deve existir e ainda não ter fatura. Após a geração,
    o status do pedido muda para FATURADO.

    Args:
        pedido_id: ID do pedido para faturar.
    """
    data = await _erp_request("POST", f"/pedidos/{pedido_id}/fatura")
    return _fmt(data)


@mcp.tool()
async def consultar_fatura(fatura_id: int) -> str:
    """Consulta detalhes de uma fatura pelo ID.

    Args:
        fatura_id: ID da fatura no ERP.
    """
    data = await _erp_request("GET", f"/faturas/{fatura_id}")
    return _fmt(data)


@mcp.tool()
async def enviar_alerta(tipo: str, mensagem: str, detalhes: dict | None = None) -> str:
    """Envia um alerta ao ERP (ex: estoque insuficiente, erro de faturamento).

    Args:
        tipo: Tipo do alerta (ex: 'estoque_insuficiente', 'erro_faturamento').
        mensagem: Descrição do alerta.
        detalhes: Dados adicionais opcionais (ex: {"produto_id": 1, "estoque_atual": 0}).
    """
    body = {"tipo": tipo, "mensagem": mensagem}
    if detalhes:
        body["detalhes"] = detalhes
    data = await _erp_request("POST", "/alertas", body)
    return _fmt(data)


@mcp.tool()
async def listar_alertas() -> str:
    """Lista os últimos 20 alertas registrados no ERP (mais recentes primeiro)."""
    data = await _erp_request("GET", "/alertas")
    return _fmt(data)


# ── Tools de Aprovação ───────────────────────────────────────────────────


@mcp.tool()
async def submeter_para_aprovacao(pedido_id: int) -> str:
    """Inicia o processo de aprovação para um pedido acima de R$10.000.

    Cria o registro de aprovação no ERP e retorna os dados do pedido
    com nome do cliente anonimizado (LGPD). Use antes de solicitar
    pareceres dos agentes financeiro e operacional.

    Args:
        pedido_id: ID do pedido que requer aprovação.
    """
    # Buscar dados do pedido para registrar o cliente no mapa de anonimização
    pedido = await _erp_request("GET", f"/pedidos/{pedido_id}")
    _registrar_cliente(pedido["nome_cliente"])

    # Criar aprovação
    data = await _erp_request("POST", "/aprovacoes", params={"pedido_id": pedido_id})

    # Retornar dados anonimizados: aprovação + pedido
    resultado = {"aprovacao": data, "pedido": pedido}
    return _fmt(_anonimizar(resultado))


@mcp.tool()
async def registrar_parecer(
    pedido_id: int, agente: str, parecer: str, recomendacao: str
) -> str:
    """Registra o parecer de um agente analista (financeiro ou operacional).

    O parecer é desanonimizado antes de salvar no banco (se contiver pseudônimos).
    Quando ambos os pareceres (financeiro e operacional) estiverem registrados,
    o status da aprovação transiciona automaticamente para PARECERES_COMPLETOS.

    Args:
        pedido_id: ID do pedido em aprovação.
        agente: Nome do agente ("financeiro" ou "operacional").
        parecer: Texto completo da análise do agente.
        recomendacao: "APROVAR" ou "REJEITAR".
    """
    etapa = f"PARECER_{agente.upper()}"
    # Desanonimizar o parecer antes de salvar
    parecer_real = _desanonimizar(parecer)
    body = {
        "etapa": etapa,
        "agente": agente,
        "parecer": parecer_real,
        "recomendacao": recomendacao,
    }
    data = await _erp_request("POST", f"/aprovacoes/{pedido_id}/parecer", body)
    return _fmt(_anonimizar(data))


@mcp.tool()
async def consultar_aprovacao(pedido_id: int) -> str:
    """Consulta o status completo de uma aprovação, incluindo todos os logs de auditoria.

    Os dados de cliente são anonimizados na resposta (LGPD).

    Args:
        pedido_id: ID do pedido cuja aprovação será consultada.
    """
    data = await _erp_request("GET", f"/aprovacoes/{pedido_id}")
    return _fmt(_anonimizar(data))


@mcp.tool()
async def decidir_aprovacao_juiz(
    pedido_id: int, decisao: str, justificativa: str
) -> str:
    """Registra a decisão do Agente Juiz (LLM-as-a-Judge).

    Só pode ser chamada após ambos os pareceres (financeiro e operacional)
    estarem registrados (status PARECERES_COMPLETOS). Transiciona o status
    para AGUARDANDO_HUMANO.

    A justificativa é desanonimizada antes de salvar no banco.

    Args:
        pedido_id: ID do pedido em aprovação.
        decisao: "APROVAR" ou "REJEITAR".
        justificativa: Texto fundamentado explicando a decisão.
    """
    justificativa_real = _desanonimizar(justificativa)
    body = {"decisao": decisao, "justificativa": justificativa_real}
    data = await _erp_request("POST", f"/aprovacoes/{pedido_id}/decisao-juiz", body)
    return _fmt(_anonimizar(data))


@mcp.tool()
async def decidir_aprovacao_humana(
    pedido_id: int, decisao: str, responsavel: str, comentario: str
) -> str:
    """Registra a decisão final do humano (HITL — Human-in-the-Loop).

    Só pode ser chamada após a decisão do juiz (status AGUARDANDO_HUMANO).
    Transiciona a aprovação e o pedido para APROVADO ou REJEITADO.
    Não aplica anonimização — o humano trabalha com dados reais.

    Args:
        pedido_id: ID do pedido em aprovação.
        decisao: "APROVAR" ou "REJEITAR".
        responsavel: Nome do humano responsável pela decisão.
        comentario: Justificativa da decisão humana.
    """
    body = {
        "decisao": decisao,
        "responsavel": responsavel,
        "comentario": comentario,
    }
    data = await _erp_request("POST", f"/aprovacoes/{pedido_id}/decisao-humana", body)
    return _fmt(data)


# ── Tools de Pesquisa para Agentes ───────────────────────────────────────


@mcp.tool()
async def consultar_pedidos_cliente(nome_cliente: str) -> str:
    """Consulta todos os pedidos de um cliente pelo nome.

    O agente pode enviar o pseudônimo (ex: CLIENTE_a3f8b2); a tool
    desanonimiza automaticamente para consultar o ERP e reanonimiza
    a resposta. Útil para o Agente Financeiro avaliar histórico de compras.

    Args:
        nome_cliente: Nome ou pseudônimo do cliente.
    """
    nome_real = _desanonimizar(nome_cliente)
    data = await _erp_request("GET", "/pedidos", params={"cliente": nome_real, "limit": 50})
    return _fmt(_anonimizar(data))


@mcp.tool()
async def consultar_historico_aprovacoes_cliente(nome_cliente: str) -> str:
    """Consulta o histórico de aprovações anteriores de um cliente.

    Desanonimiza o nome para consultar e reanonimiza a resposta.
    Útil para o Agente Financeiro avaliar padrão de aprovações do cliente.

    Args:
        nome_cliente: Nome ou pseudônimo do cliente.
    """
    nome_real = _desanonimizar(nome_cliente)
    data = await _erp_request("GET", "/aprovacoes/historico", params={"cliente": nome_real})
    return _fmt(_anonimizar(data))


@mcp.tool()
async def consultar_estoque_reservado(produto_id: int) -> str:
    """Consulta o estoque reservado de um produto (por pedidos não faturados).

    Retorna estoque total, reservado e disponível. Útil para o Agente
    Operacional avaliar se há capacidade real de entrega.

    Args:
        produto_id: ID do produto para verificar reservas.
    """
    data = await _erp_request("GET", f"/estoque/{produto_id}/reservado")
    return _fmt(data)


@mcp.tool()
async def consultar_pedidos_nao_faturados_produto(produto_id: int) -> str:
    """Lista pedidos não faturados que contêm um produto específico.

    Nomes de clientes são anonimizados na resposta. Útil para o Agente
    Operacional detalhar quais pedidos estão reservando estoque.

    Args:
        produto_id: ID do produto para buscar pedidos pendentes.
    """
    data = await _erp_request("GET", f"/pedidos/nao-faturados/{produto_id}")
    return _fmt(_anonimizar(data))


# ── Entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
