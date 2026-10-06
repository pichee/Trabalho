from ultralytics import YOLO
import cv2
import os

# 1. Carregar o modelo treinado
model = YOLO('modelos/pegarvisor.pt')

for nome_imagem in os.listdir("imagem_para_aplicar"):
    caminho_completo = os.path.join("imagem_para_aplicar", nome_imagem)
    if os.path.exists(caminho_completo):
        img_original = cv2.imread(caminho_completo)
        results = model(caminho_completo)
        
        for r in results:
            boxes = r.boxes.xyxy.cpu().numpy()  # Coordenadas [x1, y1, x2, y2]
            classes = r.boxes.cls.cpu().numpy()  # IDs das classes detetadas
            names = r.names                      # Nomes das classes do modelo
            
            for i, (box, cls_id) in enumerate(zip(boxes, classes)):
                nome_classe = names[int(cls_id)]
                
                # FILTRAR APENAS PELA CLASSE DOS NÚMEROS
                if nome_classe.lower() == 'numbers':
                    x1, y1, x2, y2 = map(int, box)
                    
                    # Recortar apenas a zona dos números da imagem original
                    recorte_numeros = img_original[y1:y2, x1:x2]
                    
                    pasta_saida = 'imagem pós modelo'
                    if not os.path.exists(pasta_saida):
                        os.makedirs(pasta_saida)

                    nome_sem_ponto = nome_imagem.split('.')[0]
                    nome_recorte = os.path.join(pasta_saida, f'visor_numeros_{nome_sem_ponto}.jpg')
                    cv2.imwrite(nome_recorte, recorte_numeros)
                    print(f"Sucesso! Apenas o visor dos números foi guardado como: '{nome_recorte}'")
                    
    else:
        print(f"Atenção: A imagem '{nome_imagem}' não foi encontrada na raiz.")