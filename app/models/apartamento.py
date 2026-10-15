from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class Apartamento(Base):
    __tablename__ = "apartamentos"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(50), unique=True, index=True, nullable=False) # Ex: "101", "102"
    bloco = Column(String(50), nullable=True, default="Bloco Único")
    morador = Column(String(100), nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Apartamento(id={self.id}, numero='{self.numero}', bloco='{self.bloco}')>"

