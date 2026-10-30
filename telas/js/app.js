document.addEventListener("DOMContentLoaded", () => {
    // 1. Verificação de Autenticação
    const token = localStorage.getItem("hidroreader_token");
    if (!token) {
        window.location.href = "/login";
        return;
    }

    function sairELimparSessao(msg = "Sessão expirada. Faça login novamente.") {
        localStorage.removeItem("hidroreader_token");
        localStorage.removeItem("hidroreader_user");
        localStorage.removeItem("hidroreader_name");
        showToast(msg, false);
        setTimeout(() => {
            window.location.href = "/login";
        }, 500);
    }

    const btnLogout = document.getElementById("btn-logout");
    if (btnLogout) {
        btnLogout.addEventListener("click", () => {
            sairELimparSessao("Você saiu da conta.");
        });
    }

    // 2. Elementos da Interface
    const selectCondominio = document.getElementById("select-condominio");
    const selectApartamento = document.getElementById("select-apartamento");
    const btnAddApto = document.getElementById("btn-add-apto");

    // Elementos de IHC: Alerta de Duplicidade e Progresso
    const cardAvisoDuplicidade = document.getElementById("card-aviso-duplicidade");
    const avisoTituloDuplicidade = document.getElementById("aviso-titulo-duplicidade");
    const avisoBadgeTempo = document.getElementById("aviso-badge-tempo");
    const avisoValorAnt = document.getElementById("aviso-valor-ant");
    const avisoOpAnt = document.getElementById("aviso-op-ant");
    const progressoTextoStats = document.getElementById("progresso-texto-stats");
    const progressoBarraFill = document.getElementById("progresso-barra-fill");
    const alertaModalDuplicata = document.getElementById("alerta-modal-duplicata");
    const modalDupVal = document.getElementById("modal-dup-val");
    const modalDupData = document.getElementById("modal-dup-data");

    let mapaApartamentos = {};
    const fileInputCamera = document.getElementById("file-input-camera");
    const fileInputGallery = document.getElementById("file-input-gallery");
    const btnProcess = document.getElementById("btn-process");
    const previewImg = document.getElementById("preview-img");
    const placeholderView = document.getElementById("placeholder-view");
    const loadingView = document.getElementById("loading-view");
    const cameraCard = document.getElementById("camera-card");

    // Painel de Resultado
    const resultCard = document.getElementById("result-card");
    const readingApto = document.getElementById("reading-apto");
    const readingVal = document.getElementById("reading-val");
    const readingMeta = document.getElementById("reading-meta");
    const valPretos = document.getElementById("val-pretos");
    const valVermelhos = document.getElementById("val-vermelhos");
    const readingStatusPill = document.getElementById("reading-status-pill");
    const digitsContainer = document.getElementById("digits-container");
    const alertsContainer = document.getElementById("alerts-container");
    const toast = document.getElementById("toast");

    // Modal de Confirmação da Leitura
    const modalConfirmacao = document.getElementById("modal-confirmacao");
    const confirmAptoText = document.getElementById("confirm-apto-text");
    const confirmImgPreview = document.getElementById("confirm-img-preview");
    const confirmReadingNumber = document.getElementById("confirm-reading-number");
    const inputOriginalIaVal = document.getElementById("input-original-ia-val");
    const inputConfirmVal = document.getElementById("input-confirm-val");
    const btnDiscardConfirm = document.getElementById("btn-discard-confirm");
    const btnSaveConfirm = document.getElementById("btn-save-confirm");

    let currentFile = null;
    let currentObjectUrl = null;
    let ultimaPredicaoIA = null;
    let leituraIaImutavel = "";

    function showToast(msg, isSuccess = true) {
        if (!toast) return;
        toast.textContent = msg;
        toast.style.background = isSuccess ? "#0284c7" : "#dc2626";
        toast.classList.add("show");
        setTimeout(() => {
            toast.classList.remove("show");
        }, 3200);
    }

    function abrirModal(modal) {
        if (!modal) return;
        modal.style.setProperty("display", "flex", "important");
        requestAnimationFrame(() => {
            modal.classList.add("active");
        });
    }

    function fecharModal(modal) {
        if (!modal) return;
        modal.classList.remove("active");
        setTimeout(() => {
            if (!modal.classList.contains("active")) {
                modal.style.setProperty("display", "none", "important");
            }
        }, 280);
    }

    // 3. Carregar Condomínios e Apartamentos em Cascata
    async function carregarCondominios() {
        try {
            const resp = await fetch("/api/v1/apartamentos/condominios", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (resp.status === 401) {
                sairELimparSessao("Sessão inválida. Redirecionando para login...");
                return;
            }
            const condominios = await resp.json();
            selectCondominio.innerHTML = "";

            if (!condominios || condominios.length === 0) {
                condominios.push("Residencial das Palmeiras");
            }

            condominios.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c;
                opt.textContent = c;
                selectCondominio.appendChild(opt);
            });

            // Verifica se veio via URL (?apto=101&condo=...) ou salvo em sessão
            const urlParams = new URLSearchParams(window.location.search);
            const aptoUrl = urlParams.get("apto") || localStorage.getItem("hidroreader_apto_ativo");
            const condoUrl = urlParams.get("condo") || localStorage.getItem("hidroreader_condo_ativo");

            if (condoUrl && condominios.includes(condoUrl)) {
                selectCondominio.value = condoUrl;
            }

            const condoAtivo = selectCondominio.value || condominios[0];
            await carregarApartamentosPorCondominio(condoAtivo, aptoUrl);
        } catch (e) {
            selectCondominio.innerHTML = '<option value="">Erro ao carregar condomínios</option>';
        }
    }

    function atualizarAvisoDuplicidade(aptoNum) {
        if (!cardAvisoDuplicidade) return;
        const ap = mapaApartamentos[String(aptoNum)];
        if (ap && (ap.lido_hoje || ap.lido_este_mes)) {
            cardAvisoDuplicidade.style.display = "flex";
            if (ap.lido_hoje) {
                if (avisoTituloDuplicidade) avisoTituloDuplicidade.textContent = "APTO JÁ MEDIDO HOJE!";
                if (avisoBadgeTempo) avisoBadgeTempo.textContent = "Hoje";
            } else {
                if (avisoTituloDuplicidade) avisoTituloDuplicidade.textContent = "APTO JÁ MEDIDO ESTE MÊS!";
                if (avisoBadgeTempo) avisoBadgeTempo.textContent = ap.ultima_leitura_data || "Este mês";
            }
            if (avisoValorAnt) avisoValorAnt.textContent = `${ap.ultima_leitura_valor || "---"} m³`;
            if (avisoOpAnt) avisoOpAnt.textContent = ap.ultima_leitura_operador || "Operador";
        } else {
            cardAvisoDuplicidade.style.display = "none";
        }
    }

    function atualizarBarraProgresso(aptos) {
        if (!progressoTextoStats || !progressoBarraFill) return;
        const total = aptos.length;
        const lidos = aptos.filter(a => a.lido_este_mes).length;
        const pct = total > 0 ? Math.round((lidos / total) * 100) : 0;
        progressoTextoStats.textContent = `${lidos} de ${total} medidos (${pct}%)`;
        progressoBarraFill.style.width = `${pct}%`;
    }

    async function carregarApartamentosPorCondominio(condoNome, aptoPreSelecionado = null) {
        selectApartamento.innerHTML = '<option value="">Carregando apartamentos...</option>';
        mapaApartamentos = {};
        try {
            const resp = await fetch(`/api/v1/apartamentos?condominio=${encodeURIComponent(condoNome)}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const aptos = await resp.json();

            atualizarBarraProgresso(aptos);

            selectApartamento.innerHTML = '<option value="">-- Selecione o Apartamento --</option>';
            aptos.forEach(ap => {
                mapaApartamentos[String(ap.numero)] = ap;
                const opt = document.createElement("option");
                opt.value = ap.numero;

                if (ap.lido_hoje) {
                    opt.textContent = `✅ Apto ${ap.numero} • LIDO HOJE (${ap.ultima_leitura_valor || "---"} m³) - ${ap.bloco || "Bloco A"}`;
                    opt.style.color = "#047857";
                    opt.style.fontWeight = "bold";
                } else if (ap.lido_este_mes) {
                    opt.textContent = `📅 Apto ${ap.numero} • Lido no mês (${ap.ultima_leitura_valor || "---"} m³) - ${ap.bloco || "Bloco A"}`;
                    opt.style.color = "#0284c7";
                } else {
                    opt.textContent = `⏳ Apto ${ap.numero} • PENDENTE - ${ap.bloco || "Bloco A"}`;
                    opt.style.color = "#b45309";
                }
                selectApartamento.appendChild(opt);
            });

            if (aptoPreSelecionado) {
                const existe = aptos.some(a => String(a.numero) === String(aptoPreSelecionado));
                if (existe) {
                    selectApartamento.value = String(aptoPreSelecionado);
                }
            }

            atualizarAvisoDuplicidade(selectApartamento.value);
        } catch (e) {
            selectApartamento.innerHTML = '<option value="">Erro ao listar apartamentos</option>';
        }
    }

    function salvarSelecaoAtual() {
        if (selectCondominio && selectCondominio.value) {
            localStorage.setItem("hidroreader_condo_ativo", selectCondominio.value);
        }
        if (selectApartamento && selectApartamento.value) {
            localStorage.setItem("hidroreader_apto_ativo", selectApartamento.value);
        }
    }

    if (selectCondominio) {
        selectCondominio.addEventListener("change", async () => {
            const cVal = selectCondominio.value;
            localStorage.setItem("hidroreader_condo_ativo", cVal);
            await carregarApartamentosPorCondominio(cVal);
        });
    }

    if (selectApartamento) {
        selectApartamento.addEventListener("change", () => {
            const aVal = selectApartamento.value;
            localStorage.setItem("hidroreader_apto_ativo", aVal);
            atualizarAvisoDuplicidade(aVal);
        });
    }

    carregarCondominios();

    // Botão para cadastrar novo apartamento rapidamente no condomínio selecionado
    if (btnAddApto) {
        btnAddApto.addEventListener("click", async () => {
            const condoAtual = selectCondominio.value || "Residencial das Palmeiras";
            const novoNumero = prompt(`Digite o número do novo apartamento para ${condoAtual} (ex: 501):`);
            if (!novoNumero || !novoNumero.trim()) return;

            const bloco = prompt("Bloco (ex: Bloco A, Bloco B):", "Bloco A") || "Bloco A";

            try {
                const resp = await fetch("/api/v1/apartamentos", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        numero: novoNumero.trim(),
                        bloco: bloco.trim(),
                        condominio: condoAtual
                    })
                });

                const data = await resp.json();
                if (!resp.ok) {
                    showToast(data.detail || "Erro ao cadastrar apartamento.", false);
                    return;
                }

                await carregarApartamentosPorCondominio(condoAtual, data.numero);
                showToast(`Apartamento ${data.numero} cadastrado com sucesso!`, true);
            } catch (err) {
                showToast("Erro: " + err.message, false);
            }
        });
    }

    // 4. Captura com Processamento 100% no Servidor (Zero uso de RAM gráfica no celular)
    let fotoPreCarregadaServidor = false;

    function sendDiag(ev, info = "") {
        try {
            const url = `/api/v1/leituras/diag?ev=${encodeURIComponent(ev)}&info=${encodeURIComponent(info)}`;
            if (navigator.sendBeacon) {
                navigator.sendBeacon(url);
            } else {
                fetch(url, { method: "POST", keepalive: true }).catch(() => {});
            }
        } catch (e) {}
    }

    sendDiag("page_load", `camFiles=${fileInputCamera && fileInputCamera.files ? fileInputCamera.files.length : 0}`);

    async function restaurarFotoPendenteServidor() {
        try {
            const resp = await fetch("/api/v1/leituras/pre-carregar", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!resp.ok) return;
            const dados = await resp.json();
            if (dados && dados.tem_foto && dados.preview_b64) {
                fotoPreCarregadaServidor = true;
                previewImg.src = dados.preview_b64;
                previewImg.style.display = "block";
                if (placeholderView) placeholderView.style.display = "none";
                btnProcess.disabled = false;
                sendDiag("restaurou_servidor", `${dados.tamanho_kb}KB`);
            }
        } catch (e) {}
    }

    async function aplicarFotoCapturada(file, origem = "câmera") {
        if (!file) {
            showToast("Nenhum arquivo de imagem recebido.", false);
            return;
        }

        if (file.size === 0) {
            showToast("O app de câmera retornou arquivo vazio. Tente pela opção de Galeria.", false);
            return;
        }

        currentFile = file;
        sendDiag("aplicar_foto_inicio", `${origem}_${file.name}_${file.size}`);

        // Feedback visual imediato no visor
        if (placeholderView) placeholderView.style.display = "none";
        if (loadingView) {
            loadingView.style.display = "flex";
            const lTitle = loadingView.querySelector(".loading-title");
            const lSub = loadingView.querySelector(".loading-subtitle");
            if (lTitle) lTitle.textContent = "Carregando foto no visor...";
            if (lSub) lSub.textContent = "O servidor está otimizando a imagem...";
        }

        try {
            // Envia o arquivo direto do disco para o servidor redimensionar com OpenCV (ZERO uso de RAM no celular!)
            const formPre = new FormData();
            formPre.append("foto", file);

            const resp = await fetch("/api/v1/leituras/pre-carregar", {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` },
                body: formPre
            });

            if (resp.ok) {
                const dados = await resp.json();
                fotoPreCarregadaServidor = true;
                previewImg.src = dados.preview_b64;
                previewImg.style.display = "block";
                btnProcess.disabled = false;
                if (resultCard) resultCard.classList.remove("active");
                sendDiag("pre_carregar_sucesso", `${dados.tamanho_kb}KB`);
                showToast(`📸 Foto pronta (${dados.tamanho_kb} KB)! Clique em Analisar.`, true);
                return;
            }
        } catch (err) {
            sendDiag("pre_carregar_erro", err.message);
        } finally {
            if (loadingView) loadingView.style.display = "none";
        }

        // Fallback local leve caso a chamada de pré-carregamento falhe
        try {
            if (currentObjectUrl) {
                try { URL.revokeObjectURL(currentObjectUrl); } catch (e) {}
            }
            currentObjectUrl = URL.createObjectURL(file);
            previewImg.src = currentObjectUrl;
            previewImg.style.display = "block";
            btnProcess.disabled = false;
            if (resultCard) resultCard.classList.remove("active");
            showToast("📸 Foto pronta! Clique em Analisar.", true);
        } catch (err) {
            if (placeholderView) placeholderView.style.display = "flex";
            showToast("Erro ao exibir imagem.", false);
        }
    }

    let isProcessingCapture = false;
    let ultimoArquivoKey = "";

    async function lidarSelecaoArquivo(input, origem) {
        if (!input || !input.files || input.files.length === 0) return;
        if (isProcessingCapture) return;

        const file = input.files[0];
        if (!file) return;

        const fileKey = `${file.name}_${file.size}_${file.lastModified}`;
        if (fileKey === ultimoArquivoKey && (currentFile || fotoPreCarregadaServidor)) return;

        isProcessingCapture = true;
        ultimoArquivoKey = fileKey;
        try {
            await aplicarFotoCapturada(file, origem);
        } catch (err) {
            console.error("Erro na captura:", err);
            ultimoArquivoKey = "";
        } finally {
            isProcessingCapture = false;
        }
    }

    const inlineVideo = document.getElementById("inline-camera-video");
    let inlineStream = null;

    // =========================================================================
    // ESCUDO ANTI-REFRESH ANDROID (Mantém o Chrome como Foreground Service)
    // =========================================================================
    // No Android, quando a Câmera nativa abre, o sistema mata abas em segundo plano
    // (oom_score_adj = 900), exceto abas com MediaSession ativa (> 5s de duração)
    // e Web Locks ativos (oom_score_adj = 100 - Foreground Media Service).
    let shieldAudio = null;
    let shieldAudioUrl = null;
    let shieldLockResolver = null;
    let shieldHeartbeat = null;

    function criarWavInaudivel6Segundos() {
        const sampleRate = 8000;
        const durationSeconds = 6; // Chromium exige >= 5s para MediaContentType::kPersistent
        const numSamples = sampleRate * durationSeconds;
        const buffer = new ArrayBuffer(44 + numSamples * 2);
        const view = new DataView(buffer);

        function writeStr(offset, str) {
            for (let i = 0; i < str.length; i++) {
                view.setUint8(offset + i, str.charCodeAt(i));
            }
        }

        writeStr(0, "RIFF");
        view.setUint32(4, 36 + numSamples * 2, true);
        writeStr(8, "WAVE");
        writeStr(12, "fmt ");
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true); // PCM
        view.setUint16(22, 1, true); // Mono
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeStr(36, "data");
        view.setUint32(40, numSamples * 2, true);

        // Onda senoidal de 25Hz com amplitude mínima (16 de 32767):
        // Inaudível ao ouvido humano, mas detectada pelo AudioPowerMonitor do Chrome
        for (let i = 0; i < numSamples; i++) {
            const sample = Math.round(Math.sin((2 * Math.PI * 25 * i) / sampleRate) * 16);
            view.setInt16(44 + i * 2, sample, true);
        }

        return new Blob([buffer], { type: "audio/wav" });
    }

    function liberarMemoriaVisualAntesDaCamera() {
        try {
            if (currentObjectUrl) {
                URL.revokeObjectURL(currentObjectUrl);
                currentObjectUrl = null;
            }
            if (previewImg && !fotoPreCarregadaServidor) {
                previewImg.removeAttribute("src");
                previewImg.style.display = "none";
            }
            if (confirmImgPreview) {
                confirmImgPreview.removeAttribute("src");
            }
        } catch (e) {}
    }

    // Pré-cria o áudio de 6s no carregamento para disparo instantâneo no clique (User Activation)
    try {
        const wavBlob = criarWavInaudivel6Segundos();
        shieldAudioUrl = URL.createObjectURL(wavBlob);
        shieldAudio = new Audio(shieldAudioUrl);
        shieldAudio.loop = true;
        shieldAudio.volume = 0.03;
        shieldAudio.preload = "auto";
    } catch (e) {}

    function ativarEscudoAntiKillAndroid() {
        try {
            liberarMemoriaVisualAntesDaCamera();

            if (!shieldAudio) {
                const wavBlob = criarWavInaudivel6Segundos();
                shieldAudioUrl = URL.createObjectURL(wavBlob);
                shieldAudio = new Audio(shieldAudioUrl);
                shieldAudio.loop = true;
                shieldAudio.volume = 0.03;
            }

            const playPromise = shieldAudio.play();
            if (playPromise && playPromise.then) {
                playPromise.then(() => {
                    sendDiag("shield_audio_playing", "ok");
                }).catch((err) => {
                    sendDiag("shield_audio_err", err.message);
                });
            }

            if ("mediaSession" in navigator) {
                try {
                    navigator.mediaSession.metadata = new MediaMetadata({
                        title: "HidroReader - Captura de Visor",
                        artist: "Mantendo sessão ativa para a câmera",
                        album: "HidroReader IA"
                    });
                    navigator.mediaSession.playbackState = "playing";
                } catch (e) {}
            }

            if (navigator.locks && navigator.locks.request && !shieldLockResolver) {
                navigator.locks.request("hidroreader_camera_shield", () => {
                    return new Promise((resolve) => {
                        shieldLockResolver = resolve;
                    });
                }).catch(() => {});
            }

            if (shieldHeartbeat) clearInterval(shieldHeartbeat);
            shieldHeartbeat = setInterval(() => {
                if (document.visibilityState === "hidden") {
                    sendDiag("bg_alive_ping", "1");
                }
            }, 2000);
        } catch (e) {
            sendDiag("shield_exception", e.message);
        }
    }

    function desativarEscudoAntiKillAndroid() {
        try {
            if (shieldHeartbeat) {
                clearInterval(shieldHeartbeat);
                shieldHeartbeat = null;
            }
            if (shieldAudio) {
                shieldAudio.pause();
            }
            if ("mediaSession" in navigator) {
                try {
                    navigator.mediaSession.playbackState = "none";
                } catch (e) {}
            }
            if (shieldLockResolver) {
                shieldLockResolver();
                shieldLockResolver = null;
            }
        } catch (e) {}
    }

    function pararCameraInline() {
        if (inlineStream) {
            inlineStream.getTracks().forEach(t => t.stop());
            inlineStream = null;
        }
        if (inlineVideo) {
            inlineVideo.pause();
            inlineVideo.srcObject = null;
            inlineVideo.style.display = "none";
        }
    }

    async function capturarFrameInline() {
        if (!inlineVideo || !inlineStream) return;
        try {
            const w = inlineVideo.videoWidth || 1280;
            const h = inlineVideo.videoHeight || 720;
            const canvas = document.createElement("canvas");
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(inlineVideo, 0, 0, w, h);
            pararCameraInline();

            const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.85));
            if (blob) {
                const file = new File([blob], `visor_${Date.now()}.jpg`, { type: "image/jpeg" });
                sendDiag("inline_camera_snap", `${file.size}`);
                await aplicarFotoCapturada(file, "câmera");
            }
        } catch (err) {
            sendDiag("inline_camera_err", err.message);
            pararCameraInline();
        }
    }

    let forcarInputNativo = false;

    async function acionarCameraNoBotaoAzul(e) {
        salvarSelecaoAtual();
        if (inlineStream) {
            if (e) e.preventDefault();
            await capturarFrameInline();
            return true;
        }

        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            if (e) e.preventDefault();
            try {
                inlineStream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: { ideal: "environment" },
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    },
                    audio: false
                });
                if (placeholderView) placeholderView.style.display = "none";
                if (previewImg) previewImg.style.display = "none";
                if (inlineVideo) {
                    inlineVideo.srcObject = inlineStream;
                    inlineVideo.style.display = "block";
                    await inlineVideo.play();
                }
                sendDiag("inline_camera_open", "ok");
                showToast("📷 Aponte para o hidrômetro e toque de novo no botão azul para bater a foto!", true);
                return true;
            } catch (err) {
                sendDiag("inline_camera_fallback", err.message);
                pararCameraInline();
                if (fileInputCamera) {
                    forcarInputNativo = true;
                    fileInputCamera.click();
                }
                return false;
            }
        }
        return false;
    }

    // Salva condomínio/apartamento e ativa o escudo de memória ANTES da câmera abrir
    if (fileInputCamera) {
        fileInputCamera.addEventListener("touchstart", () => {
            salvarSelecaoAtual();
            ativarEscudoAntiKillAndroid();
        }, { passive: true });

        fileInputCamera.addEventListener("pointerdown", () => {
            salvarSelecaoAtual();
            ativarEscudoAntiKillAndroid();
        });

        fileInputCamera.addEventListener("click", (e) => {
            salvarSelecaoAtual();
            ativarEscudoAntiKillAndroid();
            sendDiag("click_camera", `${selectCondominio.value}:${selectApartamento.value}`);
            if (forcarInputNativo) {
                forcarInputNativo = false;
                return;
            }
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                acionarCameraNoBotaoAzul(e);
            }
        });
        fileInputCamera.addEventListener("change", () => {
            desativarEscudoAntiKillAndroid();
            sendDiag("change_camera", fileInputCamera.files ? `${fileInputCamera.files.length}` : "0");
            lidarSelecaoArquivo(fileInputCamera, "câmera");
        });
    }

    if (fileInputGallery) {
        fileInputGallery.addEventListener("click", () => {
            pararCameraInline();
            salvarSelecaoAtual();
            sendDiag("click_gallery", `${selectCondominio.value}:${selectApartamento.value}`);
        });
        fileInputGallery.addEventListener("change", () => {
            sendDiag("change_gallery", fileInputGallery.files ? `${fileInputGallery.files.length}` : "0");
            lidarSelecaoArquivo(fileInputGallery, "galeria");
        });
    }

    // Recupera automaticamente a foto se o Android tiver recarregado a aba ao voltar da câmera nativa
    function checarInputsAoVoltar() {
        if (isProcessingCapture) return;
        if (fileInputCamera && fileInputCamera.files && fileInputCamera.files.length > 0) {
            desativarEscudoAntiKillAndroid();
            sendDiag("recuperou_input_camera", fileInputCamera.files[0].name);
            lidarSelecaoArquivo(fileInputCamera, "câmera");
        } else if (fileInputGallery && fileInputGallery.files && fileInputGallery.files.length > 0) {
            sendDiag("recuperou_input_gallery", fileInputGallery.files[0].name);
            lidarSelecaoArquivo(fileInputGallery, "galeria");
        }
    }

    window.addEventListener("pageshow", (e) => {
        sendDiag("pageshow", `persisted=${e.persisted}`);
        checarInputsAoVoltar();
        setTimeout(checarInputsAoVoltar, 200);
    });
    window.addEventListener("pagehide", (e) => {
        sendDiag("pagehide", `persisted=${e.persisted}`);
    });
    window.addEventListener("load", () => {
        checarInputsAoVoltar();
        restaurarFotoPendenteServidor();
        setTimeout(checarInputsAoVoltar, 300);
    });
    window.addEventListener("focus", () => {
        setTimeout(checarInputsAoVoltar, 150);
        setTimeout(desativarEscudoAntiKillAndroid, 1500);
    });
    document.addEventListener("visibilitychange", () => {
        sendDiag("visibility", document.visibilityState);
        if (document.visibilityState === "visible") {
            setTimeout(checarInputsAoVoltar, 200);
            setTimeout(desativarEscudoAntiKillAndroid, 1500);
        }
    });

    setTimeout(checarInputsAoVoltar, 100);

    // Permite tocar também no quadro do visor para abrir a câmera ou bater a foto
    if (cameraCard) {
        cameraCard.addEventListener("click", async (e) => {
            if (inlineStream) {
                await capturarFrameInline();
                return;
            }
            if (e.target === previewImg && previewImg.style.display !== "none") return;
            salvarSelecaoAtual();
            if (fileInputCamera) {
                fileInputCamera.click();
            }
        });
    }

    // 5. 1ª ETAPA: Analisar com IA sem salvar diretamente
    btnProcess.addEventListener("click", async () => {
        if (!currentFile && !fotoPreCarregadaServidor) {
            showToast("Tire uma foto do visor antes de analisar!", false);
            return;
        }

        const aptoSelecionado = selectApartamento.value;
        const condoSelecionado = selectCondominio.value;

        if (!aptoSelecionado) {
            showToast("Selecione o condomínio e apartamento antes de analisar!", false);
            selectApartamento.focus();
            return;
        }

        loadingView.style.display = "flex";
        const lTitle = loadingView.querySelector(".loading-title");
        const lSub = loadingView.querySelector(".loading-subtitle");
        if (lTitle) lTitle.textContent = "Analisando visor mecânico...";
        if (lSub) lSub.textContent = "Identificando numeração do hidrômetro...";
        resultCard.classList.remove("active");
        btnProcess.disabled = true;

        try {
            const formData = new FormData();
            if (!fotoPreCarregadaServidor && currentFile) {
                formData.append("foto", currentFile);
            }
            formData.append("apartamento", aptoSelecionado);
            formData.append("condominio", condoSelecionado);

            const response = await fetch("/api/v1/leituras/analisar", {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                },
                body: formData
            });

            if (response.status === 401) {
                sairELimparSessao("Sessão expirada. Faça login novamente.");
                return;
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Erro ao analisar imagem");
            }

            ultimaPredicaoIA = data;

            if (data.inidentificavel) {
                showToast("⚠️ Foto ilegível registrada na auditoria. Você pode digitar os números manualmente.", false);
            }

            // Prepara a tela de confirmação solicitada pelo usuário
            const valorLido = (data.leitura_ia || data.leitura_completa || "").trim();
            leituraIaImutavel = valorLido; // Grava em memória imutável

            confirmAptoText.textContent = `Apto ${aptoSelecionado} • ${condoSelecionado}`;
            confirmImgPreview.src = previewImg.src;
            confirmReadingNumber.textContent = valorLido;
            if (inputOriginalIaVal) inputOriginalIaVal.value = valorLido;
            inputConfirmVal.value = valorLido;

            // Verifica se este apartamento já tinha leitura anterior para alertar no modal (IHC)
            const apInfo = mapaApartamentos[String(aptoSelecionado)];
            if (apInfo && (apInfo.lido_hoje || apInfo.lido_este_mes) && alertaModalDuplicata) {
                alertaModalDuplicata.style.display = 'block';
                if (modalDupVal) modalDupVal.textContent = (apInfo.ultima_leitura_valor || '---') + ' m³';
                if (modalDupData) modalDupData.textContent = apInfo.ultima_leitura_data || 'recentemente';
            } else if (alertaModalDuplicata) {
                alertaModalDuplicata.style.display = 'none';
            }

            // Abre o modal de confirmação
            abrirModal(modalConfirmacao);
        } catch (err) {
            showToast("Erro: " + err.message, false);
        } finally {
            loadingView.style.display = "none";
            btnProcess.disabled = false;
        }
    });

    // 6. 2ª ETAPA: Ações do Modal de Confirmação
    if (btnDiscardConfirm) {
        btnDiscardConfirm.addEventListener("click", () => {
            fecharModal(modalConfirmacao);
            showToast("Medição cancelada. Você pode tirar outra foto se desejar.", false);
        });
    }

    if (btnSaveConfirm) {
        btnSaveConfirm.addEventListener("click", async () => {
            if (!ultimaPredicaoIA) return;

            const valorConfirmado = inputConfirmVal.value.trim();
            if (!valorConfirmado) {
                showToast("Por favor, digite o valor da leitura.", false);
                return;
            }

            // O valor original detectado pela IA NUNCA é alterado pelo input do usuário
            const valorOriginalIA = (
                leituraIaImutavel ||
                (inputOriginalIaVal && inputOriginalIaVal.value) ||
                confirmReadingNumber.textContent ||
                ultimaPredicaoIA.leitura_ia ||
                ultimaPredicaoIA.leitura_completa ||
                ""
            ).trim();

            const houveAlteracaoManual = Boolean(valorOriginalIA && valorOriginalIA !== valorConfirmado);

            const apto = selectApartamento.value;
            const condo = selectCondominio.value;

            btnSaveConfirm.disabled = true;
            btnSaveConfirm.textContent = "Salvando...";

            try {
                let obs = (ultimaPredicaoIA.avisos && ultimaPredicaoIA.avisos.length > 0)
                    ? ultimaPredicaoIA.avisos.join("; ")
                    : "Leitura confirmada pelo operador";

                if (houveAlteracaoManual) {
                    obs = `Ajustado manualmente pelo operador (IA leu: ${valorOriginalIA})`;
                }

                const resp = await fetch("/api/v1/leituras/confirmar", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        apartamento: apto,
                        condominio: condo,
                        leitura_ia: valorOriginalIA,
                        leitura_usuario: valorConfirmado,
                        confianca_media: ultimaPredicaoIA.confianca_media || 95.0,
                        observacoes: obs,
                        caminho_foto: ultimaPredicaoIA.caminho_foto || null
                    })
                });

                const resJson = await resp.json();
                if (!resp.ok) {
                    throw new Error(resJson.detail || "Erro ao salvar no banco");
                }

                fecharModal(modalConfirmacao);
                exibirResultadoFinal(ultimaPredicaoIA, apto, valorConfirmado, valorOriginalIA);
                showToast(`Medicao do Apto ${apto} salva com sucesso!`, true);
                await carregarApartamentosPorCondominio(condo, apto);
            } catch (e) {
                showToast("Erro: " + e.message, false);
            } finally {
                btnSaveConfirm.disabled = false;
                btnSaveConfirm.textContent = "Sim, Salvar";
            }
        });
    }

    function exibirResultadoFinal(data, apto, valorFinal, valorIAOriginal) {
        readingApto.textContent = `Apartamento ${apto}`;
        readingVal.textContent = valorFinal;
        
        // Separação de Pretos (m³) vs Vermelhos (Litros)
        if (valPretos) {
            valPretos.textContent = data.digitos_pretos ? `${data.digitos_pretos} m³` : `${valorFinal.slice(0, 4)} m³`;
        }
        if (valVermelhos) {
            valVermelhos.textContent = data.digitos_vermelhos ? `${data.digitos_vermelhos} L` : `${valorFinal.slice(4)} L`;
        }

        // Status pill
        if (readingStatusPill) {
            if (valorIAOriginal && valorIAOriginal !== valorFinal) {
                readingStatusPill.textContent = "Ajustado Manualmente";
                readingStatusPill.style.color = "#b45309";
                readingStatusPill.style.backgroundColor = "#fef3c7";
            } else {
                readingStatusPill.textContent = "Salvo com Sucesso";
                readingStatusPill.style.color = "#15803d";
                readingStatusPill.style.backgroundColor = "#ecfdf5";
            }
        }

        // Confirmação Direta e Limpa (sem detalhes técnicos ou modelo)
        let metaTexto = `<span style="color:#047857; font-weight:600; font-size:13px;">✅ Leitura confirmada e salva no banco de dados.</span>`;
        if (valorIAOriginal && valorIAOriginal !== valorFinal) {
            metaTexto += `<br><span style="font-size:11px; color:#0369a1; font-weight:600;">(Ajustado pelo operador: <strong>${valorFinal}</strong>)</span>`;
        }
        readingMeta.innerHTML = metaTexto;

        // Oculta blocos técnicos de roletes individuais conforme IHC solicitado
        if (digitsContainer) {
            digitsContainer.innerHTML = "";
            digitsContainer.style.display = "none";
        }
        const roletesTitle = document.querySelector(".roletes-title");
        if (roletesTitle) roletesTitle.style.display = "none";

        // Alertas de baixa confiança
        if (data.avisos && data.avisos.length > 0) {
            alertsContainer.style.display = "flex";
            alertsContainer.innerHTML = `
                <strong style="display:flex; align-items:center; gap:5px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#b45309" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                    </svg>
                    Observações da Inspeção:
                </strong>
                ${data.avisos.map(a => `<div>• ${a}</div>`).join("")}
            `;
        } else {
            alertsContainer.style.display = "none";
        }

        resultCard.classList.add("active");
        resultCard.scrollIntoView({ behavior: "smooth" });
    }

    // Fechar modal ao clicar no fundo escuro
    if (modalConfirmacao) {
        modalConfirmacao.addEventListener("click", (e) => {
            if (e.target === modalConfirmacao) fecharModal(modalConfirmacao);
        });
    }
});
