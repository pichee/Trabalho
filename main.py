from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from contextlib import asynccontextmanager

from banco.conexao import inicializar_banco
from rotas import rota_login, rota_apartamentos, rota_leitura, rota_paginas, rota_dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa o banco de dados e dados padrão no startup
    inicializar_banco()
    yield

app = FastAPI(
    title="HidroReader Mobile API",
    version="1.0.0",
    description="API Mobile-First para Leitura Automática de Hidrômetros com YOLO e Gemini Vision.",
    lifespan=lifespan
)

# Configuração de CORS para permitir acesso local e em produção
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para impedir cache agressivo do navegador em arquivos JS/CSS e HTML
@app.middleware("http")
async def desabilitar_cache_estatico(request, call_next):
    response = await call_next(request)
    caminho = request.url.path
    if caminho.startswith("/static") or caminho in ("/leitor", "/dashboard", "/login", "/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Monta arquivos estáticos (CSS, JS) da pasta telas/
pasta_telas = Path(__file__).parent / "telas"
if pasta_telas.exists():
    app.mount("/static", StaticFiles(directory=str(pasta_telas)), name="static")

# Inclusão das rotas (um arquivo para cada rota)
app.include_router(rota_paginas.router)
app.include_router(rota_login.router)
app.include_router(rota_apartamentos.router)
app.include_router(rota_leitura.router)
app.include_router(rota_dashboard.router)

