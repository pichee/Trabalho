import os
import sys
import glob
from PIL import Image

print("=" * 60)
print("TESTE DE DIAGNÓSTICO E EXTRAÇÃO DE DÍGITOS")
print("=" * 60)

# 1. Informações do Ambiente
try:
    import torch
    import ultralytics
    from ultralytics import YOLO
    print(f"[OK] Python: {sys.version.split()[0]}")
    print(f"[OK] Ultralytics: {ultralytics.__version__}")
    print(f"[OK] PyTorch: {torch.__version__} (CUDA: {torch.cuda.is_available()})")
except ImportError as e:
    print(f"[ERRO] Falha ao importar bibliotecas: {e}")
    sys.exit(1)

# 2. Listar modelos disponíveis
print("\n--- MODELOS ENCONTRADOS ---")
modelos = glob.glob("**/*.pt", recursive=True)
for m in modelos:
    print(f"  -> {m} ({os.path.getsize(m) / (1024*1024):.2f} MB)")

if not modelos:
    print("  Nenhum modelo .pt encontrado!")
    sys.exit(1)

# 3. Listar imagens disponíveis
print("\n--- IMAGENS DISPONÍVEIS ---")
imagens = glob.glob("*.jpg") + glob.glob("*.jpeg") + glob.glob("*.png")
for img in imagens:
    try:
        with Image.open(img) as im:
            print(f"  -> {img} (dimensões: {im.size[0]}x{im.size[1]})")
    except Exception:
        print(f"  -> {img}")

# 4. Imagem alvo de teste
imagem_teste = "visor_numeros_0.jpg"
if not os.path.exists(imagem_teste):
    # Se não existe visor_numeros_0.jpg, tenta pegar 2.jpeg ou a primeira imagem
    if os.path.exists("2.jpeg"):
        imagem_teste = "2.jpeg"
    elif imagens:
        imagem_teste = imagens[0]
    else:
        print("\n[ERRO] Nenhuma imagem de teste encontrada!")
        sys.exit(1)

print(f"\n=> Imagem selecionada para teste: {imagem_teste}")

# 5. Testar modelos com a imagem
modelo_caminho = "modelos/digitos.pt"
if not os.path.exists(modelo_caminho) and modelos:
    modelo_caminho = modelos[0]

print(f"=> Carregando modelo: {modelo_caminho}")
model = YOLO(modelo_caminho)

print(f"   Task: {getattr(model, 'task', 'desconhecido')}")
print(f"   Nomes das classes ({len(model.names)}): {model.names}")

# Teste com diferentes parâmetros de confiança e resolução
configuracoes = [
    {"conf": 0.25, "imgsz": None, "desc": "Padrão (conf=0.25)"},
    {"conf": 0.10, "imgsz": None, "desc": "Baixa confiança (conf=0.10)"},
    {"conf": 0.01, "imgsz": None, "desc": "Confiança mínima (conf=0.01)"},
    {"conf": 0.25, "imgsz": 640,  "desc": "Forçar imgsz=640 (conf=0.25)"},
]

sucesso = False

for config in configuracoes:
    print(f"\n------------------------------------------------------------")
    print(f"Testando configuração: {config['desc']}")
    
    kwargs = {"conf": config["conf"], "verbose": False}
    if config["imgsz"] is not None:
        kwargs["imgsz"] = config["imgsz"]
        
    results = model(imagem_teste, **kwargs)
    r = results[0]
    
    qtd_r = len(r)
    tem_boxes = r.boxes is not None and len(r.boxes) > 0
    tem_obb = r.obb is not None and len(r.obb) > 0
    
    print(f"   Resultado r.verbose(): '{r.verbose().strip()}'")
    print(f"   r.boxes presente? {tem_boxes} (len={len(r.boxes) if r.boxes is not None else 0})")
    print(f"   r.obb presente?   {tem_obb} (len={len(r.obb) if r.obb is not None else 0})")
    
    alvo_deteccoes = None
    modo = ""
    if tem_obb:
        alvo_deteccoes = r.obb
        modo = "OBB (Oriented Bounding Box)"
    elif tem_boxes:
        alvo_deteccoes = r.boxes
        modo = "Bounding Boxes convencional"
        
    if alvo_deteccoes is not None and len(alvo_deteccoes) > 0:
        print(f"   [SUCESSO!] Deteções encontradas via {modo}: {len(alvo_deteccoes)} caixas!")
        
        # Salvar imagem anotada deste teste
        nome_debug_img = f"teste_debug_{config['conf']}.jpg"
        r.save(filename=nome_debug_img)
        print(f"   Imagem com caixas salva em: {nome_debug_img}")
        
        # Extrair e processar os dígitos
        coords_arr = alvo_deteccoes.xyxy.cpu().numpy()
        confs_arr = alvo_deteccoes.conf.cpu().numpy()
        cls_arr = alvo_deteccoes.cls.cpu().numpy()
        
        detalhes = []
        for coords, conf_val, cls_id in zip(coords_arr, confs_arr, cls_arr):
            c_int = int(cls_id)
            nome_c = model.names.get(c_int, str(c_int)) if isinstance(model.names, dict) else str(c_int)
            detalhes.append({
                "x1": float(coords[0]),
                "y1": float(coords[1]),
                "x2": float(coords[2]),
                "y2": float(coords[3]),
                "conf": float(conf_val),
                "cls": c_int,
                "nome": nome_c
            })
            
        # Filtrar duplicatas (IoU / sobreposição horizontal)
        detalhes.sort(key=lambda x: x["conf"], reverse=True)
        filtrados = []
        for det in detalhes:
            mantem = True
            for f in filtrados:
                inter_left = max(det["x1"], f["x1"])
                inter_right = min(det["x2"], f["x2"])
                overlap = max(0.0, inter_right - inter_left)
                menor_w = min(det["x2"] - det["x1"], f["x2"] - f["x1"])
                if menor_w > 0 and (overlap / menor_w) > 0.5:
                    mantem = False
                    break
            if mantem:
                filtrados.append(det)
                
        # Ordenar da esquerda para a direita
        filtrados.sort(key=lambda x: x["x1"])
        
        pasta_saida = "numeros"
        os.makedirs(pasta_saida, exist_ok=True)
        
        im_orig = Image.open(imagem_teste)
        w_img, h_img = im_orig.size
        sequencia = ""
        
        print(f"\n   Recortando {len(filtrados)} dígitos ordenados:")
        for idx, det in enumerate(filtrados):
            x1 = max(0, int(round(det["x1"])))
            y1 = max(0, int(round(det["y1"])))
            x2 = min(w_img, int(round(det["x2"])))
            y2 = min(h_img, int(round(det["y2"])))
            
            if x2 <= x1 or y2 <= y1:
                continue
                
            crop_digito = im_orig.crop((x1, y1, x2, y2))
            caminho_crop = os.path.join(pasta_saida, f"digito_{idx+1}_valor_{det['nome']}.jpg")
            crop_digito.save(caminho_crop)
            
            sequencia += str(det["nome"])
            print(f"     Dígito {idx+1}: '{det['nome']}' (conf: {det['conf']:.2f}) -> {caminho_crop}")
            
        with open(os.path.join(pasta_saida, "resultado_leitura.txt"), "w") as f_txt:
            f_txt.write(sequencia)
            
        print(f"\n   >>> SEQUÊNCIA COMPLETA OBTIDA: '{sequencia}' <<<")
        print(f"   Salva em: '{os.path.join(pasta_saida, 'resultado_leitura.txt')}'")
        sucesso = True
        break

if not sucesso:
    print("\n" + "=" * 60)
    print("[ATENÇÃO] Nenhuma caixa foi detectada em nenhuma das configurações!")
    print("Possíveis causas:")
    print("1. O modelo modelos/digitos.pt espera uma imagem em formato/resolução diferente.")
    print("2. A imagem visor_numeros_0.jpg não contém os números no formato esperado pelo modelo.")
    print("=" * 60)
else:
    print("\n" + "=" * 60)
    print("Processamento concluído com êxito!")
    print("=" * 60)
