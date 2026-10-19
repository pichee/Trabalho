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
    print("=" * 65)
    print("🚀 INICIANDO SERVIDOR FASTAPI (HIDROREADER MOBILE)")
    print("=" * 65)
    print(f"👉 Acesso no Computador: http://localhost:8000")
    print(f"📱 Acesso no Celular (mesmo Wi-Fi): http://{ip_local}:8000")
    print(f"📚 Documentação Swagger da API:   http://localhost:8000/docs")
    print("=" * 65 + "\n")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
