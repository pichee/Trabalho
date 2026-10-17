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
    const fileInputCamera = document.getElementById("file-input-camera");
    const fileInputGallery = document.getElementById("file-input-gallery");
    const btnProcess = document.getElementById("btn-process");
    const previewImg = document.getElementById("preview-img");
    const placeholderView = document.getElementById("placeholder-view");
    const loadingView = document.getElementById("loading-view");

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
    const inputConfirmVal = document.getElementById("input-confirm-val");
    const btnDiscardConfirm = document.getElementById("btn-discard-confirm");
    const btnSaveConfirm = document.getElementById("btn-save-confirm");

    let currentFile = null;
    let ultimaPredicaoIA = null;

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

            // Verifica se veio via URL (?apto=101&condo=...)
            const urlParams = new URLSearchParams(window.location.search);
            const aptoUrl = urlParams.get("apto");
            const condoUrl = urlParams.get("condo");

            if (condoUrl && condominios.includes(condoUrl)) {
                selectCondominio.value = condoUrl;
            }

            const condoAtivo = selectCondominio.value || condominios[0];
            await carregarApartamentosPorCondominio(condoAtivo, aptoUrl);
        } catch (e) {
            selectCondominio.innerHTML = '<option value="">Erro ao carregar condomínios</option>';
        }
    }

    async function carregarApartamentosPorCondominio(condoNome, aptoPreSelecionado = null) {
        selectApartamento.innerHTML = '<option value="">Carregando apartamentos...</option>';
        try {
            const resp = await fetch(`/api/v1/apartamentos?condominio=${encodeURIComponent(condoNome)}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const aptos = await resp.json();

            selectApartamento.innerHTML = '<option value="">-- Selecione o Apartamento --</option>';
            aptos.forEach(ap => {
                const opt = document.createElement("option");
                opt.value = ap.numero;
                opt.textContent = `Apto ${ap.numero} (${ap.bloco || "Bloco A"})`;
                selectApartamento.appendChild(opt);
            });

            // Se um apartamento foi passado na URL ou parâmetro, tenta selecioná-lo
            if (aptoPreSelecionado) {
                const existe = aptos.some(a => a.numero === aptoPreSelecionado);
                if (existe) {
                    selectApartamento.value = aptoPreSelecionado;
                }
            }
        } catch (e) {
            selectApartamento.innerHTML = '<option value="">Erro ao listar apartamentos</option>';
        }
    }

    if (selectCondominio) {
        selectCondominio.addEventListener("change", async () => {
            await carregarApartamentosPorCondominio(selectCondominio.value);
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

    // 4. Captura com Suporte Multi-Câmera e Galeria (Mobile-First 100% Nativo)
    // Helper: Redimensionar foto grande de smartphone (15MB -> ~350KB) mantendo nitidez máxima
    async function otimizarFotoSmartphone(file) {
        if (!file || file.size < 1.5 * 1024 * 1024) {
            return file;
        }

        return new Promise((resolve) => {
            const img = new Image();
            const tempUrl = URL.createObjectURL(file);

            img.onload = () => {
                URL.revokeObjectURL(tempUrl);
                let { width, height } = img;
                const maxDim = 1600;

                if (width <= maxDim && height <= maxDim) {
                    resolve(file);
                    return;
                }

                if (width > height) {
                    height = Math.round((height * maxDim) / width);
                    width = maxDim;
                } else {
                    width = Math.round((width * maxDim) / height);
                    height = maxDim;
                }

                const canvas = document.createElement("canvas");
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0, width, height);

                canvas.toBlob(
                    (blob) => {
                        if (blob) {
                            const optFile = new File([blob], file.name || "hidrometro.jpg", {
                                type: "image/jpeg",
                                lastModified: Date.now()
                            });
                            resolve(optFile);
                        } else {
                            resolve(file);
                        }
                    },
                    "image/jpeg",
                    0.88
                );
            };

            img.onerror = () => {
                URL.revokeObjectURL(tempUrl);
                resolve(file);
            };

            img.src = tempUrl;
        });
    }

    async function aplicarFotoCapturada(file, origem = "câmera") {
        if (!file) {
            showToast("Nenhum arquivo de imagem recebido.", false);
            return;
        }

        if (file.size === 0) {
            showToast("O app de câmera retornou arquivo vazio. Tente pela opção 'Escolher da Galeria'.", false);
            return;
        }

        currentFile = file;
        const tamanhoKB = Math.round(file.size / 1024);
        showToast(`Foto recebida (${tamanhoKB} KB). Carregando...`, true);

        try {
            // Preview instantâneo via ObjectURL
            const objectUrl = URL.createObjectURL(file);
            previewImg.onload = () => {
                previewImg.style.display = "block";
                if (placeholderView) placeholderView.style.display = "none";
                btnProcess.disabled = false;
                resultCard.classList.remove("active");
                showToast("Foto pronta para análise com IA!", true);
            };

            previewImg.onerror = () => {
                const reader = new FileReader();
                reader.onload = (event) => {
                    previewImg.src = event.target.result;
                    previewImg.style.display = "block";
                    if (placeholderView) placeholderView.style.display = "none";
                    btnProcess.disabled = false;
                    resultCard.classList.remove("active");
                    showToast("Foto pronta para análise!", true);
                };
                reader.readAsDataURL(file);
            };

            previewImg.src = objectUrl;
        } catch (err) {
            console.error("Erro no ObjectURL, usando fallback:", err);
            const reader = new FileReader();
            reader.onload = (event) => {
                previewImg.src = event.target.result;
                previewImg.style.display = "block";
                if (placeholderView) placeholderView.style.display = "none";
                btnProcess.disabled = false;
                resultCard.classList.remove("active");
                showToast("Foto pronta para análise!", true);
            };
            reader.readAsDataURL(file);
        }
    }

    if (fileInputCamera) {
        fileInputCamera.addEventListener("change", async (e) => {
            const files = e.target.files;
            if (files && files.length > 0) {
                await aplicarFotoCapturada(files[0], "câmera");
            }
        });
    }

    if (fileInputGallery) {
        fileInputGallery.addEventListener("change", async (e) => {
            const files = e.target.files;
            if (files && files.length > 0) {
                await aplicarFotoCapturada(files[0], "galeria");
            }
        });
    }

    // 5. 1ª ETAPA: Analisar com IA sem salvar diretamente
    btnProcess.addEventListener("click", async () => {
        if (!currentFile) {
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
        resultCard.classList.remove("active");
        btnProcess.disabled = true;

        try {
            // Otimiza caso a foto venha de câmera de 48MP/108MP de smartphone
            const fotoPronta = await otimizarFotoSmartphone(currentFile);

            const formData = new FormData();
            formData.append("foto", fotoPronta);
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

            // Prepara a tela de confirmação solicitada pelo usuário
            const valorLido = data.leitura_completa || data.leitura_yolo || "------";
            confirmAptoText.textContent = `Apto ${aptoSelecionado} • ${condoSelecionado}`;
            confirmImgPreview.src = previewImg.src;
            confirmReadingNumber.textContent = valorLido;
            inputConfirmVal.value = valorLido;

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

            const apto = selectApartamento.value;
            const condo = selectCondominio.value;

            btnSaveConfirm.disabled = true;
            btnSaveConfirm.textContent = "Salvando...";

            try {
                const resp = await fetch("/api/v1/leituras/confirmar", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        apartamento: apto,
                        condominio: condo,
                        leitura: valorConfirmado,
                        confianca_media: ultimaPredicaoIA.confianca_media || 95.0,
                        observacoes: (ultimaPredicaoIA.avisos && ultimaPredicaoIA.avisos.length > 0)
                            ? ultimaPredicaoIA.avisos.join("; ")
                            : "Leitura confirmada pelo operador",
                        caminho_foto: ultimaPredicaoIA.caminho_foto || null
                    })
                });

                const resJson = await resp.json();
                if (!resp.ok) {
                    throw new Error(resJson.detail || "Erro ao salvar no banco");
                }

                fecharModal(modalConfirmacao);
                exibirResultadoFinal(ultimaPredicaoIA, apto, valorConfirmado);
                showToast(`Medição do Apto ${apto} salva com sucesso!`, true);
            } catch (e) {
                showToast("Erro: " + e.message, false);
            } finally {
                btnSaveConfirm.disabled = false;
                btnSaveConfirm.textContent = "Sim, Salvar";
            }
        });
    }

    function exibirResultadoFinal(data, apto, valorFinal) {
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
            const statusTexto = data.qualidade_visor || "Verificado";
            readingStatusPill.textContent = "Salvo com Sucesso";
            readingStatusPill.style.color = "#15803d";
            readingStatusPill.style.backgroundColor = "#ecfdf5";
        }

        // Metadados
        let metaTexto = `Modelo: ${data.modelo_utilizado || "IA Vision"}`;
        if (data.confianca_media) {
            metaTexto += ` • Confiança: ${data.confianca_media}%`;
        }
        metaTexto += `<br><span style="font-size:11px; color:#555;">Salvo e confirmado no banco de dados.</span>`;
        readingMeta.innerHTML = metaTexto;

        // Renderização dos Roletes Individuais
        digitsContainer.innerHTML = "";
        const qtdPretos = data.digitos_pretos ? data.digitos_pretos.length : 4;

        if (data.digitos && data.digitos.length > 0) {
            data.digitos.forEach((d, idx) => {
                const box = document.createElement("div");
                const isVermelho = idx >= qtdPretos;
                box.className = `digit-rolete ${isVermelho ? "rolete-vermelho" : "rolete-preto"}`;
                
                box.innerHTML = `
                    <div class="rolete-pos">#${d.posicao}</div>
                    <div class="rolete-char">${valorFinal[idx] || d.valor_yolo}</div>
                    <div class="rolete-conf">${d.confianca_yolo ? d.confianca_yolo + '%' : 'IA'}</div>
                `;
                digitsContainer.appendChild(box);
            });
        }

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
