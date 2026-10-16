import os
import glob
import cv2
import numpy as np
from ultralytics import YOLO

# ==========================================
# CONFIGURAÇÕES
# ==========================================
CAMINHO_MODELO = "pegarvisor.pt" if os.path.exists("pegarvisor.pt") else "modelos/pegarvisor.pt"
CONFIANCA_MINIMA = 0.25  # Limiar de confiança (25%)


def buscar_imagem():
    """Busca automaticamente fotos disponíveis no projeto."""
    arquivos = glob.glob("*.jpeg") + glob.glob("*.jpg") + glob.glob("*.png")
    ignoradas = {"resultado_deteccao.jpg", "visor_recortado_1.jpg", "visor_recortado_2.jpg", "diag_resultado.jpg"}
    validas = [f for f in arquivos if os.path.basename(f) not in ignoradas]
    
    if validas:
        return validas[0], validas
        
    sub = glob.glob("**/*.jpeg", recursive=True) + glob.glob("**/*.jpg", recursive=True)
    validas_sub = [f for f in sub if os.path.basename(f) not in ignoradas and "venv" not in f]
    if validas_sub:
        return validas_sub[0], validas_sub
        
    return None, []


def testar_modelo():
    print(f"🔄 Carregando modelo '{CAMINHO_MODELO}'...")
    try:
        model = YOLO(CAMINHO_MODELO)
    except Exception as e:
        print(f"❌ Erro ao carregar o arquivo do modelo: {e}")
        return

    print("✅ Modelo carregado com sucesso!")
    print(f"📋 Classes configuradas no modelo: {model.names}\n")

    # Localizar imagem para teste
    imagem_alvo, todas_imagens = buscar_imagem()
    if imagem_alvo is None:
        print("❌ Nenhuma imagem de foto (.jpg, .jpeg, .png) foi encontrada nesta pasta!")
        print("💡 Dica: Coloque uma foto do hidrômetro nesta pasta (ex: hidrometro.jpg) e execute novamente.")
        return

    print(f"🖼️ Fotos encontradas: {todas_imagens}")
    print(f"👉 Processando imagem: '{imagem_alvo}'...\n")

    imagem = cv2.imread(imagem_alvo)
    if imagem is None:
        print(f"❌ Erro: Não foi possível abrir '{imagem_alvo}'.")
        return

    # Identificar IDs da classe dos números ('numbers') para ignorar ponteiros ('pointer')
    ids_numeros = [k for k, v in model.names.items() if 'number' in str(v).lower()]
    if not ids_numeros:
        ids_numeros = [0]  # Padrão: classe 0 costuma ser 'numbers'
    
    print(f"🎯 Foco estrito: detectando APENAS a região dos números (classe ID: {ids_numeros})...\n")
    resultados = model(imagem, conf=CONFIANCA_MINIMA, classes=ids_numeros)[0]

    # Salva a imagem apenas com as caixas dos números desenhadas
    resultados.save(filename="resultado_deteccao.jpg")
    print("💾 Imagem com marcações dos números salva em: 'resultado_deteccao.jpg'")

    # ==========================================
    # CASO 1: Modelo com Bounding Box Orientada (OBB)
    # ==========================================
    if hasattr(resultados, 'obb') and resultados.obb is not None and len(resultados.obb) > 0:
        print(f"\n🎯 [Modo OBB] Detectado(s) {len(resultados.obb)} visor(es) de números:")
        
        for i, box in enumerate(resultados.obb):
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            nome_classe = model.names.get(cls_id, str(cls_id))

            if 'number' not in nome_classe.lower():
                continue

            print(f"  -> Visor #{i+1}: '{nome_classe}' | Confiança: {conf:.2%}")

            # 4 vértices (x, y) do polígono
            pts = box.xyxyxyxy[0].cpu().numpy().astype("float32")

            # Desentortar/retificar via transformação de perspectiva
            soma = pts.sum(axis=1)
            diff = np.diff(pts, axis=1)
            tl = pts[np.argmin(soma)]
            br = pts[np.argmax(soma)]
            tr = pts[np.argmin(diff)]
            bl = pts[np.argmax(diff)]
            pts_ordenados = np.array([tl, tr, br, bl], dtype="float32")

            largura = max(int(np.linalg.norm(br - bl)), int(np.linalg.norm(tr - tl)))
            altura = max(int(np.linalg.norm(tr - br)), int(np.linalg.norm(tl - bl)))

            dst = np.array([[0, 0], [largura - 1, 0], [largura - 1, altura - 1], [0, altura - 1]], dtype="float32")
            matriz = cv2.getPerspectiveTransform(pts_ordenados, dst)
            visor_cortado = cv2.warpPerspective(imagem, matriz, (largura, altura))

            nome_saida = f"visor_numeros_{i+1}.jpg" if len(resultados.obb) > 1 else "visor_numeros.jpg"
            cv2.imwrite(nome_saida, visor_cortado)
            print(f"     ✂️ Visor recortado e retificado salvo em: '{nome_saida}'")

    # ==========================================
    # CASO 2: Modelo com Bounding Box Convencional (Retângulo Reto)
    # ==========================================
    elif hasattr(resultados, 'boxes') and resultados.boxes is not None and len(resultados.boxes) > 0:
        print(f"\n🎯 [Modo Padrão] Detectado(s) {len(resultados.boxes)} visor(es) de números:")
        
        for i, box in enumerate(resultados.boxes):
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            nome_classe = model.names.get(cls_id, str(cls_id))

            if 'number' not in nome_classe.lower():
                continue

            print(f"  -> Visor #{i+1}: '{nome_classe}' | Confiança: {conf:.2%}")

            # Coordenadas [x1, y1, x2, y2]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Recorta a região detectada
            visor_cortado = imagem[y1:y2, x1:x2]
            nome_saida = f"visor_numeros_{i+1}.jpg" if len(resultados.boxes) > 1 else "visor_numeros.jpg"
            cv2.imwrite(nome_saida, visor_cortado)
            print(f"     ✂️ Visor recortado salvo em: '{nome_saida}'")

    else:
        print("\n⚠️ O visor dos números não foi detectado com a confiança mínima especificada.")
        print("Dica: Tente diminuir o valor de 'CONFIANCA_MINIMA' para 0.10 e teste novamente.")


if __name__ == "__main__":
    testar_modelo()