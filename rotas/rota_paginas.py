import os
from pathlib import Path
from fastapi import APIRouter, Response, status, Depends
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from sqlalchemy import text
from banco.conexao import SessionLocal, engine
from ia.leitor_ia import leitor_ia, obter_chave_gemini, obter_chave_openai, obter_modelos_gemini
from seguranca.autenticacao import obter_usuario_logado
from banco.modelos import Usuario

router = APIRouter(tags=["Páginas Web"])

PASTA_TELAS = Path(__file__).resolve().parent.parent / "telas"

NO_CACHE_HEADERS = {
    "Cache-Control": "private, no-cache"
}

@router.get("/", summary="Redireciona para o login")
async def inicio():
    return RedirectResponse(url="/login")

@router.get("/login", summary="Tela de login mobile")
async def pagina_login():
    arquivo = PASTA_TELAS / "login.html"
    if arquivo.exists():
        return FileResponse(str(arquivo), headers=NO_CACHE_HEADERS)
    return JSONResponse(status_code=404, content={"erro": "Tela de login não encontrada."})

@router.get("/leitor", summary="Tela do leitor de hidrômetro")
async def pagina_leitor():
    arquivo = PASTA_TELAS / "leitor.html"
    if arquivo.exists():
        return FileResponse(str(arquivo), headers=NO_CACHE_HEADERS)
    return JSONResponse(status_code=404, content={"erro": "Tela do leitor não encontrada."})

@router.get("/dashboard", summary="Tela inicial do aplicativo estilo Nubank")
async def pagina_dashboard():
    arquivo = PASTA_TELAS / "dashboard.html"
    if arquivo.exists():
        return FileResponse(str(arquivo), headers=NO_CACHE_HEADERS)
    return JSONResponse(status_code=404, content={"erro": "Tela do dashboard não encontrada."})

@router.get("/health", tags=["Status"], summary="Health check para monitoramento e orquestradores")
async def health_check():
    """Verifica a integridade da API, conexão com o banco e disponibilidade da IA."""
    db_ok = True
    db_erro = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_ok = False
        db_erro = str(e)

    tem_chave_gemini = bool(obter_chave_gemini())
    tem_chave_openai = bool(obter_chave_openai())
    tem_yolo = leitor_ia.modelo_yolo is not None
    provedor_ativo = os.getenv("PROVEDOR_IA", "openai if tem_openai else gemini").strip()

    saudavel = db_ok and (tem_chave_openai or tem_chave_gemini)

    resposta = {
        "status": "healthy" if saudavel else "degraded",
        "ambiente": os.getenv("ENVIRONMENT", "development"),
        "banco_dados": {
            "tipo": engine.name,
            "status": "conectado" if db_ok else "erro",
            "detalhes": db_erro
        },
        "ia": {
            "modelo_yolo": "carregado" if tem_yolo else "pendente",
            "openai_api": "configurado" if tem_chave_openai else "chave_ausente",
            "gemini_api": "configurado" if tem_chave_gemini else "chave_ausente",
            "provedor_configurado": provedor_ativo,
            "dupla_verificacao": tem_chave_openai and tem_chave_gemini
        }
    }

    status_http = status.HTTP_200_OK if saudavel else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_http, content=resposta)

@router.get("/api/v1/sistema/info", tags=["Status"], summary="Informações do sistema para manutenção")
async def info_sistema(usuario: Usuario = Depends(obter_usuario_logado)):
    """Retorna detalhes do ambiente e sistema (restrito a usuários autenticados)."""
    return {
        "aplicacao": "HidroReader Mobile",
        "versao": "1.0.0",
        "ambiente": os.getenv("ENVIRONMENT", "development"),
        "banco_tipo": engine.name,
        "usuario_logado": usuario.usuario,
        "cargo": usuario.cargo,
        "openai_configurado": bool(obter_chave_openai()),
        "gemini_configurado": bool(obter_chave_gemini()),
        "provedor_ia": os.getenv("PROVEDOR_IA", "openai"),
        "modelo_openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "modelos_gemini": obter_modelos_gemini()
    }
