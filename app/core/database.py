from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
from app.core.config import settings

# Arquivo do banco de dados SQLite na raiz do projeto
DB_PATH = settings.BASE_DIR / "hidroreader.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Cria a engine com suporte a múltiplas threads (essencial para FastAPI)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Fábrica de sessões do banco de dados
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe base para os modelos ORM
Base = declarative_base()

def get_db():
    """Dependência para injetar a sessão do banco em cada requisição FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

