from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.apartamento import Apartamento
from app.schemas.apartamento import ApartamentoSchema, ApartamentoCreateSchema
from app.api.deps import obter_usuario_atual
from app.schemas.auth import UsuarioPerfilSchema

router = APIRouter()

@router.get(
    "",
    response_model=List[ApartamentoSchema],
    summary="Listar todos os apartamentos para seleção no celular",
    description="Retorna a lista de apartamentos ativos cadastrados para preencher o seletor na tela mobile."
)
async def listar_apartamentos(
    db: Session = Depends(get_db),
    usuario_atual: UsuarioPerfilSchema = Depends(obter_usuario_atual)
):
    apartamentos = db.query(Apartamento).filter(Apartamento.ativo == True).order_by(Apartamento.numero.asc()).all()
    return apartamentos

@router.post(
    "",
    response_model=ApartamentoSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo apartamento"
)
async def criar_apartamento(
    dados: ApartamentoCreateSchema,
    db: Session = Depends(get_db),
    usuario_atual: UsuarioPerfilSchema = Depends(obter_usuario_atual)
):
    existente = db.query(Apartamento).filter(Apartamento.numero == dados.numero.strip()).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Apartamento {dados.numero} já cadastrado."
        )

    novo = Apartamento(
        numero=dados.numero.strip(),
        bloco=dados.bloco.strip() if dados.bloco else "Bloco Único",
        morador=dados.morador.strip() if dados.morador else None,
        ativo=True
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

