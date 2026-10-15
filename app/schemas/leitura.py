from typing import List, Optional
from pydantic import BaseModel, Field

class AlternativaSchema(BaseModel):
    classe: str
    confianca: float

class DigitoInfoSchema(BaseModel):
    posicao: int
    valor_yolo: str
    confianca_yolo: float
    valor_tflite: Optional[str] = None
    confianca_tflite: Optional[float] = None
    incerto: bool = False
    alternativas: List[AlternativaSchema] = []

class LeituraResponseSchema(BaseModel):
    sucesso: bool
    leitura_completa: str = Field(..., description="Leitura final dos dígitos do visor")
    leitura_yolo: Optional[str] = None
    leitura_tflite: Optional[str] = None
    digitos_pretos: Optional[str] = Field(None, description="Dígitos pretos (m³ faturados)")
    digitos_vermelhos: Optional[str] = Field(None, description="Dígitos vermelhos (litros/decimais)")
    analise_cores: Optional[str] = None
    confianca: str = Field("alta", description="Nível de confiança da leitura (alta, media, baixa)")
    confianca_media: float = 0.0
    qualidade_visor: str = Field("Aprovada", description="Avaliação de foco, contraste e nitidez do recorte")
    modelo_utilizado: str = Field("Gemini AI", description="Modelo que realizou a leitura")
    digitos: List[DigitoInfoSchema] = []
    avisos: List[str] = []
