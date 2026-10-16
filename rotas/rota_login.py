from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from banco.conexao import get_db
from banco.modelos import Usuario
from seguranca.autenticacao import verificar_senha, criar_token, obter_usuario_logado

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação"])

class LoginRequest(BaseModel):
    usuario: str
    senha: str

@router.post("/login", summary="Login do operador ou administrador")
async def login(dados: LoginRequest, db: Session = Depends(get_db)):
    """Recebe usuário e senha, valida no banco SQLite e retorna o token de acesso."""
    user = db.query(Usuario).filter(Usuario.usuario == dados.usuario.strip()).first()
    if not user or not verificar_senha(dados.senha, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos."
        )

    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado pelo administrador."
        )

    token = criar_token({"sub": user.usuario, "nome": user.nome, "cargo": user.cargo})
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": user.usuario,
        "nome": user.nome,
        "mensagem": "Login efetuado com sucesso!"
    }

@router.get("/me", summary="Dados do operador logado")
async def obter_meu_perfil(usuario: Usuario = Depends(obter_usuario_logado)):
    """Retorna o perfil do usuário logado através do token Bearer."""
    return {
        "id": usuario.id,
        "usuario": usuario.usuario,
        "nome": usuario.nome,
        "cargo": usuario.cargo,
        "ativo": usuario.ativo
    }

