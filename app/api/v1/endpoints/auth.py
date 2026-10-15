from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequestSchema, TokenResponseSchema, UsuarioPerfilSchema
from app.core.security import verificar_senha, criar_token_acesso
from app.api.deps import obter_usuario_atual

router = APIRouter()

@router.post(
    "/login",
    response_model=TokenResponseSchema,
    summary="Efetuar login no aplicativo mobile (SQLite)",
    description="Valida o usuário e senha cadastrados no banco SQLite e retorna o token de acesso."
)
async def login(
    credenciais: LoginRequestSchema,
    db: Session = Depends(get_db)
):
    # Buscar usuário no banco SQLite
    usuario_db = db.query(Usuario).filter(
        Usuario.usuario == credenciais.usuario.strip().lower()
    ).first()

    if not usuario_db or not verificar_senha(credenciais.senha, usuario_db.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos."
        )

    if not usuario_db.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este usuário está inativo no sistema."
        )

    # Gerar token assinado com o identificador do usuário
    token = criar_token_acesso(dados={"sub": usuario_db.usuario})

    return TokenResponseSchema(
        access_token=token,
        token_type="bearer",
        usuario=usuario_db.usuario,
        nome=usuario_db.nome,
        mensagem="Login efetuado com sucesso!"
    )

@router.get(
    "/me",
    response_model=UsuarioPerfilSchema,
    summary="Obter perfil do usuário autenticado a partir do SQLite"
)
async def perfil_usuario(usuario_atual: UsuarioPerfilSchema = Depends(obter_usuario_atual)):
    return usuario_atual
