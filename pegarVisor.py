from ultralytics import YOLO
import cv2
import os

# 1. Carregar o modelo treinado
model = YOLO('modelos/pegarvisor.pt')

# 2. Nome da imagem de teste na raiz
nome_imagem = 'i1.jpeg'
if os.path.exists(nome_imagem):
    img_original = cv2.imread(nome_imagem)
    results = model(nome_imagem)
    
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
                
                nome_recorte = f'visor_numeros_{i}.jpg'
                cv2.imwrite(nome_recorte, recorte_numeros)
                print(f"Sucesso! Apenas o visor dos números foi guardado como: '{nome_recorte}'")
                
else:
    print(f"Atenção: A imagem '{nome_imagem}' não foi encontrada na raiz.")