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

@router.get("", summary="Listar apartamentos com filtro opcional de condomínio")
async def listar_apartamentos(
    condominio: Optional[str] = Query(None, description="Filtrar por nome do condomínio"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """Retorna a lista de apartamentos, filtrados ou não pelo condomínio selecionado."""
    query = db.query(Apartamento).filter(Apartamento.ativo == True)
    if condominio:
        query = query.filter(Apartamento.condominio == condominio)
    aptos = query.order_by(Apartamento.numero).all()
    return [
        {
            "id": a.id,
            "numero": a.numero,
            "bloco": a.bloco or "Bloco A",
            "condominio": a.condominio or "Residencial das Palmeiras",
            "morador": a.morador
        }
        for a in aptos
    ]

@router.get("/{identificador}/historico", summary="Histórico de leituras de um apartamento específico")
async def historico_apartamento(
    identificador: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """Retorna os dados do apartamento e todo o histórico de leituras de hidrômetro dele."""
    # Busca por ID numérico ou pelo número do apartamento (ex: '101')
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

    # Busca todas as leituras vinculadas a esse apartamento
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
