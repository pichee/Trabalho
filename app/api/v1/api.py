from fastapi import APIRouter
from app.api.v1.endpoints import leituras, auth, apartamentos

api_router = APIRouter()

# Rotas de Autenticação (/api/v1/auth/login, etc.)
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticação"])

# Rotas de Apartamentos (/api/v1/apartamentos)
api_router.include_router(apartamentos.router, prefix="/apartamentos", tags=["Apartamentos"])

# Rotas de Leitura do Hidrômetro (/api/v1/leituras/processar, etc.)
api_router.include_router(leituras.router, prefix="/leituras", tags=["Leituras de Hidrômetro"])
