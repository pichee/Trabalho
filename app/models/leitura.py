from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from datetime import datetime
from app.core.database import Base

class Leitura(Base):
    __tablename__ = "leituras"

    id = Column(Integer, primary_key=True, index=True)
    apartamento_id = Column(Integer, ForeignKey("apartamentos.id"), nullable=True)
    apartamento_numero = Column(String(50), nullable=True, index=True) # Ex: "101"
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario_nome = Column(String(100), nullable=True)
    leitura_yolo = Column(String(20), nullable=False)
    leitura_tflite = Column(String(20), nullable=True)
    confianca_media = Column(Float, nullable=False)
    caminho_foto = Column(String(255), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Leitura(id={self.id}, apto='{self.apartamento_numero}', yolo='{self.leitura_yolo}')>"
