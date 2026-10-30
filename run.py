import os
import uvicorn
import socket

def obter_ip_local():
    """Descobre o IP local da máquina na rede Wi-Fi/Ethernet para teste no celular."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    ip_local = obter_ip_local()
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    ambiente = os.getenv("ENVIRONMENT", "development").lower()
    is_prod = ambiente == "production"

    reload_env = os.getenv("RELOAD")
    if reload_env is not None:
        reload = reload_env.lower() in ("true", "1")
    else:
        reload = not is_prod

    print("=" * 65)
    print(f"🚀 INICIANDO SERVIDOR FASTAPI (HIDROREADER - {ambiente.upper()})")
    print("=" * 65)
    print(f"👉 Porta do Servidor:             {port}")
    print(f"👉 Modo Hot-Reload:              {'Ativado' if reload else 'Desativado'}")
    print(f"👉 Acesso Local:                  http://localhost:{port}")
    if not is_prod:
        print(f"📱 Acesso no Celular (mesmo Wi-Fi): http://{ip_local}:{port}")
    print(f"📚 Documentação Swagger da API:   http://localhost:{port}/docs")
    print(f"🩺 Health Check:                  http://localhost:{port}/health")
    print("=" * 65 + "\n")

    uvicorn.run("main:app", host=host, port=port, reload=reload)
