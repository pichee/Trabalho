# 💧 HidroReader Mobile

Sistema inteligente para leitura automática de hidrômetros residenciais via smartphone, utilizando **FastAPI**, **Visão Computacional (YOLO)** e **Google Gemini Vision**.

---

## 🧭 Estrutura do Projeto (Simples, Organizada e Direta)

Cada diretório possui um nome autoexplicativo em português e cada rota do sistema possui **seu próprio arquivo Python dedicado**:

```text
trabalho/
│
├── 📂 rotas/                        # 🛣️ UM ARQUIVO PYTHON PARA CADA ROTA
│   ├── rota_login.py                # Login, autenticação e sessão do operador
│   ├── rota_apartamentos.py         # Listagem e cadastro de apartamentos
│   ├── rota_leitura.py              # Recebe a foto, aciona a IA e salva a medição
│   └── rota_paginas.py              # Entrega as telas HTML e health check
│
├── 📂 banco/                        # 🗄️ TUDO DO BANCO DE DADOS
│   ├── conexao.py                   # Conexão SQLite e carga inicial de dados
│   └── modelos.py                   # Tabelas: Usuario, Apartamento, Leitura
│
├── 📂 ia/                           # 🧠 INTELIGÊNCIA ARTIFICIAL
│   └── leitor_ia.py                 # YOLO (recorta visor) + Gemini Vision (lê números)
│
├── 📂 seguranca/                    # 🔒 SEGURANÇA E SESSÃO
│   └── autenticacao.py              # Criptografia de senhas e tokens de acesso
│
├── 📂 telas/                        # 🎨 FRONTEND MOBILE
│   ├── 📂 css/
│   │   └── mobile.css               # Estilos visuais Bauhaus modernos
│   ├── 📂 js/
│   │   ├── login.js                 # Lógica da tela de login
│   │   └── app.js                   # Lógica da câmera e leitura
│   ├── login.html                   # 🔑 Tela de Login
│   └── leitor.html                  # 📱 Tela do Leitor de Hidrômetro
│
├── 📂 modelos_ia/                   # 🤖 MODELOS DE IA
│   └── pegarvisor.pt                # Peso do YOLO treinado para o visor mecânico
│
├── 📂 uploads/                      # Fotos enviadas pelos operadores
├── 📂 tmp/                          # Recortes temporários durante a leitura
├── 📂 experimentos/                 # Códigos antigos e fotos de laboratório
│
├── 📄 main.py                       # Ponto de entrada FastAPI (conecta todas as rotas)
├── ▶️ run.py                         # Inicia o servidor e exibe o IP para o celular
├── 🗄️ hidroreader.db                # Banco de dados local SQLite
├── 📄 .env                          # Chave de API do Gemini (GEMINI_API_KEY)
├── 📄 requirements.txt              # Dependências Python
├── 🐳 Dockerfile                    # Container pronto para deploy em produção
└── 🐳 docker-compose.yml            # Orquestração do container
```

---

## ⚡ Guia Rápido: O que alterar quando você quiser...

| Quando você quiser... | Qual arquivo abrir: |
| :--- | :--- |
| **Mudar a rota ou regras do Login** | [`rotas/rota_login.py`](file:///c:/Users/gustavo/Downloads/trabalho/rotas/rota_login.py) |
| **Mudar a rota de Apartamentos** | [`rotas/rota_apartamentos.py`](file:///c:/Users/gustavo/Downloads/trabalho/rotas/rota_apartamentos.py) |
| **Mudar a rota que processa a Foto** | [`rotas/rota_leitura.py`](file:///c:/Users/gustavo/Downloads/trabalho/rotas/rota_leitura.py) |
| **Mudar as rotas de páginas HTML** | [`rotas/rota_paginas.py`](file:///c:/Users/gustavo/Downloads/trabalho/rotas/rota_paginas.py) |
| **Mudar o visual ou cores da tela** | [`telas/css/mobile.css`](file:///c:/Users/gustavo/Downloads/trabalho/telas/css/mobile.css) |
| **Editar os campos da tela de login** | [`telas/login.html`](file:///c:/Users/gustavo/Downloads/trabalho/telas/login.html) |
| **Editar a tela da câmera do celular** | [`telas/leitor.html`](file:///c:/Users/gustavo/Downloads/trabalho/telas/leitor.html) |
| **Ajustar o prompt ou lógica da IA** | [`ia/leitor_ia.py`](file:///c:/Users/gustavo/Downloads/trabalho/ia/leitor_ia.py) |
| **Criar novas tabelas no banco de dados** | [`banco/modelos.py`](file:///c:/Users/gustavo/Downloads/trabalho/banco/modelos.py) |
| **Trocar a chave do Gemini** | [`.env`](file:///c:/Users/gustavo/Downloads/trabalho/.env) na linha `GEMINI_API_KEY="..."` |

---

## 🚀 Como Iniciar

No terminal, execute:
```powershell
.\venv\Scripts\python.exe run.py
```

- **Acesso no Computador:** `http://localhost:8000`
- **Acesso no Celular:** `http://<SEU_IP_LOCAL>:8000` (mesmo Wi-Fi)
- **Documentação Swagger:** `http://localhost:8000/docs`
- **Usuários de teste:** `admin / admin` ou `operador / 123456`
