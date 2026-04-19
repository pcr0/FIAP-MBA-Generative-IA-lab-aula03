from datetime import datetime
from pydantic import BaseModel


# --- Produto ---

class ProdutoOut(BaseModel):
    id: int
    nome: str
    descricao: str
    preco: float
    ativo: bool

    model_config = {"from_attributes": True}


# --- Estoque ---

class EstoqueOut(BaseModel):
    produto_id: int
    produto_nome: str
    quantidade: int


# --- Pedido (request) ---

class ItemPedidoIn(BaseModel):
    produto_id: int
    quantidade: int


class PedidoIn(BaseModel):
    nome_cliente: str
    itens: list[ItemPedidoIn]


# --- Pedido (response) ---

class ItemPedidoOut(BaseModel):
    produto_id: int
    produto_nome: str
    quantidade: int
    preco_unitario: float
    subtotal: float


class PedidoOut(BaseModel):
    id: int
    nome_cliente: str
    total: float
    status: str
    criado_em: datetime
    itens: list[ItemPedidoOut]


# --- Fatura ---

class FaturaOut(BaseModel):
    id: int
    pedido_id: int
    valor_total: float
    status: str
    criada_em: datetime


# --- Aprovação ---

class LogAprovacaoIn(BaseModel):
    etapa: str
    agente: str
    parecer: str = ""
    recomendacao: str | None = None
    detalhes: str | None = None


class LogAprovacaoOut(BaseModel):
    id: int
    aprovacao_id: int
    etapa: str
    agente: str
    parecer: str
    recomendacao: str | None
    detalhes: str | None
    criado_em: datetime

    model_config = {"from_attributes": True}


class AprovacaoOut(BaseModel):
    id: int
    pedido_id: int
    status: str
    criado_em: datetime
    atualizado_em: datetime
    logs: list[LogAprovacaoOut] = []

    model_config = {"from_attributes": True}


class AprovacaoResumoOut(BaseModel):
    id: int
    pedido_id: int
    status: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class DecisaoJuizIn(BaseModel):
    decisao: str
    justificativa: str


class DecisaoHumanaIn(BaseModel):
    decisao: str
    responsavel: str
    comentario: str


class EscalonamentoIn(BaseModel):
    motivo: str
