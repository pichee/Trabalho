import os
import time
from dotenv import load_dotenv
from google import genai
from PIL import Image

# Carrega a chave do .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY não foi encontrada no arquivo .env!")

# Lista de modelos multimodais de visão para testar
MODELOS_TESTE = [
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-pro-latest"
]

def main():
    print("=" * 70)
    print("Testando Modelos do Gemini para Leitura de Imagem...")
    print("=" * 70)

    client = genai.Client(api_key=API_KEY)
    
    # Imagem de teste
    caminho_img = "saida_recortes/visores_nitidos/2_visor_0.jpg"
    if not os.path.exists(caminho_img):
        print(f"Erro: Imagem de teste não encontrada em: {caminho_img}")
        return

    img = Image.open(caminho_img)
    prompt = "Leia apenas os números do mostrador mecânico desta foto. Responda apenas com os dígitos."

    modelos_funcionais = []

    for modelo in MODELOS_TESTE:
        print(f"\nTestando: {modelo}...")
        inicio = time.time()
        try:
            resposta = client.models.generate_content(
                model=modelo,
                contents=[img, prompt]
            )
            duracao = time.time() - inicio
            resultado = resposta.text.strip().replace('\n', ' ')
            print(f"  [✓ SUCESSO] Tempo: {duracao:.2f}s | Resposta: {resultado}")
            modelos_funcionais.append((modelo, duracao))
        except Exception as e:
            msg_erro = str(e).splitlines()[0]
            print(f"  [✗ FALHA] {msg_erro[:75]}")

    print("\n" + "=" * 70)
    print("Classificação dos Melhores Modelos:")
    print("=" * 70)
    if modelos_funcionais:
        # Ordena pelo mais rápido
        modelos_funcionais.sort(key=lambda x: x[1])
        for idx, (m, t) in enumerate(modelos_funcionais, 1):
            estrela = " 🏆 (Mais recomendado)" if idx == 1 else ""
            print(f"  {idx}. {m:<25} - {t:.2f}s{estrela}")
    else:
        print("Nenhum modelo respondeu no momento. Verifique a cota ou a chave.")
    print("=" * 70)

if __name__ == "__main__":
    main()
