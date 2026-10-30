# 🚀 GUIA DE DEPLOY E MANUTENÇÃO - HIDROREADER

Este guia contém as instruções completas para colocar o **HidroReader** em produção e realizar manutenções com segurança.

---

## 1. 📋 Checklist Pré-Deploy

Defina as seguintes variáveis no painel da sua hospedagem ou no arquivo `.env`:

| Variável | Obrigatória? | Descrição | Exemplo |
| :--- | :---: | :--- | :--- |
| `PROVEDOR_IA` | Recomendado | Provedor de IA preferencial (`openai`, `gemini` ou `hibrido`) | `openai` |
| `OPENAI_API_KEY` | Recomendado | Chave da OpenAI para leitura com ChatGPT Vision | `sk-proj-...` |
| `OPENAI_MODEL` | Opcional | Modelo OpenAI Vision (padrão: `gpt-4o-mini`) | `gpt-4o-mini` ou `gpt-4o` |
| `GEMINI_API_KEY` | Opcional | Chave do Google AI Studio para contingência | `AIzaSy...` |
| `SECRET_KEY` | **Sim** | Chave secreta longa para assinar tokens JWT | `f8a93b...` (gere uma aleatória) |
| `ENVIRONMENT` | Recomendado | Define modo de produção | `production` |
| `DATABASE_URL` | Opcional | URL do banco PostgreSQL ou SQLite | `postgresql://user:pass@host:5432/db` |
| `PORT` | Opcional | Porta do servidor web (injetada pela nuvem) | `8000` |
| `ALLOWED_ORIGINS` | Opcional | Domínios permitidos no CORS | `*` ou `https://meudominio.com` |

---

## 2. 🧠 Sistema de Dupla Verificação de IA

A aplicação possui um pipeline de alta resiliência:
1. **1ª Verificação (Detecção do Visor):** O modelo YOLO (`pegarvisor.pt`) localiza e recorta o visor mecânico.
2. **2ª Verificação (ChatGPT / Gemini Vision):** A imagem recortada é lida e classificada dígito a dígito (pretos em m³ e vermelhos em litros).
3. **Contingência Automática:** Se o visor não for detectado pelo YOLO (ex: ângulo difícil ou reflexo), ou se a API primária oscilar, a contingência assume na foto completa garantindo que o operador nunca fique sem a leitura.

---

## 3. 🐳 Opção 1: Deploy com Docker (Recomendado)

O projeto possui um `Dockerfile` e `docker-compose.yml` otimizados com suporte a OpenCV, health check e portas dinâmicas.

### No Railway / Render / Fly.io / Cloud Run
1. Conecte o repositório GitHub ao painel do provedor.
2. O provedor detectará o `Dockerfile` automaticamente.
3. Adicione as variáveis de ambiente (`OPENAI_API_KEY`, `SECRET_KEY`, etc.).
4. O build iniciará automaticamente e a porta será vinculada via `$PORT`.

### Em um Servidor VPS Próprio (com Docker Compose)
```bash
# 1. Clone o repositório no servidor
git clone <url-do-repositorio>
cd trabalho

# 2. Crie o arquivo .env com suas configurações
cp .env.example .env
nano .env

# 3. Suba o container em segundo plano
docker compose up -d --build

# 4. Verifique os logs
docker compose logs -f
```

---

## 4. 🖥️ Opção 2: Deploy Direto em VPS Linux (Ubuntu + Systemd + Nginx)

Caso prefira rodar sem Docker diretamente no servidor Linux:

### Passo 1: Instalar dependências do sistema
```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip libgl1 libglib2.0-0 nginx certbot python3-certbot-nginx
```

### Passo 2: Clonar e configurar ambiente virtual
```bash
git clone <url-do-repositorio> /var/www/hidroreader
cd /var/www/hidroreader
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env
```

### Passo 3: Configurar o serviço Systemd (`/etc/systemd/system/hidroreader.service`)
```ini
[Unit]
Description=HidroReader FastAPI Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/hidroreader
Environment="PATH=/var/www/hidroreader/venv/bin"
ExecStart=/var/www/hidroreader/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

Ative o serviço:
```bash
sudo systemctl daemon-reload
sudo systemctl enable hidroreader
sudo systemctl start hidroreader
sudo systemctl status hidroreader
```

### Passo 4: Configurar Nginx com HTTPS (SSL Gratuito)
Crie o arquivo `/etc/nginx/sites-available/hidroreader`:
```nginx
server {
    server_name seudominio.com.br;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Ative e gere o certificado SSL com câmera liberada no celular:
```bash
sudo ln -s /etc/nginx/sites-available/hidroreader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d seudominio.com.br
```

---

## 5. 🗄️ Banco de Dados em Produção (PostgreSQL)

Para conectar o HidroReader a um banco PostgreSQL gerenciado (ex: Neon, Supabase, Railway Postgres):

1. Basta configurar no `.env`:
   ```ini
   DATABASE_URL="postgresql://usuario:senha@host:5432/nome_banco"
   ```
2. A aplicação detecta a URL automaticamente e cria todas as tabelas e usuários padrão no primeiro startup.

---

## 6. 🛠️ Manutenção e Monitoramento

### 🩺 Health Check da Aplicação
- URL: `GET /health`
- Retorna código HTTP `200` se o banco e a IA estiverem operacionais, informando o status da OpenAI e do Gemini.

### ℹ️ Informações do Sistema
- URL: `GET /api/v1/sistema/info` (Requer Token do Operador)
- Mostra a versão ativa, provedor de IA e status dos recursos.
