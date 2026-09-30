import numpy as np
import cv2
from tensorflow.keras.models import load_model

# 1. Carregar o modelo treinado que guardou do Google Drive
print("A carregar o modelo...")
modelo = load_model("modelos/modelo_hidrometro.h5")

# 2. Carregar a imagem de teste
# Nota: A imagem deve ser um dígito isolado (ex: o número 7), redimensionado para 28x28 e em tons de cinzento.
caminho_imagem = "digito_teste.png"  # Substitua pelo caminho da sua imagem de teste
img = cv2.imread(caminho_imagem, cv2.IMREAD_GRAYSCALE)

if img is None:
    print(f"Erro: Não foi possível carregar a imagem em '{caminho_imagem}'. Verifique o caminho.")
else:
    # 3. Garantir que a imagem tem exatamente 28x28 píxeis (como o modelo foi treinado)
    img_redimensionada = cv2.resize(img, (28, 28))

    # 4. Ajustar as dimensões para o formato que o Keras espera: (1, 28, 28, 1)
    # (1 imagem, altura 28, largura 28, 1 canal de cinzento)
    img_input = np.expand_dims(img_redimensionada, axis=0)
    img_input = np.expand_dims(img_input, axis=-1)

    # Opcional: Se a sua imagem tiver fundo branco e letra preta (e o treino foi fundo preto/letra branca), 
    # pode precisar de inverter os píxeis com: img_input = 1.0 - (img_input / 255.0)
    # Assumindo normalização básica:
    img_input = img_input / 255.0

    # 5. Fazer a previsão com a Inteligência Artificial
    previsoes = modelo.predict(img_input)
    
    # O modelo devolve uma lista com 10 probabilidades (uma para cada dígito de 0 a 9)
    digito_previsto = np.argmax(previsoes[0])
    confianca = np.max(previsoes[0]) * 100

    print("\n----------------------------------------")
    print(f"🎯 O modelo leu o número: {digito_previsto}")
    print(f"📊 Nível de confiança: {confianca:.2f}%")
    print("----------------------------------------")