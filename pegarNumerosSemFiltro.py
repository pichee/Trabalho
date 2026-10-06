import os
import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

# ==========================================
# 1. CARREGAR APENAS O MODELO DE DÍGITOS
# ==========================================
model = YOLO("modelos/digitos.pt")

# ==========================================
# 2. IMAGEM DE ENTRADA
# ==========================================]

# ==========================================
# 4. CRIAR PASTA DE DESTINO (UMA ÚNICA VEZ)
# ==========================================
pasta_destino = "numeros_sem_filtro"
os.makedirs(pasta_destino, exist_ok=True)

# Limpar ficheiros antigos da pasta para não misturar (Fazemos isso antes de começar o loop)
for f in os.listdir(pasta_destino):
    if f.endswith((".jpg", ".txt")):
        os.remove(os.path.join(pasta_destino, f))

for nome_imagem in os.listdir("imagem pós modelo"):

    imagem_path = f"imagem pós modelo/{nome_imagem}"
    print(f"Processando a imagem: {imagem_path}")

    if os.path.exists(imagem_path):
        # ==========================================
        # 3. DETECÇÃO
        # ==========================================
        results = model(imagem_path, conf=0.25)
        r = results[0]

        # Usa r.obb se o modelo for do tipo OBB (caixas orientadas), senão usa r.boxes normal
        boxes = r.obb if r.obb is not None else r.boxes

        if boxes is not None and len(boxes) > 0:
            print(f"\nForam detetadas {len(boxes)} caixas brutas!")
            detalhes_detecoes = []

            # Extrair dados de cada caixa detetada
            for box in boxes:
                coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                nome_classe = model.names[cls]

                detalhes_detecoes.append({
                    "x1": coords[0],
                    "y1": coords[1],
                    "x2": coords[2],
                    "y2": coords[3],
                    "conf": conf,
                    "cls": cls,
                    "nome": nome_classe
                })

            # ==========================================
            # 5. FILTRAR DUPLICADAS (Evita sobreposições no mesmo dígito)
            # ==========================================
            detalhes_detecoes.sort(key=lambda x: x["conf"], reverse=True)
            detalhes_filtrados = []

            for det in detalhes_detecoes:
                mantem = True
                for f_det in detalhes_filtrados:
                    inter_left = max(det["x1"], f_det["x1"])
                    inter_right = min(det["x2"], f_det["x2"])
                    overlap = max(0, inter_right - inter_left)
                    largura_det = det["x2"] - det["x1"]
                    
                    if largura_det > 0 and overlap > (largura_det * 0.5):
                        mantem = False
                        break
                if mantem:
                    detalhes_filtrados.append(det)

            # ==========================================
            # 6. ORDENAR RIGOROSAMENTE DA ESQUERDA PARA A DIREITA
            # ==========================================
            detalhes_filtrados.sort(key=lambda x: x["x1"])

            print(f"Dígitos limpos finais: {len(detalhes_filtrados)}")

            sequencia_texto = ""

            # ==========================================
            # 7. LER A SEQUÊNCIA DE DÍGITOS
            # ==========================================
            for i, det in enumerate(detalhes_filtrados):
                sequencia_texto += str(det['nome'])
                print(f"  Dígito {i+1}: '{det['nome']}' (conf: {det['conf']:.2f})")

            # ==========================================
            # 8. CRIAR COLAGEM DOS DÍGITOS LADO A LADO
            # ==========================================
            if len(detalhes_filtrados) > 0:
                img_cv = cv2.imread(imagem_path)
                paineis_cv = []
                
                for det in detalhes_filtrados:
                    x1, y1, x2, y2 = int(det["x1"]), int(det["y1"]), int(det["x2"]), int(det["y2"])
                    recorte = img_cv[y1:y2, x1:x2]
                    valor_str = str(det['nome'])
                    
                    altura, largura, _ = recorte.shape
                    # Cria um painel branco com 40px de altura extra em cima para o texto
                    largura_painel = max(largura, 40)
                    painel = np.ones((altura + 40, largura_painel, 3), dtype=np.uint8) * 255
                    
                    # Centraliza o recorte na parte de baixo do painel
                    offset_x = (largura_painel - largura) // 2
                    painel[40:40+altura, offset_x:offset_x+largura] = recorte
                    
                    # Escreve o valor do dígito de vermelho no topo
                    cv2.putText(painel, valor_str, (offset_x + 5, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    paineis_cv.append(painel)
                
                # Força todos os painéis a terem a mesma altura (a máxima entre eles) para o hconcat funcionar
                altura_max = max(p.shape[0] for p in paineis_cv)
                paineis_ajustados = []
                for p in paineis_cv:
                    h, w, _ = p.shape
                    if h < altura_max:
                        fundo = np.ones((altura_max, w, 3), dtype=np.uint8) * 255
                        fundo[0:h, 0:w] = p
                        paineis_ajustados.append(fundo)
                    else:
                        paineis_ajustados.append(p)
                
                # Junta tudo na horizontal
                colagem_final = cv2.hconcat(paineis_ajustados)
                nome_sem_extensao = os.path.splitext(nome_imagem)[0]
                caminho_colagem = os.path.join(pasta_destino, f"{nome_sem_extensao}_COLAGEM.jpg")
                cv2.imwrite(caminho_colagem, colagem_final)
                print(f"Colagem visual salva em '{caminho_colagem}'")

            # Guardar a leitura completa concatenada num ficheiro de texto geral
            caminho_geral = os.path.join(pasta_destino, "resultado_leitura.txt")
            with open(caminho_geral, "w") as f_geral:
                f_geral.write(sequencia_texto)

            print(f"\nSequência completa obtida: {sequencia_texto} (Guardada em '{caminho_geral}')")
        else:
            print("\nNenhum dígito foi detetado.")

        # Guardar a imagem global com todas as caixas desenhadas para conferência
        # r.save(filename=f"numero_{nome_imagem}.jpg")
        # print("\nProcesso concluído com sucesso!")

    else:
        print(f"Atenção: A imagem '{imagem_path}' não foi encontrada.")