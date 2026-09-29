import os
from PIL import Image
from ultralytics import YOLO


# ==========================================
# 1. CARREGAR MODELO
# ==========================================
model = YOLO("modelos/digitos.pt")


# ==========================================
# 2. IMAGEM
# ==========================================
imagem_path = "visor_numeros_0.jpg"
print(f"Processando a imagem: {imagem_path}")


# ==========================================
# 3. DETECÇÃO
# ==========================================
results = model(imagem_path, conf=0.25)
r = results[0]


# ==========================================
# 4. CRIAR PASTA
# ==========================================
pasta_destino = "numeros"
os.makedirs(pasta_destino, exist_ok=True)

# Limpar arquivos antigos para não misturar
for f in os.listdir(pasta_destino):
    if f.endswith((".jpg", ".txt")):
        os.remove(os.path.join(pasta_destino, f))


# ==========================================
# 5. PROCESSAR CAIXAS (USANDO r.boxes)
# ==========================================
boxes = r.boxes

if boxes is not None and len(boxes) > 0:
    print(f"\nForam detetadas {len(boxes)} caixas brutas!")
    detalhes_detecoes = []

    # ======================================
    # PEGAR AS DETECÇÕES
    # ======================================
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

    # ======================================
    # FILTRAR DUPLICADAS (Evita detetar 2 números no mesmo sítio)
    # ======================================
    detalhes_detecoes.sort(key=lambda x: x["conf"], reverse=True)
    detalhes_filtrados = []

    for det in detalhes_detecoes:
        mantem = True
        for f_det in detalhes_filtrados:
            inter_left = max(det["x1"], f_det["x1"])
            inter_right = min(det["x2"], f_det["x2"])
            overlap = max(0, inter_right - inter_left)
            largura_det = det["x2"] - det["x1"]
            
            # Se sobrepor muito, descarta a mais fraca
            if largura_det > 0 and overlap > (largura_det * 0.5):
                mantem = False
                break
        if mantem:
            detalhes_filtrados.append(det)

    # ======================================
    # ORDENAR DA ESQUERDA PARA DIREITA
    # ======================================
    detalhes_filtrados.sort(key=lambda x: x["x1"])

    print(f"Dígitos limpos finais: {len(detalhes_filtrados)}")

    # ======================================
    # ABRIR IMAGEM ORIGINAL PARA OBTER DIMENSÕES
    # ======================================
    imagem_original = Image.open(imagem_path)
    largura_img, altura_img = imagem_original.size

    # String para acumular a sequência completa dos dígitos detetados (ex: "000542")
    sequencia_texto = ""

    # ======================================
    # SALVAR CADA DÍGITO E GERAR LABELS
    # ======================================
    for i, det in enumerate(detalhes_filtrados):
        x1 = int(det["x1"])
        y1 = int(det["y1"])
        x2 = int(det["x2"])
        y2 = int(det["y2"])

        # Recortar imagem individual do dígito
        digito_recortado = imagem_original.crop((x1, y1, x2, y2))

        # Nome base do arquivo
        nome_base = f"digito_{i+1}_valor_{det['nome']}"
        caminho_imagem = os.path.join(pasta_destino, f"{nome_base}.jpg")
        caminho_txt = os.path.join(pasta_destino, f"{nome_base}.txt")

        # Salvar imagem recortada
        digito_recortado.save(caminho_imagem)

        # ---- GERAR O LABEL NO FORMATO YOLT (x_center, y_center, width, height normalizados) ----
        box_w = x2 - x1
        box_h = y2 - y1
        x_center = x1 + (box_w / 2.0)
        y_center = y1 + (box_h / 2.0)

        # Normalizar com base nas dimensões da imagem original
        x_center_norm = x_center / largura_img
        y_center_norm = y_center / altura_img
        w_norm = box_w / largura_img
        h_norm = box_h / altura_img

        # Escrever o ficheiro .txt do label (classe_id x_center y_center largura altura)
        with open(caminho_txt, "w") as f_txt:
            f_txt.write(f"{det['cls']} {x_center_norm:.6f} {y_center_norm:.6f} {w_norm:.6f} {h_norm:.6f}\n")

        sequencia_texto += str(det['nome'])

        print(
            f"  Dígito {i+1}: {det['nome']} (conf: {det['conf']:.2f}) -> Salvo com label .txt"
        )

    # Guardar também um ficheiro de texto global com o valor completo lido no visor
    caminho_resultado_geral = os.path.join(pasta_destino, "resultado_leitura.txt")
    with open(caminho_resultado_geral, "w") as f_geral:
        f_geral.write(sequencia_texto)
    
    print(f"\nValor completo detetado no visor: {sequencia_texto} (Guardado em {caminho_resultado_geral})")

else:
    print("\nNenhum dígito foi detectado.")


# ==========================================
# 6. SALVAR IMAGEM COM DETECÇÕES GLOBAIS
# ==========================================
r.save(filename="resultado_deteccao.jpg")

print("\nProcesso concluído com sucesso!")