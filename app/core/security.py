import hashlib
import hmac
import secrets
import json
import base64
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.core.config import settings

# Chave secreta da aplicação (pode vir de .env ou ser gerada dinamicamente)
SECRET_KEY = getattr(settings, "SECRET_KEY", "hidroreader_super_secret_mobile_key_2026")
TOKEN_EXPIRACAO_HORAS = 24

def gerar_hash_senha(senha: str) -> str:
    """Gera hash seguro da senha usando PBKDF2-HMAC-SHA256 com salt aleatório."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',
        senha.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100000
    )
    return f"{salt}${hash_obj.hex()}"

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """Compara a senha informada com o hash armazenado de forma resistente a timing attacks."""
    if not senha_hash or "$" not in senha_hash:
        return False
    try:
        salt, hash_gravado = senha_hash.split("$", 1)
        hash_recalculado = hashlib.pbkdf2_hmac(
            'sha256',
            senha_plana.encode('utf-8'),
            salt.encode('utf-8'),
            iterations=100000
        ).hex()
        return hmac.compare_digest(hash_gravado, hash_recalculado)
    except Exception:
        return False

def criar_token_acesso(dados: Dict[str, Any], expira_horas: int = TOKEN_EXPIRACAO_HORAS) -> str:
    """Cria um token assinado (HMAC-SHA256) com payload e tempo de expiração."""
    payload = dados.copy()
    exp_timestamp = int(time.time()) + (expira_horas * 3600)
    payload["exp"] = exp_timestamp

    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8').rstrip('=')

    assinatura = hmac.new(
        SECRET_KEY.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}.{assinatura}"

def decodificar_token(token: str) -> Optional[Dict[str, Any]]:
    """Valida a assinatura e expiração do token e retorna seu payload."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, assinatura = token.split(".", 1)
        
        # Validar assinatura
        assinatura_esperada = hmac.new(
            SECRET_KEY.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(assinatura, assinatura_esperada):
            return None

        # Decodificar payload
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += '=' * (4 - rem)
        
        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode('utf-8'))
        payload = json.loads(payload_bytes.decode('utf-8'))

        # Verificar se expirou
        if "exp" in payload and time.time() > payload["exp"]:
            return None

        return payload
    except Exception:
        return None

