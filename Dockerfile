# Imagem base oficial leve do Python
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

WORKDIR /app

# Instalar dependências de sistema para o OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar os módulos limpos da aplicação
COPY rotas/ ./rotas/
COPY banco/ ./banco/
COPY ia/ ./ia/
COPY seguranca/ ./seguranca/
COPY telas/ ./telas/
COPY modelos_ia/ ./modelos_ia/
COPY main.py .
COPY run.py .
COPY .env.example .

# Criar pastas operacionais
RUN mkdir -p uploads tmp

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Inicialização com uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
