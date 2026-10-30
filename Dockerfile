# Imagem base oficial leve do Python
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    PORT=8000

WORKDIR /app

# Instalar dependências de sistema para o OpenCV e ferramentas de health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar os módulos da aplicação
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

# Health check para orquestradores (Docker, Kubernetes, AWS ECS)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Inicialização com uvicorn compatível com portas dinâmicas de nuvem ($PORT)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
