import os
import time
import json
import hmac
import hashlib
import base64
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from banco.conexao import get_db
from banco.modelos import Usuario

SECRET_KEY = os.getenv("SECRET_KEY", "hidroreader_secret_key_2026")
security_scheme = HTTPBearer(auto_error=False)

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """Verifica se a senha informada confere com o hash salvo."""
    if not senha_hash or "$" not in senha_hash:
        return False
    try:
        salt, hash_gravado = senha_hash.split("$", 1)
        hash_recalculado = hashlib.pbkdf2_hmac('sha256', senha_plana.encode('utf-8'), salt.encode('utf-8'), iterations=100000).hex()
        return hmac.compare_digest(hash_gravado, hash_recalculado)
    except Exception:
        return False

def criar_token(dados: Dict[str, Any], expira_horas: int = 24) -> str:
    """Cria um token assinado com validade configurável."""
    payload = dados.copy()
    payload["exp"] = int(time.time()) + (expira_horas * 3600)
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8').rstrip('=')

    assinatura = hmac.new(SECRET_KEY.encode('utf-8'), payload_b64.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{assinatura}"

CHAVES_VALIDAS = [
    SECRET_KEY,
    "hidroreader_super_secret_mobile_key_2026",
    "hidroreader_secret_key_change_in_production_2026",
    "hidroreader_secret_key_2026"
]

def decodificar_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodifica e valida o token."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, assinatura = token.split(".", 1)

        valido = False
        for k in CHAVES_VALIDAS:
            assinatura_esperada = hmac.new(k.encode('utf-8'), payload_b64.encode('utf-8'), hashlib.sha256).hexdigest()
            if hmac.compare_digest(assinatura, assinatura_esperada):
                valido = True
                break

        if not valido:
            return None

        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += '=' * (4 - rem)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode('utf-8')).decode('utf-8'))
        if "exp" in payload and time.time() > payload["exp"]:
            return None
        return payload
    except Exception:
        return None

def obter_usuario_logado(
    credenciais: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Usuario:
    """Dependência para proteger rotas: valida o token e retorna o usuário logado."""
    if not credenciais or not credenciais.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autenticação não fornecido.")

    payload = decodificar_token(credenciais.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado.")

    user = db.query(Usuario).filter(Usuario.usuario == payload["sub"], Usuario.ativo == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado ou inativo.")

    return user

