import cv2
import os
import numpy as np

def aplicar_filtros(pasta_entrada, pasta_saida):
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)
        
    # Percorre todos os arquivos na pasta de entrada
    for nome_arquivo in os.listdir(pasta_entrada):
        if nome_arquivo.lower().endswith(('.png', '.jpg', '.jpeg')):
            caminho_imagem = os.path.join(pasta_entrada, nome_arquivo)
            
            # 1. Carrega a imagem
            imagem = cv2.imread(caminho_imagem)
            if imagem is None:
                continue
                
            # 2. APLICANDO FILTROS (Você pode escolher qual usar):
            imagem_filtrada = cv2.GaussianBlur(imagem, (9, 9), 0)
            
            # Filtro A: Tons de cinza (Preto e Branco)
            imagem_filtrada = cv2.cvtColor(imagem_filtrada, cv2.COLOR_BGR2GRAY)
            
            # 2. Aplica o Mean Threshold Binarization
            imagem_filtrada = cv2.adaptiveThreshold(
                imagem_filtrada,              # Imagem de entrada (em cinza ou blur)
                255,                          # Valor máximo (255 = branco)
                cv2.ADAPTIVE_THRESH_MEAN_C,   # Método da média (Mean)
                cv2.THRESH_BINARY,            # Tipo de binarização (Pode usar cv2.THRESH_BINARY_INV para inverter cores)
                11,                           # Tamanho do bloco (Área que ele analisa por vez, TEM que ser número ímpar: 11, 15, 21...)
                2                             # Constante 'C' subtraída da média (geralmente entre 2 e 5)
            )
            
            # remover ruidos
            # contornos, hierarquia = cv2.findContours(imagem_filtrada, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # # 2. Cria uma imagem totalmente preta do mesmo tamanho para desenharmos os números "limpos"
            # imagem_filtrada = np.zeros_like(imagem_filtrada)
            # # 3. Analisa cada contorno encontrado
            # for contorno in contornos:
            #     area = cv2.contourArea(contorno)
                
            #     # 4. FILTRO DE TAMANHO: 
            #     # Descartamos tudo que for menor que 50 pixels (ruído) 
            #     # e maior que 1000 pixels (manchas gigantes).
            #     # *ATENÇÃO: Você provavelmente terá que ajustar esses valores (50 e 1000)*
            #     # *de acordo com o tamanho real dos números na sua imagem!*
            #     if area > 105 and area < 1716:
            #         # Se o tamanho estiver ok, desenhamos esse contorno (número) na nova imagem
            #         cv2.drawContours(imagem_filtrada, [contorno], -1, 255, thickness=cv2.FILLED)

            nome_sem_ponto = nome_arquivo.split('.')[0]
            caminho_saida = os.path.join(pasta_saida, f"{nome_sem_ponto}_filtrado.jpg")
            cv2.imwrite(caminho_saida, imagem_filtrada)
            print(f"Filtro aplicado: {nome_arquivo}")

# Como usar:
# Coloque suas imagens originais numa pasta chamada 'imagens_originais'
# aplicar_filtros('imagens_originais', 'imagens_filtradas')

aplicar_filtros("imagem pós modelo", "imagem pós filtro")