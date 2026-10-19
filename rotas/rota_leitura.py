import base64
from datetime import datetime
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends, Request
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
    leitura: Optional[str] = None
    leitura_ia: Optional[str] = None
    leitura_usuario: Optional[str] = None
    confianca_media: Optional[float] = 95.0
    observacoes: Optional[str] = None
    caminho_foto: Optional[str] = None

# Cache em memória das últimas leituras analisadas pela IA
# Garante que o valor detectado pela IA seja imutável e nunca sobrescrito pelo usuário
ULTIMAS_ANALISES_IA = {}

# Cache em memória da última foto pré-carregada por operador (evita decodificar 50MP no celular e sobrevive a reloads)
ULTIMAS_FOTOS_PRECARREGADAS = {}

def registrar_diag_camera(msg: str):
    try:
        with open("camera_diag.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n")
    except Exception:
        pass

@router.api_route("/diag", methods=["GET", "POST"], include_in_schema=False)
async def diag_camera(request: Request, ev: str = "unknown", info: str = ""):
    ip = request.client.host if request.client else "?"
    registrar_diag_camera(f"IP={ip} EV={ev} INFO={info}")
    return {"ok": True}

def otimizar_imagem_servidor(foto_bytes: bytes):
    """Redimensiona a imagem no servidor usando OpenCV para não consumir RAM do celular."""
    try:
        arr = np.frombuffer(foto_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            b64 = "data:image/jpeg;base64," + base64.b64encode(foto_bytes).decode("ascii")
            return foto_bytes, b64

        h, w = img.shape[:2]
        # 1. Versão para análise IA (máx 1400px)
        max_ia = 1400
        if max(h, w) > max_ia:
            escala = max_ia / float(max(h, w))
            img_ia = cv2.resize(img, (int(w * escala), int(h * escala)), interpolation=cv2.INTER_AREA)
        else:
            img_ia = img
        _, buf_ia = cv2.imencode(".jpg", img_ia, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        bytes_ia = buf_ia.tobytes()

        # 2. Miniatura super leve para o visor do celular (máx 640px, ~35KB)
        max_prev = 640
        if max(h, w) > max_prev:
            escala_p = max_prev / float(max(h, w))
            img_prev = cv2.resize(img, (int(w * escala_p), int(h * escala_p)), interpolation=cv2.INTER_AREA)
        else:
            img_prev = img
        _, buf_prev = cv2.imencode(".jpg", img_prev, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
        preview_b64 = "data:image/jpeg;base64," + base64.b64encode(buf_prev.tobytes()).decode("ascii")

        return bytes_ia, preview_b64
    except Exception:
        b64 = "data:image/jpeg;base64," + base64.b64encode(foto_bytes).decode("ascii")
        return foto_bytes, b64

@router.post("/pre-carregar", summary="Recebe a foto da câmera e devolve miniatura leve sem estourar RAM do celular")
async def pre_carregar_foto(
    foto: UploadFile = File(...),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    foto_bytes = await foto.read()
    if not foto_bytes:
        raise HTTPException(status_code=400, detail="Arquivo de foto vazio.")

    registrar_diag_camera(f"PRE_CARREGAR user={usuario.id} nome={foto.filename} bytes={len(foto_bytes)}")
    bytes_ia, preview_b64 = otimizar_imagem_servidor(foto_bytes)
    tamanho_kb = max(1, round(len(bytes_ia) / 1024))

    ULTIMAS_FOTOS_PRECARREGADAS[usuario.id] = {
        "bytes": bytes_ia,
        "preview_b64": preview_b64,
        "tamanho_kb": tamanho_kb,
        "timestamp": datetime.now().isoformat()
    }
    return {
        "sucesso": True,
        "preview_b64": preview_b64,
        "tamanho_kb": tamanho_kb
    }

@router.get("/pre-carregar", summary="Recupera a última foto pré-carregada caso o celular tenha dado refresh")
async def obter_foto_pre_carregada(usuario: Usuario = Depends(obter_usuario_logado)):
    dados = ULTIMAS_FOTOS_PRECARREGADAS.get(usuario.id)
    if not dados:
        return {"tem_foto": False}
    return {
        "tem_foto": True,
        "preview_b64": dados["preview_b64"],
        "tamanho_kb": dados["tamanho_kb"]
    }

@router.delete("/pre-carregar", summary="Limpa a foto pré-carregada pendente")
async def limpar_foto_pre_carregada(usuario: Usuario = Depends(obter_usuario_logado)):
    ULTIMAS_FOTOS_PRECARREGADAS.pop(usuario.id, None)
    return {"sucesso": True}

@router.post("/analisar", summary="Analisar foto do hidrômetro com IA sem salvar no banco")
async def analisar_foto(
    foto: Optional[UploadFile] = File(None, description="Foto capturada da câmera (opcional se já pré-carregada)"),
    apartamento: Optional[str] = Form(None, description="Número do apartamento"),
    condominio: Optional[str] = Form(None, description="Nome do condomínio"),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """
    1ª Etapa: Análise Preditiva com IA
    - Valida o arquivo de imagem (ou utiliza a foto pré-carregada na sessão do operador).
    - O YOLO recorta o visor e o Gemini Vision faz a leitura cromática.
    - Retorna a predição para conferência humana antes de salvar no banco de dados.
    """
    try:
        foto_bytes = None
        if foto is not None and foto.filename:
            if foto.content_type and not foto.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O arquivo enviado precisa ser uma imagem (JPG, PNG, JPEG)."
                )
            lidos = await foto.read()
            if lidos:
                foto_bytes, preview_b64 = otimizar_imagem_servidor(lidos)
                ULTIMAS_FOTOS_PRECARREGADAS[usuario.id] = {
                    "bytes": foto_bytes,
                    "preview_b64": preview_b64,
                    "tamanho_kb": max(1, round(len(foto_bytes) / 1024)),
                    "timestamp": datetime.now().isoformat()
                }

        if not foto_bytes:
            pre = ULTIMAS_FOTOS_PRECARREGADAS.get(usuario.id)
            if pre and pre.get("bytes"):
                foto_bytes = pre["bytes"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nenhuma foto recebida para análise."
                )

        resultado = leitor_ia.processar_foto(foto_bytes)
        
        apto_limpo = (apartamento or "").strip()
        condo_limpo = (condominio or "Residencial das Palmeiras").strip()
        valor_ia_lido = str(resultado.get("leitura_ia") or resultado.get("leitura_completa") or "").strip()

        resultado["apartamento"] = apto_limpo
        resultado["condominio"] = condo_limpo
        resultado["leitura_ia"] = valor_ia_lido

        # Registra no servidor a análise da IA de forma imutável para este operador
        dados_analise = {
            "leitura_ia": valor_ia_lido,
            "apartamento": apto_limpo,
            "condominio": condo_limpo,
            "confianca_media": resultado.get("confianca_media", 95.0),
            "avisos": resultado.get("avisos", [])
        }
        ULTIMAS_ANALISES_IA[usuario.id] = dados_analise
        if apto_limpo:
            ULTIMAS_ANALISES_IA[f"{usuario.id}:{apto_limpo}"] = dados_analise

        return resultado
    except HTTPException:
        raise
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
    - leitura_ia: É SEMPRE o valor original lido pela IA (imutável).
    - leitura_usuario: É o valor conferido ou ajustado manualmente pelo usuário.
    """
    apto_texto = dados.apartamento.strip()
    condo_texto = (dados.condominio or "Residencial das Palmeiras").strip()

    # 1. Recupera o valor original que a IA detectou da análise recente no servidor
    chave_especifica = f"{usuario.id}:{apto_texto}"
    analise_original = ULTIMAS_ANALISES_IA.get(chave_especifica) or ULTIMAS_ANALISES_IA.get(usuario.id)

    # 2. Leitura do Usuário: o valor que o usuário confirmou/editou no campo de texto
    valor_usuario = (dados.leitura_usuario or dados.leitura or "").strip()

    # 3. Leitura da IA: valor detectado pela IA (nunca alterado pelo usuário)
    if analise_original and analise_original.get("leitura_ia"):
        valor_ia = analise_original["leitura_ia"].strip()
    elif dados.leitura_ia and dados.leitura_ia.strip():
        valor_ia = dados.leitura_ia.strip()
    else:
        valor_ia = valor_usuario

    if not valor_usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O valor da leitura não pode estar vazio."
        )

    # Limpa a memória de análise e de foto pré-carregada consumidas
    ULTIMAS_ANALISES_IA.pop(chave_especifica, None)
    ULTIMAS_ANALISES_IA.pop(usuario.id, None)
    ULTIMAS_FOTOS_PRECARREGADAS.pop(usuario.id, None)

    # Busca o apartamento vinculado
    apto_db = db.query(Apartamento).filter(
        Apartamento.numero == apto_texto,
        Apartamento.condominio == condo_texto
    ).first()

    if not apto_db:
        # Tenta buscar apenas pelo número se não achar pelo condomínio exato
        apto_db = db.query(Apartamento).filter(Apartamento.numero == apto_texto).first()

    obs = (dados.observacoes or "").strip()
    if valor_ia and valor_usuario and valor_ia != valor_usuario:
        if not obs or obs in ("Leitura normal", "Leitura confirmada pelo operador"):
            obs = f"Ajustado manualmente pelo operador (IA leu: {valor_ia})"
        elif f"IA leu: {valor_ia}" not in obs:
            obs = f"{obs} (IA leu: {valor_ia})"
    elif not obs:
        obs = "Leitura confirmada pelo operador"

    nova_leitura = Leitura(
        apartamento_id=apto_db.id if apto_db else None,
        apartamento_numero=apto_texto,
        usuario_id=usuario.id,
        usuario_nome=usuario.nome,
        leitura_ia=valor_ia,
        leitura_usuario=valor_usuario,
        confianca_media=dados.confianca_media or 95.0,
        caminho_foto=dados.caminho_foto,
        observacoes=obs
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
            "leitura": nova_leitura.leitura_usuario,
            "leitura_ia": nova_leitura.leitura_ia,
            "leitura_usuario": nova_leitura.leitura_usuario,
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
            leitura_ia=resultado["leitura_completa"],
            leitura_usuario=resultado["leitura_completa"],
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


