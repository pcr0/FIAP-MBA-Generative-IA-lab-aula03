from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import get_db
from app.models import Estoque, ItemPedido, Pedido
from app.schemas import EstoqueOut

router = APIRouter(tags=["Estoque"])


@router.get("/estoque/{produto_id}", response_model=EstoqueOut)
def consultar_estoque(produto_id: int, db: Session = Depends(get_db)):
    """Consulta estoque de um produto."""
    estoque = db.query(Estoque).filter(Estoque.produto_id == produto_id).first()
    if not estoque:
        raise HTTPException(status_code=404, detail="Estoque não encontrado para este produto")
    return EstoqueOut(
        produto_id=estoque.produto_id,
        produto_nome=estoque.produto.nome,
        quantidade=estoque.quantidade,
    )


@router.get("/estoque/{produto_id}/reservado")
def estoque_reservado(produto_id: int, db: Session = Depends(get_db)):
    """Calcula estoque reservado por pedidos não faturados (CRIADO, PENDENTE_APROVACAO, APROVADO)."""
    estoque = db.query(Estoque).filter(Estoque.produto_id == produto_id).first()
    if not estoque:
        raise HTTPException(status_code=404, detail="Estoque não encontrado para este produto")

    reservado = (
        db.query(func.coalesce(func.sum(ItemPedido.quantidade), 0))
        .join(Pedido)
        .filter(
            ItemPedido.produto_id == produto_id,
            Pedido.status.in_(["CRIADO", "PENDENTE_APROVACAO", "APROVADO"]),
        )
        .scalar()
    )

    return {
        "produto_id": produto_id,
        "produto_nome": estoque.produto.nome,
        "estoque_total": estoque.quantidade,
        "estoque_reservado": reservado,
        "estoque_disponivel": estoque.quantidade - reservado,
    }
