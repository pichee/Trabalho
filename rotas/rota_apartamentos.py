from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from banco.conexao import get_db
from banco.modelos import Apartamento, Usuario, Leitura
from seguranca.autenticacao import obter_usuario_logado

router = APIRouter(prefix="/api/v1/apartamentos", tags=["Apartamentos"])

class ApartamentoInput(BaseModel):
    numero: str
    bloco: Optional[str] = "Bloco A"
    condominio: Optional[str] = "Residencial das Palmeiras"
    morador: Optional[str] = None

@router.get("/condominios", summary="Listar condomínios cadastrados")
async def listar_condominios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """Retorna os nomes dos condomínios distintos para filtrar na interface."""
    linhas = db.query(Apartamento.condominio).filter(Apartamento.ativo == True).distinct().all()
    condominios = [l[0] for l in linhas if l[0]]
    if not condominios:
        condominios = ["Residencial das Palmeiras"]
    return sorted(condominios)

@router.get("", summary="Listar apartamentos com status visual de leitura recente (IHC)")
async def listar_apartamentos(
    condominio: Optional[str] = Query(None, description="Filtrar por nome do condomínio"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """
    Retorna a lista de apartamentos enriquecida com status de medição para IHC:
    - lido_hoje: Se já foi medido na data de hoje
    - lido_este_mes: Se já foi medido no mês vigente
    - status_leitura: 'lido_hoje' | 'lido_mes' | 'pendente'
    - Dados da última leitura (valor, data, operador e foto)
    """
    query = db.query(Apartamento).filter(Apartamento.ativo == True)
    if condominio:
        query = query.filter(Apartamento.condominio == condominio)
    aptos = query.order_by(Apartamento.numero).all()

    hoje = datetime.utcnow().date()
    inicio_mes = datetime(hoje.year, hoje.month, 1)

    resultado = []
    for a in aptos:
        # Busca a leitura mais recente deste apartamento
        ult_leitura = db.query(Leitura).filter(
            or_(
                Leitura.apartamento_id == a.id,
                Leitura.apartamento_numero == a.numero
            )
        ).order_by(Leitura.criado_em.desc()).first()

        lido_hoje = False
        lido_mes = False
        data_formatada = None
        valor_lido = None
        operador_leitura = None
        caminho_foto = None

        if ult_leitura and ult_leitura.criado_em:
            data_leitura = ult_leitura.criado_em.date()
            lido_hoje = (data_leitura == hoje)
            lido_mes = (ult_leitura.criado_em >= inicio_mes)
            data_formatada = ult_leitura.criado_em.strftime("%d/%m/%Y às %H:%M")
            valor_lido = ult_leitura.leitura_usuario
            operador_leitura = ult_leitura.usuario_nome or "Operador"
            caminho_foto = ult_leitura.caminho_foto

        resultado.append({
            "id": a.id,
            "numero": a.numero,
            "bloco": a.bloco or "Bloco A",
            "condominio": a.condominio or "Residencial das Palmeiras",
            "morador": a.morador,
            "lido_hoje": lido_hoje,
            "lido_este_mes": lido_mes,
            "status_leitura": "lido_hoje" if lido_hoje else ("lido_mes" if lido_mes else "pendente"),
            "ultima_leitura_valor": valor_lido,
            "ultima_leitura_data": data_formatada,
            "ultima_leitura_operador": operador_leitura,
            "ultima_leitura_foto": caminho_foto
        })

    return resultado

@router.get("/progresso", summary="Progresso de medição do condomínio (IHC Feedback)")
async def progresso_condominio(
    condominio: str = Query("Residencial das Palmeiras", description="Nome do condomínio"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """Calcula estatísticas de progresso para exibir no topo do leitor."""
    aptos = db.query(Apartamento).filter(
        Apartamento.condominio == condominio,
        Apartamento.ativo == True
    ).all()

    total_aptos = len(aptos)
    if total_aptos == 0:
        return {
            "total_apartamentos": 0,
            "total_lidos_mes": 0,
            "total_lidos_hoje": 0,
            "percentual_concluido": 0,
            "pendentes": 0
        }

    hoje = datetime.utcnow().date()
    inicio_mes = datetime(hoje.year, hoje.month, 1)

    lidos_hoje_count = 0
    lidos_mes_count = 0

    for a in aptos:
        ult = db.query(Leitura).filter(
            or_(
                Leitura.apartamento_id == a.id,
                Leitura.apartamento_numero == a.numero
            )
        ).order_by(Leitura.criado_em.desc()).first()

        if ult and ult.criado_em:
            if ult.criado_em.date() == hoje:
                lidos_hoje_count += 1
            if ult.criado_em >= inicio_mes:
                lidos_mes_count += 1

    percentual = round((lidos_mes_count / total_aptos) * 100) if total_aptos > 0 else 0

    return {
        "condominio": condominio,
        "total_apartamentos": total_aptos,
        "total_lidos_mes": lidos_mes_count,
        "total_lidos_hoje": lidos_hoje_count,
        "pendentes": max(0, total_aptos - lidos_mes_count),
        "percentual_concluido": percentual
    }

@router.get("/{identificador}/historico", summary="Histórico de leituras de um apartamento específico")
async def historico_apartamento(
    identificador: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """Retorna os dados do apartamento e todo o histórico de leituras de hidrômetro dele."""
    apto = None
    if identificador.isdigit():
        apto = db.query(Apartamento).filter(Apartamento.id == int(identificador)).first()
    if not apto:
        apto = db.query(Apartamento).filter(Apartamento.numero == identificador).first()

    if not apto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Apartamento '{identificador}' não encontrado."
        )

    leituras = db.query(Leitura).filter(
        or_(
            Leitura.apartamento_id == apto.id,
            Leitura.apartamento_numero == apto.numero
        )
    ).order_by(Leitura.criado_em.desc()).all()

    lista_leituras = []
    for l in leituras:
        valor_ia = l.leitura_ia or ""
        valor_usuario = l.leitura_usuario or ""
        foi_ajustada = bool(valor_ia and valor_usuario and valor_ia != valor_usuario)

        lista_leituras.append({
            "id": l.id,
            "leitura": valor_usuario,
            "leitura_ia": valor_ia,
            "leitura_usuario": valor_usuario,
            "foi_ajustada": foi_ajustada,
            "confianca": f"{l.confianca_media:.1f}%" if l.confianca_media else "95%",
            "data": l.criado_em.strftime("%d/%m/%Y %H:%M") if l.criado_em else "-",
            "operador": l.usuario_nome or "Operador",
            "observacoes": l.observacoes or "Leitura normal",
            "caminho_foto": l.caminho_foto
        })

    return {
        "apartamento": {
            "id": apto.id,
            "numero": apto.numero,
            "bloco": apto.bloco or "Bloco A",
            "condominio": apto.condominio or "Residencial das Palmeiras",
            "morador": apto.morador or "Não informado"
        },
        "total_leituras": len(lista_leituras),
        "ultima_leitura": lista_leituras[0]["leitura"] if lista_leituras else None,
        "leituras": lista_leituras
    }

@router.post("", summary="Cadastrar novo apartamento rapidamente")
async def criar_apartamento(
    dados: ApartamentoInput,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """Permite ao operador cadastrar um novo apartamento diretamente pelo botão '+' do app."""
    numero_limpo = dados.numero.strip()
    condominio_limpo = (dados.condominio or "Residencial das Palmeiras").strip()
    bloco_limpo = (dados.bloco or "Bloco A").strip()

    existente = db.query(Apartamento).filter(
        Apartamento.numero == numero_limpo,
        Apartamento.condominio == condominio_limpo
    ).first()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O apartamento {numero_limpo} já está cadastrado no condomínio {condominio_limpo}."
        )

    novo = Apartamento(
        numero=numero_limpo,
        bloco=bloco_limpo,
        condominio=condominio_limpo,
        morador=dados.morador
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)

    return {
        "id": novo.id,
        "numero": novo.numero,
        "bloco": novo.bloco,
        "condominio": novo.condominio,
        "mensagem": "Apartamento cadastrado com sucesso!"
    }
