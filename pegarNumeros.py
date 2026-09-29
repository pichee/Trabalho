import os
from PIL import Image
from ultralytics import YOLO

# ==========================================
# 1. CARREGAR APENAS O MODELO DE DÍGITOS
# ==========================================
model = YOLO("modelos/digitos.pt")

# ==========================================
# 2. IMAGEM DE ENTRADA
# ==========================================
imagem_path = "visor_numeros_0.jpg"  # Pode trocar para a imagem que quiser processar diretamente
print(f"Processando a imagem: {imagem_path}")

if os.path.exists(imagem_path):
    # ==========================================
    # 3. DETECÇÃO
    # ==========================================
    results = model(imagem_path, conf=0.25)
    r = results[0]

    # ==========================================
    # 4. CRIAR PASTA DE DESTINO
    # ==========================================
    pasta_destino = "numeros"
    os.makedirs(pasta_destino, exist_ok=True)

    # Limpar ficheiros antigos da pasta para não misturar
    for f in os.listdir(pasta_destino):
        if f.endswith((".jpg", ".txt")):
            os.remove(os.path.join(pasta_destino, f))

    boxes = r.boxes

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

        # Abrir imagem original para os recortes
        imagem_original = Image.open(imagem_path)
        largura_img, altura_img = imagem_original.size
        sequencia_texto = ""

        # ==========================================
        # 7. SALVAR CADA DÍGITO SEPARADAMENTE COM O SEU LABEL
        # ==========================================
        for i, det in enumerate(detalhes_filtrados):
            x1, y1, x2, y2 = int(det["x1"]), int(det["y1"]), int(det["x2"]), int(det["y2"])

            # Recortar estritamente o dígito isolado
            digito_recortado = imagem_original.crop((x1, y1, x2, y2))

            # Nomes dos ficheiros individuais
            nome_base = f"digito_{i+1}_valor_{det['nome']}"
            caminho_imagem = os.path.join(pasta_destino, f"{nome_base}.jpg")
            caminho_txt = os.path.join(pasta_destino, f"{nome_base}.txt")

            # Guardar a imagem do dígito separado
            digito_recortado.save(caminho_imagem)

            # Gerar o label no formato YOLO (.txt normalizado)
            box_w = x2 - x1
            box_h = y2 - y1
            x_center = x1 + (box_w / 2.0)
            y_center = y1 + (box_h / 2.0)

            x_center_norm = x_center / largura_img
            y_center_norm = y_center / altura_img
            w_norm = box_w / largura_img
            h_norm = box_h / altura_img

            with open(caminho_txt, "w") as f_txt:
                f_txt.write(f"{det['cls']} {x_center_norm:.6f} {y_center_norm:.6f} {w_norm:.6f} {h_norm:.6f}\n")

            sequencia_texto += str(det['nome'])

            print(
                f"  Dígito {i+1}: '{det['nome']}' "
                f"(conf: {det['conf']:.2f}) -> Guardado separadamente em '{caminho_imagem}'"
            )

        # Guardar a leitura completa concatenada num ficheiro de texto geral
        caminho_geral = os.path.join(pasta_destino, "resultado_leitura.txt")
        with open(caminho_geral, "w") as f_geral:
            f_geral.write(sequencia_texto)

        print(f"\nSequência completa obtida: {sequencia_texto} (Guardada em '{caminho_geral}')")
    else:
        print("\nNenhum dígito foi detetado.")

    # Guardar a imagem global com todas as caixas desenhadas para conferência
    r.save(filename="resultado_deteccao.jpg")
    print("\nProcesso concluído com sucesso!")

else:
    print(f"Atenção: A imagem '{imagem_path}' não foi encontrada.")