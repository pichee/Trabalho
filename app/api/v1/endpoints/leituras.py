from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.leitura import Leitura
from app.models.apartamento import Apartamento
from app.models.usuario import Usuario
from app.schemas.leitura import LeituraResponseSchema
from app.services.vision.pipeline import visao_service
from app.api.deps import obter_usuario_atual
from app.schemas.auth import UsuarioPerfilSchema

router = APIRouter()

@router.post(
    "/processar",
    response_model=LeituraResponseSchema,
    summary="Processar foto do hidrômetro para um apartamento específico",
    description="Recebe o apartamento selecionado e a foto capturada pelo celular, processa os dígitos e salva a medição no banco SQLite."
)
async def processar_foto_hidrometro(
    foto: UploadFile = File(..., description="Arquivo de imagem do hidrômetro"),
    apartamento: Optional[str] = Form(None, description="Número do apartamento (ex: 101, 102)"),
    db: Session = Depends(get_db),
    usuario_atual: UsuarioPerfilSchema = Depends(obter_usuario_atual)
):
    if not foto.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado não é uma imagem válida."
        )

    try:
        conteudo_bytes = await foto.read()
        resultado = visao_service.processar_imagem(conteudo_bytes, nome_arquivo=foto.filename)

        # Salvar a leitura no banco de dados SQLite associada ao apartamento e ao operador
        apto_texto = apartamento.strip() if apartamento else "Não Informado"
        apto_db = db.query(Apartamento).filter(Apartamento.numero == apto_texto).first()
        user_db = db.query(Usuario).filter(Usuario.usuario == usuario_atual.usuario).first()

        nova_leitura = Leitura(
            apartamento_id=apto_db.id if apto_db else None,
            apartamento_numero=apto_texto,
            usuario_id=user_db.id if user_db else None,
            usuario_nome=usuario_atual.nome,
            leitura_yolo=resultado.leitura_completa or resultado.leitura_yolo,
            leitura_tflite=resultado.leitura_tflite,
            confianca_media=resultado.confianca_media,
            observacoes="; ".join(resultado.avisos) if resultado.avisos else "Leitura normal"
        )
        db.add(nova_leitura)
        db.commit()

        return resultado
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar imagem: {str(e)}"
        )
