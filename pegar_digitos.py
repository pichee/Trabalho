import os
import sys
import glob
import cv2
import numpy as np
from ultralytics import YOLO

# Garantir codificação UTF-8 no terminal Windows para evitar UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ==========================================
# CONFIGURAÇÕES
# ==========================================
if os.path.exists("digitos.pt"):
    CAMINHO_MODELO = "digitos.pt"
elif os.path.exists("modelos/digitos.pt"):
    CAMINHO_MODELO = "modelos/digitos.pt"
else:
    CAMINHO_MODELO = "digitos.pt"

PASTA_TMP = "tmp"
CONFIANCA_MINIMA = 0.15          # Limiar para detecção de candidatos
LIMIAR_BAIXA_CONFIANCA = 0.60    # Abaixo de 60% é considerado duvidoso


def buscar_visor():
    """Busca a imagem do visor recortado pelo script anterior."""
    candidatos = [
        "visor_numeros.jpg",
        "visor_recortado_1.jpg",
        "visor_numeros_0.jpg",
        "visor_extraido.jpg"
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
            
    outros = glob.glob("visor*.jpg") + glob.glob("*visor*.jpg")
    if outros:
        return outros[0]
        
    return None


def detectar_e_desentortar_visor(img):
    """
    Detecta automaticamente o ângulo de inclinação do visor (linhas horizontais)
    e o retifica para que os números fiquem perfeitamente alinhados na horizontal.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, minLineLength=25, maxLineGap=10)

    if lines is not None and len(lines) > 0:
        angles = []
        for l in lines:
            vals = l[0] if len(l.shape) > 1 and l.shape[0] == 1 else l
            if len(vals) == 4:
                x1, y1, x2, y2 = vals
                ang = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                if 5 <= abs(ang) <= 35:
                    angles.append(ang)

        if len(angles) >= 3:
            ang_mediana = float(np.median(angles))
            if abs(ang_mediana) >= 3.0:
                h, w = img.shape[:2]
                M = cv2.getRotationMatrix2D((w // 2, h // 2), ang_mediana, 1.0)
                img_retificada = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return img_retificada, ang_mediana

    return img, 0.0


def identificar_e_recortar_digitos():
    print("=" * 65)
    print("IDENTIFICAÇÃO E RECORTE DOS DÍGITOS PARA A PASTA 'tmp'")
    print("=" * 65)

    # 1. Carregar Modelo de Dígitos
    print(f"\n🔄 Carregando modelo de dígitos: '{CAMINHO_MODELO}'...")
    try:
        model = YOLO(CAMINHO_MODELO)
        print("✅ Modelo carregado com sucesso!")
        print(f"📋 Classes do modelo: {model.names}")
    except Exception as e:
        print(f"❌ Erro ao carregar o modelo '{CAMINHO_MODELO}': {e}")
        return

    # 2. Localizar imagem do visor
    imagem_visor_path = buscar_visor()
    if imagem_visor_path is None:
        print("\n❌ Nenhuma imagem de visor encontrada na pasta!")
        print("💡 Execute primeiro o script 'pegar_visor.py' para gerar o 'visor_numeros.jpg'.")
        return

    print(f"\n👉 Processando visor: '{imagem_visor_path}'")
    img_visor = cv2.imread(imagem_visor_path)
    if img_visor is None:
        print(f"❌ Erro: Não foi possível abrir a imagem '{imagem_visor_path}'.")
        return

    # 3. Alinhamento automático (Deskew) do visor se estiver inclinado
    img_processar, angulo_detectado = detectar_e_desentortar_visor(img_visor)
    if abs(angulo_detectado) >= 3.0:
        print(f"📐 Visor inclinado detectado ({angulo_detectado:.1f}°). Aplicada retificação automática!")
        cv2.imwrite(os.path.join(PASTA_TMP, "visor_retificado.jpg") if os.path.exists(PASTA_TMP) else "visor_retificado.jpg", img_processar)
    else:
        print("📐 Visor alinhado horizontalmente.")

    h_v, w_v = img_processar.shape[:2]
    print(f"📐 Dimensões do visor: {w_v}x{h_v} píxeis")

    # 4. Criar/Limpar pasta tmp
    os.makedirs(PASTA_TMP, exist_ok=True)
    for f in os.listdir(PASTA_TMP):
        caminho_arq = os.path.join(PASTA_TMP, f)
        if os.path.isfile(caminho_arq):
            try:
                os.remove(caminho_arq)
            except Exception:
                pass
    print(f"📁 Pasta '{PASTA_TMP}' pronta para receber os recortes.")

    # 5. Executar Detecção com YOLO
    print(f"\n🔍 Detectando dígitos...")
    res = model(img_processar, conf=CONFIANCA_MINIMA, verbose=False)[0]

    deteccoes = res.obb if (getattr(res, "obb", None) is not None and len(res.obb) > 0) else getattr(res, "boxes", None)

    if deteccoes is None or len(deteccoes) == 0:
        print("⚠️ Nenhum dígito detectado no visor!")
        print("Dica: Tente aproximar a câmera ou diminuir CONFIANCA_MINIMA para 0.10.")
        return

    # Extrair informações completas
    is_obb = hasattr(deteccoes, "xyxyxyxy") and deteccoes.xyxyxyxy is not None
    detalhes = []

    for i in range(len(deteccoes)):
        conf = float(deteccoes.conf[i])
        cls_id = int(deteccoes.cls[i])
        nome_c = model.names.get(cls_id, str(cls_id))

        if is_obb:
            pts = deteccoes.xyxyxyxy[i].cpu().numpy()
            cx = float(pts[:, 0].mean())
            cy = float(pts[:, 1].mean())
            x1 = float(pts[:, 0].min())
            x2 = float(pts[:, 0].max())
            y1 = float(pts[:, 1].min())
            y2 = float(pts[:, 1].max())
            item = {
                "conf": conf,
                "cls": cls_id,
                "nome": nome_c,
                "cx": cx,
                "cy": cy,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "pts": pts
            }
        else:
            coords = deteccoes.xyxy[i].cpu().numpy()
            x1, y1, x2, y2 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
            item = {
                "conf": conf,
                "cls": cls_id,
                "nome": nome_c,
                "cx": (x1 + x2) / 2.0,
                "cy": (y1 + y2) / 2.0,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "pts": None
            }
        detalhes.append(item)

    # 6. Agrupar detecções concorrentes no mesmo slot horizontal (raio de 18 pixels)
    detalhes.sort(key=lambda x: x["conf"], reverse=True)
    filtrados = []

    for det in detalhes:
        # Procurar se já existe um slot próximo
        encontrado = None
        for f in filtrados:
            if abs(det["cx"] - f["cx"]) < 18.0:
                encontrado = f
                break

        if encontrado is None:
            # Novo slot detectado
            det["concorrentes"] = []
            filtrados.append(det)
        else:
            # Já existe uma detecção para este slot
            encontrado["concorrentes"].append((det["nome"], det["conf"]))

    # 7. Ordenar estritamente da esquerda para a direita (eixo X)
    filtrados.sort(key=lambda x: x["cx"])

    print(f"🎯 Total de dígitos localizados: {len(filtrados)}\n")
    print("-" * 65)

    sequencia = ""
    linhas_relatorio = []
    avisos_duvida = []

    for idx, det in enumerate(filtrados):
        pos = idx + 1
        x1 = max(0, int(round(det["x1"])))
        y1 = max(0, int(round(det["y1"])))
        x2 = min(w_v, int(round(det["x2"])))
        y2 = min(h_v, int(round(det["y2"])))

        # Recorte do número individual
        if is_obb and det["pts"] is not None:
            # Usar perspectiva dos 4 cantos para retificar a caixa orientada
            pts = det["pts"].astype(np.float32)
            s = pts.sum(axis=1)
            d = np.diff(pts, axis=1)
            tl = pts[np.argmin(s)]
            br = pts[np.argmax(s)]
            tr = pts[np.argmin(d)]
            bl = pts[np.argmax(d)]
            ordered = np.array([tl, tr, br, bl], dtype=np.float32)
            w_crop = max(10, int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl))))
            h_crop = max(10, int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr))))
            dst = np.array([[0, 0], [w_crop - 1, 0], [w_crop - 1, h_crop - 1], [0, h_crop - 1]], dtype=np.float32)
            M = cv2.getPerspectiveTransform(ordered, dst)
            digito_crop = cv2.warpPerspective(img_processar, M, (w_crop, h_crop))
        else:
            digito_crop = img_processar[y1:y2, x1:x2]

        if digito_crop is None or digito_crop.size == 0:
            continue

        nome_arquivo = f"digito_{pos}_valor_{det['nome']}.jpg"
        caminho_salvo = os.path.join(PASTA_TMP, nome_arquivo)
        cv2.imwrite(caminho_salvo, digito_crop)

        conf_pct = det["conf"] * 100
        eh_duvidoso = det["conf"] < LIMIAR_BAIXA_CONFIANCA

        # Montar lista de concorrentes se houver
        alt_str = ""
        if det["concorrentes"]:
            alt_list = [f"'{c_nome}' ({c_conf*100:.1f}%)" for c_nome, c_conf in det["concorrentes"][:2]]
            alt_str = f" | Alternativas detectadas: {', '.join(alt_list)}"

        if eh_duvidoso:
            status_tag = f"⚠️ [INCERTO: {conf_pct:5.1f}%]{alt_str}"
            avisos_duvida.append(f"Posição {pos}: previsto '{det['nome']}' ({conf_pct:.1f}%){alt_str}")
        else:
            status_tag = f"✅ [Confiança: {conf_pct:5.1f}%]"

        print(f"  👉 Posição {pos}: Dígito '{det['nome']}'  {status_tag}")
        linhas_relatorio.append(f"Posição {pos}: '{det['nome']}' (conf: {conf_pct:.1f}%){alt_str}")
        sequencia += str(det["nome"])

    # 8. Salvar a imagem com todas as marcações
    caminho_anotada = os.path.join(PASTA_TMP, "deteccao_conferir.jpg")
    cv2.imwrite(caminho_anotada, res.plot())

    # 9. Salvar o arquivo de leitura simples
    caminho_txt = os.path.join(PASTA_TMP, "leitura.txt")
    with open(caminho_txt, "w", encoding="utf-8") as f_txt:
        f_txt.write(sequencia)

    # 10. Salvar relatório analítico completo
    caminho_relatorio = os.path.join(PASTA_TMP, "leitura_relatorio.txt")
    with open(caminho_relatorio, "w", encoding="utf-8") as f_rel:
        f_rel.write(f"SEQUÊNCIA: {sequencia}\n")
        f_rel.write("=" * 40 + "\n")
        for linha in linhas_relatorio:
            f_rel.write(linha + "\n")
        if avisos_duvida:
            f_rel.write("\nALERTAS DE BAIXA CONFIANÇA:\n")
            for av in avisos_duvida:
                f_rel.write("- " + av + "\n")

    print("-" * 65)
    print(f"\n🎉 SEQUÊNCIA COMPLETA OBTIDA:  {sequencia}")
    if avisos_duvida:
        print("\n⚠️  ATENÇÃO: Foram identificadas posições com baixa certeza do modelo:")
        for av in avisos_duvida:
            print(f"   • {av}")
        print("   💡 Dica: Se o número real for diferente, confira a alternativa listada acima.")
    print(f"\n💾 Sequência salva em:        '{caminho_txt}'")
    print(f"📋 Relatório salvo em:        '{caminho_relatorio}'")
    print(f"🖼️ Imagem anotada salva em:   '{caminho_anotada}'")
    print("=" * 65)


if __name__ == "__main__":
    identificar_e_recortar_digitos()
