from pydantic import BaseModel, Field
from typing import Optional

class LoginRequestSchema(BaseModel):
    usuario: str = Field(..., example="admin", description="Nome de usuário ou e-mail de acesso")
    senha: str = Field(..., example="123456", description="Senha do usuário")

class TokenResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: str
    nome: Optional[str] = None
    mensagem: str = "Login efetuado com sucesso!"

class UsuarioPerfilSchema(BaseModel):
    usuario: str
    nome: str
    cargo: str = "Operador de Campo"
    ativo: bool = True

