import os
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import text
from banco.conexao import SessionLocal
from ia.leitor_ia import leitor_ia

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
    return {"erro": "Tela de login não encontrada."}

@router.get("/leitor", summary="Tela do leitor de hidrômetro")
async def pagina_leitor():
    arquivo = PASTA_TELAS / "leitor.html"
    if arquivo.exists():
        return FileResponse(str(arquivo), headers=NO_CACHE_HEADERS)
    return {"erro": "Tela do leitor não encontrada."}

@router.get("/dashboard", summary="Tela inicial do aplicativo estilo Nubank")
async def pagina_dashboard():
    arquivo = PASTA_TELAS / "dashboard.html"
    if arquivo.exists():
        return FileResponse(str(arquivo), headers=NO_CACHE_HEADERS)
    return {"erro": "Tela do dashboard não encontrada."}

@router.get("/health", tags=["Status"], summary="Health check para monitoramento")
async def health_check():
    """Verifica a saúde da API, conexão com SQLite e status dos modelos de IA."""
    db_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "banco_sqlite": "conectado" if db_ok else "erro",
        "modelo_yolo": "carregado" if leitor_ia.modelo_yolo is not None else "pendente",
        "gemini_api": "configurado" if bool(os.getenv("GEMINI_API_KEY")) else "chave_ausente"
    }

