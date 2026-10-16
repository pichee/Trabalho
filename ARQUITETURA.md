# 🏛️ Arquitetura e Guia de Diretórios - HidroReader

Este documento descreve detalhadamente o padrão arquitetural do **HidroReader Mobile**, suas camadas de responsabilidade e as diretrizes para manutenção e deploy em **produção**.

---

## 🎯 Princípios Arquiteturais

O sistema é construído sobre os pilares da **Clean Architecture** adaptada para **FastAPI**:

1. **Separação Estrita de Responsabilidades:** Cada diretório possui um único propósito bem definido.
2. **Desacoplamento:** A interface web (`app/static/`) não acessa banco de dados; a API (`app/api/`) não implementa redes neurais diretamente; a IA (`app/services/vision/`) não lida com requisições HTTP.
3. **Pronto para Produção (12-Factor App):** Configurações externas via variáveis de ambiente (`.env`), suporte a containers (`Docker`), persistência flexível (SQLite local ou PostgreSQL em produção) e health checks para monitoramento.

---

## 📂 Guia Detalhado de Cada Diretório

### 1. `app/` — Núcleo da Aplicação
Contém todo o código da aplicação. Nada de regras de negócio ou telas deve ficar fora de `app/`.

| Subdiretório | Responsabilidade | O que DEVE ter aqui | O que NÃO deve ter aqui |
| :--- | :--- | :--- | :--- |
| **`app/api/`** | **Camada HTTP** | Roteadores FastAPI, endpoints REST, injeção de dependências (`deps.py`), validação de tokens JWT. | Consultas SQL diretas, lógica pesada de visão computacional. |
| **`app/core/`** | **Fundação do Sistema** | Leitura de `.env` (`config.py`), conexão com banco (`database.py`), criptografia e JWT (`security.py`), scripts de seed (`init_db.py`). | Rotas HTTP, templates visuais. |
| **`app/models/`** | **Modelos ORM (Banco)** | Classes SQLAlchemy que mapeiam tabelas relacionais (`Usuario`, `Apartamento`, `Leitura`). | Schemas Pydantic, lógica de rotas. |
| **`app/schemas/`** | **Contratos de Dados (DTO)** | Schemas Pydantic para validar entradas e saídas de dados com tipagem estrita e documentação automática no Swagger. | Consultas a banco de dados. |
| **`app/services/`** | **Regras de Negócio e IA** | Pipeline de Visão Computacional (`services/vision/pipeline.py`), chamada aos modelos YOLO e integração com a API Gemini Vision. | Lógica de respostas HTTP diretas. |
| **`app/static/`** | **Frontend Mobile** | Interface Web responsiva: HTMLs (`login.html`, `index.html`), folhas de estilo (`css/mobile.css`) e scripts do cliente (`js/`). | Códigos Python ou arquivos de backend. |

---

### 2. `modelos/` — Pesos e Modelos de Machine Learning
- **Propósito:** Armazenamento centralizado de pesos de redes neurais (`.pt`, `.h5`, `.onnx`).
- **Arquivos Atuais:**
  - `pegarvisor.pt`: Modelo treinado YOLO para detecção e recorte preciso do mostrador mecânico.
  - `modelo_hidrometro.h5`: Modelo histórico preservado para referência.

---

### 3. `experimentos/` — Scripts de Teste e Amostras
- **Propósito:** Isolar códigos de laboratório, testes de acurácia manuais e imagens de exemplo para não poluir o código de produção.
- **Arquivos:** Scripts exploratórios como `pegar_visor.py` e pastas com amostras de fotos.

---

### 4. Arquivos de Raiz
- **`run.py`**: Ponto de partida único para iniciar o servidor em desenvolvimento (descobre o IP da rede Wi-Fi para testes no celular).
- **`Dockerfile` & `docker-compose.yml`**: Configurações de container otimizadas para deploy em produção.
- **`.env` / `.env.example`**: Configurações de chaves e variáveis de ambiente.
- **`hidroreader.db`**: Banco de dados SQLite padrão para desenvolvimento.

---

## 🔄 Fluxo de Uma Requisição (Passo a Passo)

```mermaid
sequenceDiagram
    autonumber
    actor Operador as 📱 Operador (Celular)
    participant Front as 🎨 Frontend (app/static)
    participant API as 🌐 Endpoint (app/api/v1/leituras)
    participant Dep as 🔒 Segurança (app/api/deps)
    participant IA as 🧠 Visão (app/services/vision)
    participant DB as 🗄️ Banco de Dados (app/models)

    Operador->>Front: Seleciona apartamento e tira foto do hidrômetro
    Front->>API: POST /api/v1/leituras/processar (Multipart Form + Bearer Token)
    API->>Dep: Valida token JWT do operador
    Dep-->>API: Operador autenticado (ex: Admin)
    API->>IA: visao_service.processar_imagem(bytes)
    IA->>IA: 1. YOLO detecta e recorta o visor (modelos/pegarvisor.pt)
    IA->>IA: 2. Filtro Sobel avalia foco e contraste
    IA->>IA: 3. Gemini Vision lê e separa m³ (pretos) e Litros (vermelhos)
    IA-->>API: Resultado estruturado (LeituraResponseSchema)
    API->>DB: Salva registro na tabela 'leituras' com apto_id e usuario_id
    DB-->>API: Confirmação de persistência
    API-->>Front: Retorna JSON com medição e separação cromática
    Front-->>Operador: Exibe card de medição e roletes coloridos na tela
```

---

## 🚀 Checklist para Deploy em Produção

Quando você for publicar o sistema em um servidor na nuvem (AWS, DigitalOcean, VPS, Render, etc.):

1. **Trocar a Chave Secreta no `.env`:**
   ```bash
   SECRET_KEY="gere_uma_chave_aleatoria_longa_e_segura"
   ```
2. **Definir o Ambiente:**
   ```bash
   ENVIRONMENT="production"
   DEBUG=False
   ```
3. **CORS Restrito:**
   No `.env`, limite `CORS_ORIGINS` para o domínio real do seu aplicativo (ex: `https://app.hidroreader.com.br`).
4. **Deploy com Docker (Recomendado):**
   ```bash
   docker compose up -d --build
   ```
5. **Monitoramento e Health Check:**
   O container possui monitoramento contínuo apontando para `http://localhost:8000/health`, verificando a integridade da API, do banco de dados e do modelo de IA.

