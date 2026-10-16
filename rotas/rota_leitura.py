from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from banco.conexao import get_db
from banco.modelos import Leitura, Apartamento, Usuario
from seguranca.autenticacao import obter_usuario_logado
from ia.leitor_ia import leitor_ia

router = APIRouter(prefix="/api/v1/leituras", tags=["Leituras"])

class ConfirmarLeituraInput(BaseModel):
    apartamento: str
    condominio: Optional[str] = "Residencial das Palmeiras"
    leitura: str
    confianca_media: Optional[float] = 95.0
    observacoes: Optional[str] = "Leitura normal"
    caminho_foto: Optional[str] = None

@router.post("/analisar", summary="Analisar foto do hidrômetro com IA sem salvar no banco")
async def analisar_foto(
    foto: UploadFile = File(..., description="Foto capturada da câmera"),
    apartamento: Optional[str] = Form(None, description="Número do apartamento"),
    condominio: Optional[str] = Form(None, description="Nome do condomínio"),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """
    1ª Etapa: Análise Preditiva com IA
    - Valida o arquivo de imagem.
    - O YOLO recorta o visor e o Gemini Vision faz a leitura cromática.
    - Retorna a predição para conferência humana antes de salvar no banco de dados.
    """
    if not foto.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado precisa ser uma imagem (JPG, PNG, JPEG)."
        )

    try:
        foto_bytes = await foto.read()
        resultado = leitor_ia.processar_foto(foto_bytes)
        resultado["apartamento"] = apartamento
        resultado["condominio"] = condominio
        return resultado
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao analisar imagem: {str(e)}")

@router.post("/confirmar", summary="Confirmar e salvar a medição no banco de dados")
async def confirmar_leitura(
    dados: ConfirmarLeituraInput,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """
    2ª Etapa: Confirmação e Persistência
    - Salva a medição no banco apenas após a confirmação explícita do operador.
    """
    apto_texto = dados.apartamento.strip()
    condo_texto = (dados.condominio or "Residencial das Palmeiras").strip()

    # Busca o apartamento vinculado
    apto_db = db.query(Apartamento).filter(
        Apartamento.numero == apto_texto,
        Apartamento.condominio == condo_texto
    ).first()

    if not apto_db:
        # Tenta buscar apenas pelo número se não achar pelo condomínio exato
        apto_db = db.query(Apartamento).filter(Apartamento.numero == apto_texto).first()

    nova_leitura = Leitura(
        apartamento_id=apto_db.id if apto_db else None,
        apartamento_numero=apto_texto,
        usuario_id=usuario.id,
        usuario_nome=usuario.nome,
        leitura_yolo=dados.leitura.strip(),
        confianca_media=dados.confianca_media or 95.0,
        caminho_foto=dados.caminho_foto,
        observacoes=dados.observacoes or "Leitura confirmada pelo operador"
    )

    try:
        db.add(nova_leitura)
        db.commit()
        db.refresh(nova_leitura)
        return {
            "sucesso": True,
            "mensagem": "Medição confirmada e salva com sucesso!",
            "leitura_id": nova_leitura.id,
            "apartamento": apto_texto,
            "condominio": condo_texto,
            "leitura": nova_leitura.leitura_yolo,
            "data": nova_leitura.criado_em.strftime("%d/%m/%Y %H:%M")
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao salvar leitura: {str(e)}")

@router.post("/processar", summary="Processar e salvar diretamente (compatibilidade)")
async def processar_foto(
    foto: UploadFile = File(..., description="Foto capturada pelo smartphone"),
    apartamento: Optional[str] = Form(None, description="Número do apartamento (ex: 101)"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """Executa a análise e salva diretamente (mantido para retrocompatibilidade)."""
    if not foto.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado precisa ser uma imagem (JPG, PNG, JPEG)."
        )

    try:
        foto_bytes = await foto.read()
        resultado = leitor_ia.processar_foto(foto_bytes)

        apto_texto = apartamento.strip() if apartamento else "Não Informado"
        apto_db = db.query(Apartamento).filter(Apartamento.numero == apto_texto).first()

        nova_leitura = Leitura(
            apartamento_id=apto_db.id if apto_db else None,
            apartamento_numero=apto_texto,
            usuario_id=usuario.id,
            usuario_nome=usuario.nome,
            leitura_yolo=resultado["leitura_completa"],
            confianca_media=resultado["confianca_media"],
            observacoes="; ".join(resultado["avisos"]) if resultado["avisos"] else "Leitura normal"
        )
        db.add(nova_leitura)
        db.commit()

        return resultado
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao processar imagem: {str(e)}")


