import os
import base64
import secrets
import logging
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from banco.conexao import get_db
from banco.modelos import Leitura, Apartamento, Usuario, FotoInidentificavel
from seguranca.autenticacao import obter_usuario_logado
from ia.leitor_ia import leitor_ia

logger = logging.getLogger("hidroreader.camera")

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
ULTIMAS_ANALISES_IA = {}

# Cache em memória da última foto pré-carregada por operador
ULTIMAS_FOTOS_PRECARREGADAS = {}

def registrar_diag_camera(msg: str):
    logger.info(f"[CAMERA_DIAG] {msg}")
    try:
        with open("camera_diag.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n")
    except Exception:
        pass

def salvar_foto_leitura(foto_bytes: bytes, apartamento: str, condominio: str) -> str:
    """Salva a foto da leitura aprovada/analisada no disco em uploads/leituras/ e retorna o caminho relativo."""
    try:
        agora = datetime.now()
        subpasta = agora.strftime("%Y/%m")
        pasta = Path("uploads/leituras") / subpasta
        pasta.mkdir(parents=True, exist_ok=True)

        apto_limpo = (apartamento or "geral").strip().replace(" ", "_").replace("/", "-")
        timestamp = agora.strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"leitura_{apto_limpo}_{timestamp}_{secrets.token_hex(4)}.jpg"
        caminho_completo = pasta / nome_arquivo

        with open(caminho_completo, "wb") as f:
            f.write(foto_bytes)

        caminho_relativo = f"/uploads/leituras/{subpasta}/{nome_arquivo}".replace("\\", "/")
        logger.info(f"Foto de leitura salva com sucesso: {caminho_relativo}")
        return caminho_relativo
    except Exception as e:
        logger.error(f"Erro ao salvar foto da leitura no disco: {e}")
        return ""

def salvar_foto_inidentificavel(
    foto_bytes: bytes,
    motivo: str,
    apartamento: str,
    condominio: str,
    usuario: Usuario,
    db: Session,
    modelo_tentado: str = "OpenAI gpt-4o-mini"
) -> str:
    """Salva no disco e registra na tabela fotos_inidentificaveis para auditoria."""
    try:
        pasta = Path("uploads/inidentificaveis")
        pasta.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"inid_{timestamp}_{secrets.token_hex(4)}.jpg"
        caminho_completo = pasta / nome_arquivo

        with open(caminho_completo, "wb") as f:
            f.write(foto_bytes)

        caminho_relativo = f"/uploads/inidentificaveis/{nome_arquivo}"

        apto_db = db.query(Apartamento).filter(
            Apartamento.numero == apartamento.strip()
        ).first() if apartamento else None

        registro = FotoInidentificavel(
            apartamento_id=apto_db.id if apto_db else None,
            apartamento_numero=apartamento.strip() if apartamento else "Não Informado",
            condominio=condominio.strip() if condominio else "Residencial das Palmeiras",
            usuario_id=usuario.id,
            usuario_nome=usuario.nome,
            motivo_falha=motivo,
            caminho_foto=caminho_relativo,
            modelo_tentado=modelo_tentado
        )
        db.add(registro)
        db.commit()
        db.refresh(registro)
        logger.info(f"Foto inidentificável salva com sucesso! ID={registro.id}, Apto={apartamento}, Motivo={motivo}")
        return caminho_relativo
    except Exception as e:
        logger.error(f"Erro ao registrar foto inidentificável no banco: {e}")
        return ""

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

@router.post("/analisar", summary="Analisar foto do hidrômetro com IA e salvar foto no disco")
async def analisar_foto(
    foto: Optional[UploadFile] = File(None, description="Foto capturada da câmera (opcional se já pré-carregada)"),
    apartamento: Optional[str] = Form(None, description="Número do apartamento"),
    condominio: Optional[str] = Form(None, description="Nome do condomínio"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """
    1ª Etapa: Análise Preditiva com IA
    - Valida o arquivo de imagem (ou utiliza a foto pré-carregada).
    - Salva TODA foto no disco para auditoria permanente (uploads/leituras/).
    - O YOLO recorta o visor e o ChatGPT/Gemini Vision faz a leitura cromática.
    - Se a IA não identificar, registra também na tabela fotos_inidentificaveis.
    """
    apto_limpo = (apartamento or "").strip()
    condo_limpo = (condominio or "Residencial das Palmeiras").strip()
    foto_bytes = None

    try:
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

        # SALVA A FOTO NO DISCO PERMANENTEMENTE (Atendendo à exigência: toda foto deve ser salva)
        caminho_foto_salva = salvar_foto_leitura(foto_bytes, apto_limpo, condo_limpo)

        # Processamento de IA
        resultado = leitor_ia.processar_foto(foto_bytes)
        valor_ia_lido = str(resultado.get("leitura_ia") or resultado.get("leitura_completa") or "").strip()

        # Verifica se o modelo conseguiu extrair dígitos numéricos válidos
        tem_numeros = any(c.isdigit() for c in valor_ia_lido)
        if not tem_numeros:
            motivo = "A IA analisou a imagem mas não identificou dígitos legíveis no mostrador."
            caminho_inid = salvar_foto_inidentificavel(
                foto_bytes=foto_bytes,
                motivo=motivo,
                apartamento=apto_limpo,
                condominio=condo_limpo,
                usuario=usuario,
                db=db,
                modelo_tentado=resultado.get("modelo_utilizado", "OpenAI gpt-4o-mini")
            )
            resultado["sucesso"] = False
            resultado["inidentificavel"] = True
            resultado["motivo_inidentificavel"] = motivo
            resultado["caminho_foto_inidentificavel"] = caminho_inid
            resultado["avisos"].append(motivo)

        resultado["apartamento"] = apto_limpo
        resultado["condominio"] = condo_limpo
        resultado["leitura_ia"] = valor_ia_lido
        resultado["caminho_foto"] = caminho_foto_salva

        # Registra no servidor a análise da IA com o caminho permanente da foto
        dados_analise = {
            "leitura_ia": valor_ia_lido,
            "apartamento": apto_limpo,
            "condominio": condo_limpo,
            "confianca_media": resultado.get("confianca_media", 95.0),
            "avisos": resultado.get("avisos", []),
            "caminho_foto": caminho_foto_salva
        }
        ULTIMAS_ANALISES_IA[usuario.id] = dados_analise
        if apto_limpo:
            ULTIMAS_ANALISES_IA[f"{usuario.id}:{apto_limpo}"] = dados_analise

        if usuario.id in ULTIMAS_FOTOS_PRECARREGADAS:
            ULTIMAS_FOTOS_PRECARREGADAS[usuario.id]["caminho_foto"] = caminho_foto_salva

        return resultado
    except HTTPException:
        raise
    except ValueError as ve:
        motivo = str(ve)
        if foto_bytes:
            salvar_foto_inidentificavel(foto_bytes, motivo, apto_limpo, condo_limpo, usuario, db)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Foto inidentificável: {motivo}. Registrada na tabela de fotos inidentificáveis para auditoria."
        )
    except Exception as e:
        motivo = f"Falha na IA: {str(e)}"
        if foto_bytes:
            salvar_foto_inidentificavel(foto_bytes, motivo, apto_limpo, condo_limpo, usuario, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Não foi possível ler os números: {str(e)}. A imagem foi salva na tabela de fotos inidentificáveis."
        )

@router.get("/inidentificaveis", summary="Listar fotos que a IA não conseguiu identificar")
async def listar_fotos_inidentificaveis(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """Retorna o histórico de fotos que a IA não conseguiu identificar para auditoria e conferência."""
    registros = db.query(FotoInidentificavel).order_by(FotoInidentificavel.criado_em.desc()).limit(100).all()
    return [
        {
            "id": r.id,
            "apartamento": r.apartamento_numero,
            "condominio": r.condominio,
            "operador": r.usuario_nome,
            "motivo_falha": r.motivo_falha,
            "caminho_foto": r.caminho_foto,
            "modelo_tentado": r.modelo_tentado,
            "data": r.criado_em.strftime("%d/%m/%Y %H:%M:%S") if r.criado_em else "-"
        }
        for r in registros
    ]

@router.post("/confirmar", summary="Confirmar e salvar a medição no banco de dados com vínculo da foto")
async def confirmar_leitura(
    dados: ConfirmarLeituraInput,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """
    2ª Etapa: Confirmação e Persistência
    - Salva a medição no banco apenas após a confirmação explícita do operador.
    - Garante que a foto correspondente seja vinculada à coluna caminho_foto.
    """
    apto_texto = dados.apartamento.strip()
    condo_texto = (dados.condominio or "Residencial das Palmeiras").strip()

    chave_especifica = f"{usuario.id}:{apto_texto}"
    analise_original = ULTIMAS_ANALISES_IA.get(chave_especifica) or ULTIMAS_ANALISES_IA.get(usuario.id)
    foto_pre = ULTIMAS_FOTOS_PRECARREGADAS.get(usuario.id)

    valor_usuario = (dados.leitura_usuario or dados.leitura or "").strip()

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

    # Recupera o caminho permanente da foto salva
    caminho_foto_final = dados.caminho_foto
    if not caminho_foto_final and analise_original:
        caminho_foto_final = analise_original.get("caminho_foto")
    if not caminho_foto_final and foto_pre:
        caminho_foto_final = foto_pre.get("caminho_foto")
    if not caminho_foto_final and foto_pre and foto_pre.get("bytes"):
        caminho_foto_final = salvar_foto_leitura(foto_pre["bytes"], apto_texto, condo_texto)

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
        caminho_foto=caminho_foto_final,
        observacoes=obs
    )

    try:
        db.add(nova_leitura)
        db.commit()
        db.refresh(nova_leitura)
        return {
            "sucesso": True,
            "mensagem": "Medição confirmada e salva com sucesso com foto arquivada!",
            "leitura_id": nova_leitura.id,
            "apartamento": apto_texto,
            "condominio": condo_texto,
            "leitura": nova_leitura.leitura_usuario,
            "leitura_ia": nova_leitura.leitura_ia,
            "leitura_usuario": nova_leitura.leitura_usuario,
            "caminho_foto": nova_leitura.caminho_foto,
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
    """Executa a análise, salva a foto e persiste diretamente no banco."""
    if not foto.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado precisa ser uma imagem (JPG, PNG, JPEG)."
        )

    foto_bytes = await foto.read()
    apto_texto = apartamento.strip() if apartamento else "Não Informado"

    # Salva a foto no disco
    caminho_foto_salva = salvar_foto_leitura(foto_bytes, apto_texto, "Residencial das Palmeiras")

    try:
        resultado = leitor_ia.processar_foto(foto_bytes)
        apto_db = db.query(Apartamento).filter(Apartamento.numero == apto_texto).first()

        nova_leitura = Leitura(
            apartamento_id=apto_db.id if apto_db else None,
            apartamento_numero=apto_texto,
            usuario_id=usuario.id,
            usuario_nome=usuario.nome,
            leitura_ia=resultado["leitura_completa"],
            leitura_usuario=resultado["leitura_completa"],
            confianca_media=resultado["confianca_media"],
            caminho_foto=caminho_foto_salva,
            observacoes="; ".join(resultado["avisos"]) if resultado["avisos"] else "Leitura normal"
        )
        db.add(nova_leitura)
        db.commit()
        db.refresh(nova_leitura)

        resultado["caminho_foto"] = caminho_foto_salva
        resultado["leitura_id"] = nova_leitura.id
        return resultado
    except ValueError as ve:
        salvar_foto_inidentificavel(foto_bytes, str(ve), apto_texto, "Residencial das Palmeiras", usuario, db)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        db.rollback()
        salvar_foto_inidentificavel(foto_bytes, str(e), apto_texto, "Residencial das Palmeiras", usuario, db)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao processar imagem: {str(e)}")
