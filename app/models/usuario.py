from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String(50), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    nome = Column(String(100), nullable=False)
    cargo = Column(String(50), default="Operador de Campo")
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Usuario(id={self.id}, usuario='{self.usuario}', nome='{self.nome}')>"

