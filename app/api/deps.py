from fastapi import Header, HTTPException, status, Depends
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario
from app.core.security import decodificar_token
from app.schemas.auth import UsuarioPerfilSchema

async def obter_usuario_atual(
    authorization: Optional[str] = Header(None, description="Token Bearer no cabeçalho Authorization"),
    db: Session = Depends(get_db)
) -> UsuarioPerfilSchema:
    """Valida o token JWT/HMAC enviado no cabeçalho e busca o usuário correspondente no SQLite."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado. Por favor, realize o login.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split("Bearer ", 1)[1].strip()
    payload = decodificar_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario_id = payload["sub"]

    # Buscar usuário no SQLite
    usuario_db = db.query(Usuario).filter(Usuario.usuario == usuario_id).first()

    if not usuario_db or not usuario_db.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou desativado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UsuarioPerfilSchema(
        usuario=usuario_db.usuario,
        nome=usuario_db.nome,
        cargo=usuario_db.cargo,
        ativo=usuario_db.ativo
    )

    return UsuarioPerfilSchema(
        usuario=usuario_db.usuario,
        nome=usuario_db.nome,
        cargo=usuario_db.cargo,
        ativo=usuario_db.ativo
    )

