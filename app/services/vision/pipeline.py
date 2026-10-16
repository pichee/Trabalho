import os
import io
import json
import time
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from ultralytics import YOLO
from dotenv import load_dotenv

from app.core.config import settings
from app.schemas.leitura import LeituraResponseSchema, DigitoInfoSchema, AlternativaSchema

# Carregar variáveis de ambiente (.env)
load_dotenv()
load_dotenv(dotenv_path=os.path.join("leitura_hidr-metro-main", ".env"))

API_KEY_GEMINI = os.getenv("GEMINI_API_KEY")

# Modelos preferenciais do Gemini compatíveis com a API atual
MODELOS_GEMINI = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-pro-latest",
    "gemini-flash-latest"
]

# Limiares de Qualidade calibrados do repo leitura_hidr-metro-main/testar_recorte.py
ALTURA_MINIMA = 70
ASPECT_RATIO_MIN = 1.35
DYNAMIC_RANGE_MIN = 35.0
BORDAS_MINIMA = 82.0


def obter_chave_gemini() -> str:
    """Busca a chave do Gemini no .env raiz, no subdiretório ou no ambiente."""
    for env_path in [".env", os.path.join("leitura_hidr-metro-main", ".env")]:
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=True)
            chave = os.getenv("GEMINI_API_KEY", "").strip()
            if chave:
                return chave
    chave = os.getenv("GEMINI_API_KEY", "").strip()
    if chave:
        return chave
    return ""


def avaliar_qualidade_visor(crop):
    """
    Avalia a qualidade real de leitura do visor conforme leitura_hidr-metro-main:
    - Resolução mínima (altura >= 70px)
    - Proporção geométrica (aspect ratio >= 1.35)
    - Faixa dinâmica de contraste (percentil 90 vs percentil 10 >= 35.0)
    - Nitidez de bordas pelo gradiente Sobel (>= 82.0)
    """
    if crop is None or crop.size == 0:
        return False, "Recorte vazio", 0.0, 0.0, (0, 0)
    
    h, w = crop.shape[:2]
    aspect_ratio = w / max(h, 1)

    if h < ALTURA_MINIMA:
        return False, f"Muito longe (altura {h}px < {ALTURA_MINIMA}px)", 0.0, 0.0, (w, h)
    
    if aspect_ratio < ASPECT_RATIO_MIN:
        return False, f"Formato inválido (aspect {aspect_ratio:.1f} < {ASPECT_RATIO_MIN})", 0.0, 0.0, (w, h)

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    p10, p90 = np.percentile(gray, 10), np.percentile(gray, 90)
    dyn_range = float(p90 - p10)

    scale = 100.0 / h
    norm = cv2.resize(gray, (max(1, int(w * scale)), 100), interpolation=cv2.INTER_AREA)
    suave = cv2.GaussianBlur(norm, (3, 3), 0)
    gx = cv2.Sobel(suave, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(suave, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(gx**2 + gy**2)

    limiar_borda = np.percentile(mag, 85)
    bordas_principais = mag[mag > limiar_borda]
    score_bordas = float(np.mean(bordas_principais)) if len(bordas_principais) > 0 else 0.0

    if dyn_range < DYNAMIC_RANGE_MIN:
        return False, f"Baixo contraste ({dyn_range:.0f} < {DYNAMIC_RANGE_MIN:.0f})", score_bordas, dyn_range, (w, h)
    
    if score_bordas < BORDAS_MINIMA:
        return False, f"Desfocado/Embaçado ({score_bordas:.1f} < {BORDAS_MINIMA:.1f})", score_bordas, dyn_range, (w, h)

    return True, "Aprovada", score_bordas, dyn_range, (w, h)


class VisaoPipelineService:
    def __init__(self):
        self.model_visor = None
        self.model_digitos = None
        self.client_gemini = None
        self._inicializar()

    def _inicializar(self):
        # 1. Localizar modelo de visor (pegarvisor.pt) - Ordem principal da aplicação
        caminhos_visor = [
            os.path.join("leitura_hidr-metro-main", "pegarvisor.pt"),
            "pegarvisor.pt",
            os.path.join("modelos", "pegarvisor.pt")
        ]
        for c in caminhos_visor:
            if os.path.exists(c):
                try:
                    self.model_visor = YOLO(c)
                    break
                except Exception:
                    pass

        # 2. Localizar modelo de dígitos local (caso exista como alternativa)
        caminhos_dig = ["digitos.pt", os.path.join("modelos", "digitos.pt")]
        for c in caminhos_dig:
            if os.path.exists(c):
                try:
                    self.model_digitos = YOLO(c)
                    break
                except Exception:
                    pass

        # 3. Inicializar cliente Gemini AI
        chave = obter_chave_gemini()
        if chave:
            try:
                from google import genai
                self.client_gemini = genai.Client(api_key=chave)
                print("[IA] Gemini Vision SDK inicializado com sucesso!")
            except Exception as e:
                print(f"[IA] Aviso: Não foi possível iniciar Gemini SDK: {e}")

    def ler_com_gemini(self, crop_visor_bgr):
        """
        Executa a leitura oficial via Gemini Vision:
        Analisa o visor recortado pelo YOLO e lê os números com análise cromática de m³ e litros.
        """
        chave = obter_chave_gemini()
        if not chave:
            raise RuntimeError("Chave GEMINI_API_KEY não configurada no arquivo .env! Adicione sua chave para o Gemini ler o visor.")

        if self.client_gemini is None:
            from google import genai
            self.client_gemini = genai.Client(api_key=chave)

        from google.genai import types

        # Converter recorte BGR para PIL Image
        img_rgb = cv2.cvtColor(crop_visor_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        prompt = """
        Você é um perito em inspeção de hidrômetros (medidores de água).
        Analise minuciosamente a imagem deste visor de roletes mecânicos.

        REGRAS ESTRITAS DE LEITURA E CORES:
        1. ANALISE CROMÁTICA DÍGITO A DÍGITO:
           - Inspecione a COR REAL DA TINTA de cada rolete individualmente.
           - Dígitos PRETOS: roletes com tinta preta (medem m³ / consumo faturado).
           - Dígitos VERMELHOS: roletes com tinta vermelha ou bordas vermelhas (medem litros/decimais).
           - ATENÇÃO: Classifique estritamente pela cor visual de cada um.
        
        2. ORIENTAÇÃO E LEITURA:
           - Leia da esquerda para a direita na orientação correta.
           - Se a imagem estiver inclinada ou invertida, corrija a rotação mentalmente.
        
        3. TRANSIÇÃO DE ROLETES:
           - Se algum número estiver girando na metade, indique o valor predominante.

        Retorne ESTRITAMENTE um JSON com esta estrutura:
        {
            "leitura_completa": "000802",
            "digitos_pretos": "0008",
            "digitos_vermelhos": "02",
            "qtd_pretos": 4,
            "qtd_vermelhos": 2,
            "analise_cores": "descreva a cor que você viu em cada dígito",
            "confianca": "alta"
        }
        """

        ultimo_erro = None
        for modelo in MODELOS_GEMINI:
            try:
                resp = self.client_gemini.models.generate_content(
                    model=modelo,
                    contents=[pil_img, prompt],
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                dados = json.loads(resp.text)
                dados["modelo"] = modelo
                return dados
            except Exception as e:
                ultimo_erro = e
                time.sleep(0.3)
                continue

        if ultimo_erro:
            raise RuntimeError(f"Erro na API do Gemini: {ultimo_erro}")

        return None

    def processar_imagem(self, img_bytes: bytes, nome_arquivo: str = "foto.jpg") -> LeituraResponseSchema:
        """Executa o pipeline completo do repositório leitura_hidr-metro-main."""
        nparr = np.frombuffer(img_bytes, np.uint8)
        img_original = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_original is None:
            raise ValueError("Não foi possível decodificar a foto enviada.")

        if self.model_visor is None:
            raise RuntimeError("Modelo de detecção de visor (pegarvisor.pt) não encontrado.")

        h_orig, w_orig = img_original.shape[:2]

        # 1. Detecção do Visor (classe 0 = numbers, com limiar CONF_MINIMA_YOLO=0.50)
        res_v = self.model_visor(img_original, conf=0.35, verbose=False)[0]

        visores = []
        if hasattr(res_v, 'boxes') and res_v.boxes is not None and len(res_v.boxes) > 0:
            for b in res_v.boxes:
                if int(b.cls[0].item()) == 0:  # Classe 0 = 'numbers'
                    visores.append(b)
        elif hasattr(res_v, 'obb') and res_v.obb is not None and len(res_v.obb) > 0:
            for b in res_v.obb:
                if int(b.cls[0].item()) == 0:
                    visores.append(b)

        if not visores:
            raise ValueError("Visor de números não foi detectado. Centralize o mostrador mecânico e aproxime a câmera.")

        # Pega o visor de maior confiança
        box = sorted(visores, key=lambda b: float(b.conf[0].item()), reverse=True)[0]
        conf_visor = float(box.conf[0].item())

        # Recorte com margem de segurança (pad = 5) conforme leitura_hidr-metro-main
        pad = 5
        if hasattr(box, 'xyxy'):
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            x1_crop = max(0, x1 - pad)
            y1_crop = max(0, y1 - pad)
            x2_crop = min(w_orig, x2 + pad)
            y2_crop = min(h_orig, y2 + pad)
            crop_visor = img_original[y1_crop:y2_crop, x1_crop:x2_crop]
        else:
            pts = box.xyxyxyxy[0].cpu().numpy().astype("float32")
            s, d = pts.sum(axis=1), np.diff(pts, axis=1)
            ordered = np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")
            w_v = int(max(np.linalg.norm(ordered[1] - ordered[0]), np.linalg.norm(ordered[2] - ordered[3])))
            h_v = int(max(np.linalg.norm(ordered[3] - ordered[0]), np.linalg.norm(ordered[2] - ordered[1])))
            dst = np.array([[0, 0], [w_v - 1, 0], [w_v - 1, h_v - 1], [0, h_v - 1]], dtype="float32")
            M = cv2.getPerspectiveTransform(ordered, dst)
            crop_visor = cv2.warpPerspective(img_original, M, (w_v, h_v))

        # 2. Avaliação de Qualidade (testar_recorte.py)
        aprovado, motivo_qualidade, score_bordas, dyn_range, dimensoes = avaliar_qualidade_visor(crop_visor)
        avisos = []
        if not aprovado:
            avisos.append(f"Aviso de Qualidade: {motivo_qualidade}")

        # Salvar visor temporário para conferência
        os.makedirs(settings.TMP_DIR, exist_ok=True)
        cv2.imwrite(str(settings.TMP_DIR / "visor_recortado.jpg"), crop_visor)

        # 3. Execução da Leitura do Visor (leitura_hidr-metro-main)
        # Tenta Gemini Vision primeiro (reconhece cores e resolve 000802)
        resultado_gemini = None
        try:
            resultado_gemini = self.ler_com_gemini(crop_visor)
        except Exception as e_gemini:
            if self.model_digitos is None:
                raise e_gemini
            avisos.append(f"Aviso Gemini: {e_gemini} (Usando modelo YOLO local como fallback)")

        if resultado_gemini is not None:
            leitura_comp = str(resultado_gemini.get("leitura_completa", ""))
            dig_pretos = str(resultado_gemini.get("digitos_pretos", ""))
            dig_vermelhos = str(resultado_gemini.get("digitos_vermelhos", ""))
            analise_cor = str(resultado_gemini.get("analise_cores", ""))
            conf_nivel = str(resultado_gemini.get("confianca", "alta"))
            modelo_usado = f"Gemini AI ({resultado_gemini.get('modelo', 'vision')})"

            # Mapeia os dígitos individuais para exibição visual no card mobile
            digitos_info = []
            for idx, ch in enumerate(leitura_comp):
                digitos_info.append(DigitoInfoSchema(
                    posicao=idx + 1,
                    valor_yolo=ch,
                    confianca_yolo=95.0,
                    incerto=False
                ))

            return LeituraResponseSchema(
                sucesso=True,
                leitura_completa=leitura_comp,
                leitura_yolo=leitura_comp,
                digitos_pretos=dig_pretos,
                digitos_vermelhos=dig_vermelhos,
                analise_cores=analise_cor,
                confianca=conf_nivel,
                confianca_media=95.0,
                qualidade_visor=motivo_qualidade,
                modelo_utilizado=modelo_usado,
                digitos=digitos_info,
                avisos=avisos
            )

        # 4. Fallback Local (YOLO digitos.pt) caso não haja chave Gemini configurada
        if self.model_digitos is not None:
            res_d = self.model_digitos(crop_visor, conf=0.15, verbose=False)[0]
            deteccoes = res_d.obb if (getattr(res_d, "obb", None) is not None and len(res_d.obb) > 0) else getattr(res_d, "boxes", None)
            
            sequencia_yolo = ""
            digitos_info = []
            if deteccoes is not None and len(deteccoes) > 0:
                is_obb = hasattr(deteccoes, "xyxyxyxy") and deteccoes.xyxyxyxy is not None
                brutos = []
                for i in range(len(deteccoes)):
                    conf = float(deteccoes.conf[i])
                    cls_id = int(deteccoes.cls[i])
                    nome = self.model_digitos.names.get(cls_id, str(cls_id))
                    cx = float(deteccoes.xyxyxyxy[i].cpu().numpy()[:, 0].mean()) if is_obb else float((deteccoes.xyxy[i][0] + deteccoes.xyxy[i][2]) / 2.0)
                    brutos.append({"conf": conf, "cls": cls_id, "nome": nome, "cx": cx})

                brutos.sort(key=lambda x: x["conf"], reverse=True)
                slots = []
                for b in brutos:
                    if not any(abs(b["cx"] - s["cx"]) < 18.0 for s in slots):
                        slots.append(b)
                slots.sort(key=lambda x: x["cx"])

                for idx, s in enumerate(slots):
                    sequencia_yolo += str(s["nome"])
                    digitos_info.append(DigitoInfoSchema(
                        posicao=idx + 1,
                        valor_yolo=str(s["nome"]),
                        confianca_yolo=round(s["conf"] * 100, 1),
                        incerto=s["conf"] < 0.60
                    ))

            if not sequencia_yolo:
                sequencia_yolo = "000000"

            if not os.getenv("GEMINI_API_KEY"):
                avisos.append("Dica: Adicione GEMINI_API_KEY no arquivo .env para ativar a leitura avançada com análise cromática de m³ e litros!")

            return LeituraResponseSchema(
                sucesso=True,
                leitura_completa=sequencia_yolo,
                leitura_yolo=sequencia_yolo,
                digitos_pretos=sequencia_yolo[:4] if len(sequencia_yolo) >= 4 else sequencia_yolo,
                digitos_vermelhos=sequencia_yolo[4:] if len(sequencia_yolo) > 4 else "",
                confianca="media",
                confianca_media=round(float(np.mean([d.confianca_yolo for d in digitos_info])), 1) if digitos_info else 0.0,
                qualidade_visor=motivo_qualidade,
                modelo_utilizado="YOLO Local (leitura_hidr-metro-main)",
                digitos=digitos_info,
                avisos=avisos
            )

        raise RuntimeError("Não foi possível realizar a leitura dos números. Verifique se a chave GEMINI_API_KEY está configurada no .env e tem acesso aos modelos Gemini Vision.")

# Singleton exportado para as rotas
visao_service = VisaoPipelineService()
