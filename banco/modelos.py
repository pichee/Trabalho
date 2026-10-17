from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from datetime import datetime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

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


class Apartamento(Base):
    __tablename__ = "apartamentos"

    id = Column(Integer, primary_key=True, index=True)
    condominio = Column(String(100), nullable=True, default="Residencial das Palmeiras")
    numero = Column(String(50), unique=True, index=True, nullable=False)
    bloco = Column(String(50), nullable=True, default="Bloco A")
    morador = Column(String(100), nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Apartamento(numero='{self.numero}', bloco='{self.bloco}', condominio='{self.condominio}')>"


class Leitura(Base):
    __tablename__ = "leituras"

    id = Column(Integer, primary_key=True, index=True)
    apartamento_id = Column(Integer, ForeignKey("apartamentos.id"), nullable=True)
    apartamento_numero = Column(String(50), nullable=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario_nome = Column(String(100), nullable=True)
    leitura_ia = Column(String(50), nullable=True)
    leitura_usuario = Column(String(50), nullable=False)
    confianca_media = Column(Float, nullable=False)
    caminho_foto = Column(String(255), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Leitura(id={self.id}, apto='{self.apartamento_numero}', ia='{self.leitura_ia}', usuario='{self.leitura_usuario}')>"

