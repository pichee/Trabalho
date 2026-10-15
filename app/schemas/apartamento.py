from pydantic import BaseModel
from typing import Optional

class ApartamentoSchema(BaseModel):
    id: int
    numero: str
    bloco: Optional[str] = "Bloco Único"
    morador: Optional[str] = None
    ativo: bool = True

    class Config:
        from_attributes = True

class ApartamentoCreateSchema(BaseModel):
    numero: str
    bloco: Optional[str] = "Bloco Único"
    morador: Optional[str] = None

