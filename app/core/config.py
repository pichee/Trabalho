import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "HidroReader Mobile API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Diretórios Base
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    TMP_DIR: Path = BASE_DIR / "tmp"
    MODELS_DIR: Path = BASE_DIR / "modelos"

    # Modelos de Machine Learning
    MODELO_VISOR: str = str(BASE_DIR / "pegarvisor.pt")
    MODELO_DIGITOS: str = str(BASE_DIR / "digitos.pt")
    MODELO_TFLITE: str = str(BASE_DIR / "dig-class11_2000_s2.tflite")

    # Limiares de Detecção
    CONFIANCA_MIN_VISOR: float = 0.25
    CONFIANCA_MIN_DIGITOS: float = 0.15
    LIMIAR_BAIXA_CONFIANCA: float = 0.60

    # Configurações de API Externa
    GEMINI_API_KEY: str = ""

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Garantir existência de pastas operacionais
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.TMP_DIR, exist_ok=True)

