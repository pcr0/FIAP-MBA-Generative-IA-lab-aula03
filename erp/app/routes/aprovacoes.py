from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Pedido, Aprovacao, LogAprovacao
from app.schemas import (
    AprovacaoOut,
    AprovacaoResumoOut,
    LogAprovacaoIn,
    LogAprovacaoOut,
    DecisaoJuizIn,
    DecisaoHumanaIn,
    EscalonamentoIn,
)

router = APIRouter(tags=["Aprovações"])

LIMITE_APROVACAO = 10_000.0


def _aprovacao_to_out(aprovacao: Aprovacao) -> AprovacaoOut:
    return AprovacaoOut(
        id=aprovacao.id,
        pedido_id=aprovacao.pedido_id,
        status=aprovacao.status,
        criado_em=aprovacao.criado_em,
        atualizado_em=aprovacao.atualizado_em,
        logs=[
            LogAprovacaoOut(
                id=log.id,
                aprovacao_id=log.aprovacao_id,
                etapa=log.etapa,
                agente=log.agente,
                parecer=log.parecer,
                recomendacao=log.recomendacao,
                detalhes=log.detalhes,
                criado_em=log.criado_em,
            )
            for log in aprovacao.logs
        ],
    )


@router.post("/aprovacoes", response_model=AprovacaoOut, status_code=201)
def criar_aprovacao(pedido_id: int, db: Session = Depends(get_db)):
    """Inicia processo de aprovação para um pedido > R$10.000."""
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if pedido.total <= LIMITE_APROVACAO:
        raise HTTPException(status_code=400, detail=f"Pedido com total R${pedido.total:.2f} não requer aprovação (limite: R${LIMITE_APROVACAO:.2f})")
    if pedido.status != "PENDENTE_APROVACAO":
        raise HTTPException(status_code=400, detail=f"Pedido com status '{pedido.status}' não pode iniciar aprovação")

    existente = db.query(Aprovacao).filter(Aprovacao.pedido_id == pedido_id).first()
    if existente:
        raise HTTPException(status_code=400, detail="Pedido já possui processo de aprovação")

    aprovacao = Aprovacao(pedido_id=pedido_id)
    db.add(aprovacao)
    db.flush()

    log = LogAprovacao(
        aprovacao_id=aprovacao.id,
        etapa="SUBMISSAO",
        agente="sistema",
        parecer=f"Processo de aprovação iniciado para pedido #{pedido_id} (total: R${pedido.total:.2f})",
        recomendacao=None,
    )
    db.add(log)
    db.commit()
    db.refresh(aprovacao)

    return _aprovacao_to_out(aprovacao)


@router.get("/aprovacoes/pendentes", response_model=list[AprovacaoResumoOut])
def listar_pendentes(db: Session = Depends(get_db)):
    """Lista aprovações que não estão em estado terminal."""
    estados_terminais = ("APROVADO", "REJEITADO")
    aprovacoes = (
        db.query(Aprovacao)
        .filter(Aprovacao.status.notin_(estados_terminais))
        .order_by(Aprovacao.criado_em.desc())
        .all()
    )
    return [
        AprovacaoResumoOut(
            id=a.id,
            pedido_id=a.pedido_id,
            status=a.status,
            criado_em=a.criado_em,
        )
        for a in aprovacoes
    ]


@router.get("/aprovacoes/historico", response_model=list[AprovacaoResumoOut])
def historico_cliente(cliente: str, db: Session = Depends(get_db)):
    """Retorna histórico de aprovações de um cliente (por nome)."""
    aprovacoes = (
        db.query(Aprovacao)
        .join(Pedido)
        .filter(Pedido.nome_cliente == cliente)
        .order_by(Aprovacao.criado_em.desc())
        .all()
    )
    return [
        AprovacaoResumoOut(
            id=a.id,
            pedido_id=a.pedido_id,
            status=a.status,
            criado_em=a.criado_em,
        )
        for a in aprovacoes
    ]


@router.get("/aprovacoes/{pedido_id}", response_model=AprovacaoOut)
def consultar_aprovacao(pedido_id: int, db: Session = Depends(get_db)):
    """Retorna aprovação completa com todos os logs de auditoria."""
    aprovacao = db.query(Aprovacao).filter(Aprovacao.pedido_id == pedido_id).first()
    if not aprovacao:
        raise HTTPException(status_code=404, detail="Aprovação não encontrada para este pedido")
    return _aprovacao_to_out(aprovacao)


@router.post("/aprovacoes/{pedido_id}/parecer", response_model=LogAprovacaoOut, status_code=201)
def registrar_parecer(pedido_id: int, dados: LogAprovacaoIn, db: Session = Depends(get_db)):
    """Registra parecer de um agente (financeiro ou operacional)."""
    aprovacao = db.query(Aprovacao).filter(Aprovacao.pedido_id == pedido_id).first()
    if not aprovacao:
        raise HTTPException(status_code=404, detail="Aprovação não encontrada para este pedido")
    if aprovacao.status != "ANALISE_EM_ANDAMENTO":
        raise HTTPException(status_code=400, detail=f"Aprovação com status '{aprovacao.status}' não aceita pareceres")

    etapas_validas = ("PARECER_FINANCEIRO", "PARECER_OPERACIONAL")
    if dados.etapa not in etapas_validas:
        raise HTTPException(status_code=400, detail=f"Etapa deve ser uma de: {etapas_validas}")

    # Verificar duplicata
    existente = (
        db.query(LogAprovacao)
        .filter(LogAprovacao.aprovacao_id == aprovacao.id, LogAprovacao.etapa == dados.etapa)
        .first()
    )
    if existente:
        raise HTTPException(status_code=400, detail=f"Parecer '{dados.etapa}' já registrado para esta aprovação")

    log = LogAprovacao(
        aprovacao_id=aprovacao.id,
        etapa=dados.etapa,
        agente=dados.agente,
        parecer=dados.parecer,
        recomendacao=dados.recomendacao,
        detalhes=dados.detalhes,
    )
    db.add(log)

    # Verificar se ambos os pareceres já existem
    etapas_existentes = {dados.etapa}
    for l in aprovacao.logs:
        if l.etapa in etapas_validas:
            etapas_existentes.add(l.etapa)

    if etapas_existentes == set(etapas_validas):
        aprovacao.status = "PARECERES_COMPLETOS"
        aprovacao.atualizado_em = datetime.now()

    db.commit()
    db.refresh(log)

    return LogAprovacaoOut(
        id=log.id,
        aprovacao_id=log.aprovacao_id,
        etapa=log.etapa,
        agente=log.agente,
        parecer=log.parecer,
        recomendacao=log.recomendacao,
        detalhes=log.detalhes,
        criado_em=log.criado_em,
    )


@router.post("/aprovacoes/{pedido_id}/decisao-juiz", response_model=LogAprovacaoOut, status_code=201)
def decisao_juiz(pedido_id: int, dados: DecisaoJuizIn, db: Session = Depends(get_db)):
    """Registra decisão do Juiz (LLM-as-a-Judge). Transiciona para AGUARDANDO_HUMANO."""
    aprovacao = db.query(Aprovacao).filter(Aprovacao.pedido_id == pedido_id).first()
    if not aprovacao:
        raise HTTPException(status_code=404, detail="Aprovação não encontrada para este pedido")
    if aprovacao.status != "PARECERES_COMPLETOS":
        raise HTTPException(status_code=400, detail=f"Aprovação com status '{aprovacao.status}' não está pronta para decisão do juiz")

    if dados.decisao not in ("APROVAR", "REJEITAR"):
        raise HTTPException(status_code=400, detail="Decisão deve ser 'APROVAR' ou 'REJEITAR'")

    log = LogAprovacao(
        aprovacao_id=aprovacao.id,
        etapa="DECISAO_JUIZ",
        agente="juiz",
        parecer=dados.justificativa,
        recomendacao=dados.decisao,
    )
    db.add(log)

    aprovacao.status = "AGUARDANDO_HUMANO"
    aprovacao.atualizado_em = datetime.now()

    db.commit()
    db.refresh(log)

    return LogAprovacaoOut(
        id=log.id,
        aprovacao_id=log.aprovacao_id,
        etapa=log.etapa,
        agente=log.agente,
        parecer=log.parecer,
        recomendacao=log.recomendacao,
        detalhes=log.detalhes,
        criado_em=log.criado_em,
    )


@router.post("/aprovacoes/{pedido_id}/decisao-humana", response_model=LogAprovacaoOut, status_code=201)
def decisao_humana(pedido_id: int, dados: DecisaoHumanaIn, db: Session = Depends(get_db)):
    """Registra decisão final do humano (HITL). Atualiza status do pedido."""
    aprovacao = db.query(Aprovacao).filter(Aprovacao.pedido_id == pedido_id).first()
    if not aprovacao:
        raise HTTPException(status_code=404, detail="Aprovação não encontrada para este pedido")
    if aprovacao.status != "AGUARDANDO_HUMANO":
        raise HTTPException(status_code=400, detail=f"Aprovação com status '{aprovacao.status}' não está aguardando decisão humana")

    if dados.decisao not in ("APROVAR", "REJEITAR"):
        raise HTTPException(status_code=400, detail="Decisão deve ser 'APROVAR' ou 'REJEITAR'")

    status_final = "APROVADO" if dados.decisao == "APROVAR" else "REJEITADO"

    log = LogAprovacao(
        aprovacao_id=aprovacao.id,
        etapa="DECISAO_HUMANA",
        agente=f"humano:{dados.responsavel}",
        parecer=dados.comentario,
        recomendacao=dados.decisao,
    )
    db.add(log)

    aprovacao.status = status_final
    aprovacao.atualizado_em = datetime.now()

    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    pedido.status = status_final

    db.commit()
    db.refresh(log)

    return LogAprovacaoOut(
        id=log.id,
        aprovacao_id=log.aprovacao_id,
        etapa=log.etapa,
        agente=log.agente,
        parecer=log.parecer,
        recomendacao=log.recomendacao,
        detalhes=log.detalhes,
        criado_em=log.criado_em,
    )


@router.post("/aprovacoes/{pedido_id}/escalar", response_model=LogAprovacaoOut, status_code=201)
def escalar(pedido_id: int, dados: EscalonamentoIn, db: Session = Depends(get_db)):
    """Escala aprovação (ex: timeout 24h). Transiciona para ESCALADO."""
    aprovacao = db.query(Aprovacao).filter(Aprovacao.pedido_id == pedido_id).first()
    if not aprovacao:
        raise HTTPException(status_code=404, detail="Aprovação não encontrada para este pedido")
    if aprovacao.status in ("APROVADO", "REJEITADO"):
        raise HTTPException(status_code=400, detail="Aprovação já finalizada, não pode ser escalada")

    log = LogAprovacao(
        aprovacao_id=aprovacao.id,
        etapa="ESCALONAMENTO",
        agente="sistema",
        parecer=dados.motivo,
        recomendacao="ESCALAR",
    )
    db.add(log)

    aprovacao.status = "ESCALADO"
    aprovacao.atualizado_em = datetime.now()

    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    pedido.status = "ESCALADO"

    db.commit()
    db.refresh(log)

    return LogAprovacaoOut(
        id=log.id,
        aprovacao_id=log.aprovacao_id,
        etapa=log.etapa,
        agente=log.agente,
        parecer=log.parecer,
        recomendacao=log.recomendacao,
        detalhes=log.detalhes,
        criado_em=log.criado_em,
    )
