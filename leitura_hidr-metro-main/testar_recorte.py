import os
import sys
import glob
import cv2
import numpy as np
from ultralytics import YOLO

# Diretório padrão com as imagens
DIRETORIO_PADRAO = "/home/eduzera/Desktop/Programs/hidrometro_new/imagem_para_aplicar"

# Limiares calibrados especificamente para leitura de hidrômetros (OCR)
CONF_MINIMA_YOLO = 0.50   # O modelo precisa ter certeza do visor
ALTURA_MINIMA = 70        # Se a altura for < 70px, os dígitos ficam microscópicos (foto de longe)
ASPECT_RATIO_MIN = 1.35   # O visor mecânico é retangular; se for quadrado é falso positivo
DYNAMIC_RANGE_MIN = 35.0  # Diferença real entre preto e branco (elimina penumbra e reflexo lavado)
BORDAS_MINIMA = 82.0      # Energia de transição dos dígitos (elimina desfoque e vidro embaçado)

def avaliar_qualidade_visor(crop):
    """
    Avalia a qualidade real de leitura do visor:
    - Resolução mínima (altura e largura úteis para OCR)
    - Proporção geométrica (formato retangular do visor mecânico)
    - Faixa dinâmica (contraste percentil 90 vs percentil 10)
    - Nitidez de bordas (gradiente Sobel após normalização de escala)
    """
    if crop is None or crop.size == 0:
        return False, "Recorte vazio", 0.0, 0.0, (0, 0)
    
    h, w = crop.shape[:2]
    aspect_ratio = w / max(h, 1)

    # 1. Checagem de distância/resolução
    if h < ALTURA_MINIMA:
        return False, f"Muito longe (altura {h}px < {ALTURA_MINIMA}px)", 0.0, 0.0, (w, h)
    
    if aspect_ratio < ASPECT_RATIO_MIN:
        return False, f"Formato inválido (aspect {aspect_ratio:.1f} < {ASPECT_RATIO_MIN})", 0.0, 0.0, (w, h)

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # 2. Contraste real (Faixa dinâmica entre números e fundo)
    p10, p90 = np.percentile(gray, 10), np.percentile(gray, 90)
    dyn_range = float(p90 - p10)

    # 3. Nitidez de bordas normalizada
    # Normalizamos a escala para 100px para calibrar a energia das bordas
    scale = 100.0 / h
    norm = cv2.resize(gray, (max(1, int(w * scale)), 100), interpolation=cv2.INTER_AREA)
    
    # Filtro suave para desconsiderar poeira e arranhões microscópicos
    suave = cv2.GaussianBlur(norm, (3, 3), 0)
    gx = cv2.Sobel(suave, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(suave, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(gx**2 + gy**2)

    # Avaliamos apenas as bordas estruturadas principais (top 15% mais fortes)
    limiar_borda = np.percentile(mag, 85)
    bordas_principais = mag[mag > limiar_borda]
    score_bordas = float(np.mean(bordas_principais)) if len(bordas_principais) > 0 else 0.0

    # 4. Decisão de aprovação
    if dyn_range < DYNAMIC_RANGE_MIN:
        return False, f"Baixo contraste ({dyn_range:.0f} < {DYNAMIC_RANGE_MIN:.0f})", score_bordas, dyn_range, (w, h)
    
    if score_bordas < BORDAS_MINIMA:
        return False, f"Desfocado/Embaçado ({score_bordas:.1f} < {BORDAS_MINIMA:.1f})", score_bordas, dyn_range, (w, h)

    return True, "Aprovada", score_bordas, dyn_range, (w, h)

def encontrar_imagens(origem=None):
    caminho = origem if origem else DIRETORIO_PADRAO
    extensoes = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")
    
    if os.path.isfile(caminho):
        return [caminho]
    
    if os.path.isdir(caminho):
        arquivos = []
        for ext in extensoes:
            arquivos.extend(glob.glob(os.path.join(caminho, ext)))
        return sorted(list(set(arquivos)))

    print(f"Aviso: Diretório não encontrado: {caminho}")
    return []

def main():
    caminho_modelo = "best.pt"
    if not os.path.exists(caminho_modelo):
        print(f"Erro: Modelo {caminho_modelo} não encontrado!")
        return

    origem = sys.argv[1] if len(sys.argv) > 1 else DIRETORIO_PADRAO
    imagens = encontrar_imagens(origem)

    if not imagens:
        print(f"\nNenhuma imagem encontrada em: {origem}")
        return

    print("=" * 88)
    print(f"Carregando modelo YOLOv8 ({caminho_modelo})...")
    model = YOLO(caminho_modelo)
    print("Modelo carregado!")
    print(f"Processando {len(imagens)} foto(s)...")
    print("=" * 88)

    pasta_saida = "saida_recortes"
    pasta_nitidos = os.path.join(pasta_saida, "visores_nitidos")
    pasta_nao_nitidos = os.path.join(pasta_saida, "visores_nao_nitidos")
    pasta_deteccoes = os.path.join(pasta_saida, "deteccoes")

    os.makedirs(pasta_nitidos, exist_ok=True)
    os.makedirs(pasta_nao_nitidos, exist_ok=True)
    os.makedirs(pasta_deteccoes, exist_ok=True)

    relatorio = []

    for foto_caminho in imagens:
        nome_arquivo = os.path.basename(foto_caminho)
        nome_base, _ = os.path.splitext(nome_arquivo)

        img_original = cv2.imread(foto_caminho)
        if img_original is None:
            continue

        results = model(foto_caminho, conf=CONF_MINIMA_YOLO, verbose=False)
        result = results[0]
        nomes_classes = result.names

        visores_encontrados = []
        for b in result.boxes:
            if int(b.cls[0].item()) == 0:  # 0 = 'numbers'
                visores_encontrados.append(b)

        # Salva imagem anotada pelo YOLO para debug
        img_com_caixas = result.plot()
        cv2.imwrite(os.path.join(pasta_deteccoes, f"{nome_base}_det.jpg"), img_com_caixas)

        if not visores_encontrados:
            relatorio.append({
                "foto": nome_arquivo,
                "status": "REJEITADA",
                "motivo": "Visor não detectado (ângulo/rotação/escuro)",
                "tamanho": "-",
                "conf": "-",
                "bordas": 0.0,
                "contraste": 0.0
            })
            continue

        for i, box in enumerate(visores_encontrados):
            confianca = float(box.conf[0].item())
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            h_orig, w_orig, _ = img_original.shape
            pad = 5
            x1_crop = max(0, x1 - pad)
            y1_crop = max(0, y1 - pad)
            x2_crop = min(w_orig, x2 + pad)
            y2_crop = min(h_orig, y2 + pad)

            crop_visor = img_original[y1_crop:y2_crop, x1_crop:x2_crop]

            aprovado, motivo, score_bordas, dyn_range, dimensoes = avaliar_qualidade_visor(crop_visor)

            if aprovado:
                pasta_destino = pasta_nitidos
                status_str = "NÍTIDA"
                nome_salvo = f"{nome_base}_visor_{i}.jpg"
            else:
                pasta_destino = pasta_nao_nitidos
                status_str = "NÃO NÍTIDA"
                nome_salvo = f"{nome_base}_visor_{i}_motivo.jpg"

            caminho_salvo = os.path.join(pasta_destino, nome_salvo)
            cv2.imwrite(caminho_salvo, crop_visor)

            relatorio.append({
                "foto": nome_arquivo,
                "status": status_str,
                "motivo": motivo,
                "tamanho": f"{dimensoes[0]}x{dimensoes[1]}",
                "conf": f"{confianca:.1%}",
                "bordas": score_bordas,
                "contraste": dyn_range
            })

    # Imprime a tabela de comparação
    print("\n" + "=" * 105)
    print(f"{'FOTO':<18} | {'STATUS':<11} | {'TAMANHO':<9} | {'YOLO':<6} | {'BORDAS':<7} | {'CONTRASTE':<9} | {'MOTIVO'}")
    print("-" * 105)
    for r in relatorio:
        cor = "✓" if r["status"] == "NÍTIDA" else "✗"
        print(f"{r['foto']:<18} | {cor} {r['status']:<9} | {r['tamanho']:<9} | {r['conf']:<6} | {r['bordas']:<7.1f} | {r['contraste']:<9.1f} | {r['motivo']}")
    print("=" * 105)

    total_nitidas = sum(1 for r in relatorio if r["status"] == "NÍTIDA")
    total_rejeitadas = len(relatorio) - total_nitidas

    print(f"\nResumo da Separação:")
    print(f"  [✓] {total_nitidas} visores nítidos salvos em: {pasta_nitidos}/")
    print(f"  [✗] {total_rejeitadas} visores não nítidos salvos em: {pasta_nao_nitidos}/")
    print(f"  [i] Todas as detecções salvas em: {pasta_deteccoes}/\n")

if __name__ == "__main__":
    main()
