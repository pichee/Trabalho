import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

# Carrega as variáveis do arquivo .env
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY não foi encontrada no arquivo .env!")

# Prioriza os modelos mais inteligentes e sensíveis a cores antes das versões lite
MODELOS_PREFERENCIAIS = [
    "gemini-flash-latest",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-pro-latest",
    "gemini-3.1-flash-lite"
]

def ler_visor_hidrometro(caminho_imagem, client):
    img = Image.open(caminho_imagem)

    prompt = """
    Você é um perito em inspeção de hidrômetros (medidores de água).
    Analise minuciosamente a imagem deste visor de roletes mecânicos.

    REGRAS ESTRITAS DE LEITURA E CORES:
    1. ANALISE CROMÁTICA DÍGITO A DÍGITO:
       - Inspecione a COR REAL DA TINTA de cada rolete individualmente.
       - Dígitos PRETOS: roletes com tinta preta (medem m³ / consumo faturado).
       - Dígitos VERMELHOS: roletes com tinta vermelha ou bordas vermelhas (medem litros/decimais).
       - ATENÇÃO: NÃO assuma quantidades pré-definidas. Existem hidrômetros com 3 pretos e 2 vermelhos, 4 pretos e 1 vermelho, 4 pretos e 2 vermelhos, etc. Classifique estritamente pela cor visual de cada um.
    
    2. ORIENTAÇÃO E LEITURA:
       - Leia da esquerda para a direita na orientação correta.
       - Se a imagem estiver invertida (cabeça para baixo), corrija a rotação mentalmente.
    
    3. TRANSIÇÃO DE ROLETES:
       - Se algum número estiver girando na metade, indique o valor predominante.

    Retorne ESTRITAMENTE um JSON com esta estrutura:
    {
        "leitura_completa": "00054",
        "digitos_pretos": "000",
        "digitos_vermelhos": "54",
        "qtd_pretos": 3,
        "qtd_vermelhos": 2,
        "analise_cores": "descreva a cor que você viu em cada dígito (ex: 0=preto, 0=preto, 0=preto, 5=vermelho, 4=vermelho)",
        "confianca": "alta|media|baixa"
    }
    """

    ultimo_erro = None
    for modelo in MODELOS_PREFERENCIAIS:
        try:
            response = client.models.generate_content(
                model=modelo,
                contents=[img, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return modelo, response.text
        except Exception as e:
            ultimo_erro = e
            time.sleep(1)
            continue

    raise RuntimeError(f"Nenhum modelo respondeu. Erro: {ultimo_erro}")

def main():
    client = genai.Client(api_key=API_KEY)
    pasta_visores = "saida_recortes/visores_nitidos"
    
    if not os.path.exists(pasta_visores):
        print(f"Pasta {pasta_visores} não encontrada!")
        return

    fotos = sorted([f for f in os.listdir(pasta_visores) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

    for foto_nome in fotos:
        print(f"\n=======================================================")
        print(f"Lendo: {foto_nome}...")
        try:
            caminho_foto = os.path.join(pasta_visores, foto_nome)
            modelo_usado, resultado_json = ler_visor_hidrometro(caminho_foto, client)
            dados = json.loads(resultado_json)

            print(f"  [✓] Modelo            : {modelo_usado}")
            print(f"  [✓] Leitura Completa  : {dados.get('leitura_completa')}")
            print(f"      - Pretos (m³)     : {dados.get('digitos_pretos')}")
            print(f"      - Vermelhos (l)   : {dados.get('digitos_vermelhos')}")
            print(f"      - Análise de Cor  : {dados.get('analise_cores')}")
        except Exception as e:
            print(f"  [✗] Erro: {e}")

if __name__ == "__main__":
    main()
