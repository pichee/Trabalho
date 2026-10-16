import os
import hashlib
import secrets
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from banco.modelos import Base, Usuario, Apartamento

# Caminho do banco SQLite na raiz
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "hidroreader.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependência do FastAPI para injetar a sessão do banco em cada requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _gerar_hash(senha: str) -> str:
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', senha.encode('utf-8'), salt.encode('utf-8'), iterations=100000)
    return f"{salt}${hash_obj.hex()}"

def inicializar_banco():
    """Garante que as tabelas existam e cadastra os usuários/apartamentos padrão se estiver vazio."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Usuários padrão
        if db.query(Usuario).count() == 0:
            db.add_all([
                Usuario(usuario="admin", senha_hash=_gerar_hash("admin"), nome="Administrador do Sistema", cargo="Administrador"),
                Usuario(usuario="operador", senha_hash=_gerar_hash("123456"), nome="Operador de Campo", cargo="Operador")
            ])
            db.commit()

        # Apartamentos padrão (101 a 404)
        if db.query(Apartamento).count() == 0:
            aptos = []
            for andar in range(1, 5):
                for num in range(1, 5):
                    apto_num = f"{andar}0{num}"
                    aptos.append(Apartamento(numero=apto_num, bloco="Bloco A", condominio="Residencial das Palmeiras"))
            db.add_all(aptos)
            db.commit()
    finally:
        db.close()

