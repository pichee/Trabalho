from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.init_db import inicializar_banco_sqlite

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa o banco de dados SQLite e cria tabelas/usuários no startup
    inicializar_banco_sqlite()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API Mobile-First para Leitura Automática de Hidrômetros com Autenticação e Visão Computacional.",
    lifespan=lifespan
)

# Configuração de CORS para permitir acesso do app mobile na rede local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Roteador da API v1 (/api/v1/auth/..., /api/v1/leituras/...)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Montar pasta de arquivos estáticos
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# ==========================================
# ROTAS DE PÁGINAS WEB (MOBILE-FIRST)
# ==========================================
@app.get("/", summary="Rota padrão do aplicativo")
async def rota_padrao():
    """Rota inicial: direciona o usuário diretamente para a tela de login."""
    return RedirectResponse(url="/login")

@app.get("/login", summary="Tela de Login Mobile")
async def tela_login():
    """Exibe o formulário de login para celular."""
    login_file = static_path / "login.html"
    if login_file.exists():
        return FileResponse(str(login_file))
    return {"status": "online", "message": "Tela de login não encontrada."}

@app.get("/leitor", summary="Tela do Leitor de Hidrômetro")
async def tela_leitor():
    """Exibe a interface de câmera e leitura de hidrômetro."""
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"status": "online", "message": "Interface do leitor não encontrada."}

@app.get("/health", tags=["Status"])
async def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}
