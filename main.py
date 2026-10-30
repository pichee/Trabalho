import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Configuração global de logs para monitoramento e manutenção
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("hidroreader.main")

from banco.conexao import inicializar_banco
from rotas import rota_login, rota_apartamentos, rota_leitura, rota_paginas, rota_dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante a existência de todos os diretórios de upload no disco
    Path("uploads/leituras").mkdir(parents=True, exist_ok=True)
    Path("uploads/inidentificaveis").mkdir(parents=True, exist_ok=True)
    Path("tmp").mkdir(parents=True, exist_ok=True)

    # Inicializa banco de dados, migrações e seed inicial
    logger.info("Inicializando infraestrutura e banco de dados...")
    inicializar_banco()
    logger.info("HidroReader pronto para conexões.")
    yield
    logger.info("Encerrando aplicação HidroReader...")

app = FastAPI(
    title="HidroReader Mobile API",
    version="1.0.0",
    description="API Mobile-First para Leitura Automática de Hidrômetros com YOLO e Gemini/OpenAI Vision.",
    lifespan=lifespan
)

# Configuração de CORS compatível com Produção e Desenvolvimento
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*").strip()
if allowed_origins_env == "*":
    origins = ["*"]
    allow_credentials = False
else:
    origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Handler global para capturar erros 500 inesperados e registrar no log do servidor
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erro não tratado na rota {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"sucesso": False, "erro": "Erro interno no servidor. Contate o suporte técnico."}
    )

# Middleware para revalidação de arquivos estáticos sem destruir o estado da página no Android (sem no-store)
@app.middleware("http")
async def desabilitar_cache_estatico(request: Request, call_next):
    response = await call_next(request)
    caminho = request.url.path
    if caminho.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache"
    elif caminho in ("/leitor", "/dashboard", "/login", "/"):
        response.headers["Cache-Control"] = "private, no-cache"
    return response

# Monta arquivos estáticos (CSS, JS, imagens) da pasta telas/
pasta_telas = Path(__file__).resolve().parent / "telas"
if pasta_telas.exists():
    app.mount("/static", StaticFiles(directory=str(pasta_telas)), name="static")

# Monta pasta de uploads para acesso seguro aos comprovantes e fotos das leituras
pasta_uploads = Path(__file__).resolve().parent / "uploads"
pasta_uploads.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(pasta_uploads)), name="uploads")

# Inclusão das rotas modulares
app.include_router(rota_paginas.router)
app.include_router(rota_login.router)
app.include_router(rota_apartamentos.router)
app.include_router(rota_leitura.router)
app.include_router(rota_dashboard.router)
