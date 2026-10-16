document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("hidroreader_token");
    if (!token) {
        window.location.href = "/login";
        return;
    }

    // Elementos da Interface
    const greetingName = document.getElementById("greeting-name");
    const greetingRole = document.getElementById("greeting-role");
    const volumeVal = document.getElementById("volume-val");
    const volumeHidden = document.getElementById("volume-hidden");
    const displaySub = document.getElementById("display-sub");
    const btnToggleEye = document.getElementById("btn-toggle-eye");
    const btnLogout = document.getElementById("btn-logout");
    const btnHelp = document.getElementById("btn-help");
    const recentList = document.getElementById("recent-list");
    const toast = document.getElementById("toast");

    // Botões de Ação
    const actNovaLeitura = document.getElementById("act-nova-leitura");
    const actApartamentos = document.getElementById("act-apartamentos");
    const actHistorico = document.getElementById("act-historico");
    const actExportar = document.getElementById("act-exportar");
    const actGuiaIA = document.getElementById("act-guia-ia");
    const shortcutStart = document.getElementById("shortcut-start-inspection");
    const linkVerTodas = document.getElementById("link-ver-todas");

    // Modais
    const modalHistorico = document.getElementById("modal-historico");
    const closeModalHistorico = document.getElementById("close-modal-historico");
    const modalHistoricoBody = document.getElementById("modal-historico-body");

    const modalApartamentos = document.getElementById("modal-apartamentos");
    const closeModalApartamentos = document.getElementById("close-modal-apartamentos");
    const modalAptosBody = document.getElementById("modal-aptos-body");
    const btnNovoAptoModal = document.getElementById("btn-novo-apto-modal");

    let isEyeHidden = false;

    function showToast(msg, isSuccess = true) {
        if (!toast) return;
        toast.textContent = msg;
        toast.style.background = isSuccess ? "#0a0a0a" : "#dc2626";
        toast.classList.add("show");
        setTimeout(() => {
            toast.classList.remove("show");
        }, 3200);
    }

    function encerrarSessao() {
        localStorage.removeItem("hidroreader_token");
        localStorage.removeItem("hidroreader_user");
        localStorage.removeItem("hidroreader_name");
        window.location.href = "/login";
    }

    if (btnLogout) {
        btnLogout.addEventListener("click", () => {
            encerrarSessao();
        });
    }

    // Toggle ocultar/mostrar valores (se existir)
    if (btnToggleEye) {
        btnToggleEye.addEventListener("click", () => {
            isEyeHidden = !isEyeHidden;
            if (isEyeHidden) {
                if (volumeVal) volumeVal.style.display = "none";
                if (volumeHidden) volumeHidden.style.display = "inline-block";
            } else {
                if (volumeVal) volumeVal.style.display = "inline-block";
                if (volumeHidden) volumeHidden.style.display = "none";
            }
        });
    }

    // 1. Carregar Dados do Dashboard
    async function carregarDashboard() {
        try {
            const resp = await fetch("/api/v1/dashboard/resumo", {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (resp.status === 401) {
                encerrarSessao();
                return;
            }

            const data = await resp.json();

            // Atualiza Saudação
            if (greetingName) greetingName.textContent = `Olá, ${data.operador_nome || "Operador"}`;
            if (greetingRole) greetingRole.textContent = `${data.operador_cargo || "Operador"} • Condomínio`;

            // Atualiza Métrica Principal
            if (volumeVal) volumeVal.textContent = `${data.volume_acumulado_m3} m³`;
            if (displaySub) displaySub.textContent = `${data.total_apartamentos} apartamentos cadastrados • ${data.total_leituras} leituras salvas`;

            // Atualiza Lista Recente
            renderizarRecentes(data.ultimas_leituras);
        } catch (err) {
            console.error("Erro ao carregar dashboard:", err);
            if (displaySub) displaySub.textContent = "Erro ao conectar com o servidor.";
        }
    }

    function renderizarRecentes(leituras) {
        if (!recentList) return;
        if (!leituras || leituras.length === 0) {
            recentList.innerHTML = `
                <div class="empty-recent">
                    <p>Nenhuma leitura salva ainda.</p>
                    <button type="button" class="btn-sm-action" onclick="window.location.href='/leitor'">Fazer Primeira Leitura</button>
                </div>
            `;
            return;
        }

        recentList.innerHTML = "";
        leituras.slice(0, 4).forEach(l => {
            const item = document.createElement("div");
            item.className = "recent-item";
            item.innerHTML = `
                <div class="recent-left">
                    <div class="recent-apto-pill">Apto ${l.apartamento}</div>
                    <div class="recent-info">
                        <span class="recent-leitura">${l.leitura} m³</span>
                        <span class="recent-meta">${l.operador} • ${l.data}</span>
                    </div>
                </div>
                <div class="recent-badge">${l.confianca} IA</div>
            `;
            recentList.appendChild(item);
        });
    }

    // 2. Ações dos Botões
    if (actNovaLeitura) {
        actNovaLeitura.addEventListener("click", () => {
            window.location.href = "/leitor";
        });
    }

    if (shortcutStart) {
        shortcutStart.addEventListener("click", () => {
            window.location.href = "/leitor";
        });
    }

    // 3. Exportar Planilha CSV
    actExportar.addEventListener("click", async () => {
        showToast("Preparando planilha de condomínio...", true);
        try {
            const resp = await fetch("/api/v1/dashboard/exportar-csv", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!resp.ok) throw new Error("Erro ao baixar");

            const blob = await resp.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `relatorio_leituras_${new Date().toISOString().slice(0, 10)}.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            showToast("Planilha CSV baixada com sucesso!", true);
        } catch (e) {
            showToast("Erro ao exportar planilha.", false);
        }
    });

    // Helpers para abrir/fechar modais garantindo isolamento total
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

    // 4. Modal de Histórico
    actHistorico.addEventListener("click", abrirModalHistorico);
    if (linkVerTodas) linkVerTodas.addEventListener("click", abrirModalHistorico);

    async function abrirModalHistorico() {
        abrirModal(modalHistorico);
        modalHistoricoBody.innerHTML = "Carregando histórico completo...";

        try {
            const resp = await fetch("/api/v1/dashboard/resumo", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await resp.json();

            if (!data.ultimas_leituras || data.ultimas_leituras.length === 0) {
                modalHistoricoBody.innerHTML = "<p>Nenhuma medição registrada até o momento.</p>";
                return;
            }

            modalHistoricoBody.innerHTML = "";
            data.ultimas_leituras.forEach(l => {
                const row = document.createElement("div");
                row.className = "history-row";
                row.innerHTML = `
                    <div class="history-main">
                        <strong>Apartamento ${l.apartamento}</strong>
                        <span class="history-val">${l.leitura} m³</span>
                    </div>
                    <div class="history-sub">
                        <span>${l.data}</span>
                        <span>Operador: ${l.operador}</span>
                    </div>
                `;
                modalHistoricoBody.appendChild(row);
            });
        } catch (e) {
            modalHistoricoBody.innerHTML = "<p>Erro ao carregar histórico.</p>";
        }
    }

    closeModalHistorico.addEventListener("click", () => {
        fecharModal(modalHistorico);
    });

    // 5. Modal de Apartamentos com Filtro por Condomínio e Histórico Específico
    const modalAptosTitle = document.getElementById("modal-aptos-title");
    const modalAptosViewList = document.getElementById("modal-aptos-view-list");
    const modalAptoViewDetail = document.getElementById("modal-apto-view-detail");
    const selectCondoFilter = document.getElementById("select-condominio-filter");
    const inputBuscaApto = document.getElementById("input-busca-apto");
    const modalAptosGrid = document.getElementById("modal-aptos-grid");
    const btnBackToAptos = document.getElementById("btn-back-to-aptos");
    const detailAptoBadge = document.getElementById("detail-apto-badge");
    const detailAptoTitle = document.getElementById("detail-apto-title");
    const detailAptoSub = document.getElementById("detail-apto-sub");
    const detailLastReading = document.getElementById("detail-last-reading");
    const detailTotalReadings = document.getElementById("detail-total-readings");
    const detailAptoHistoryList = document.getElementById("detail-apto-history-list");
    const btnMeasureThisApto = document.getElementById("btn-measure-this-apto");
    const modalAptosFooter = document.getElementById("modal-aptos-footer");

    let condominiosCadastrados = [];
    let todosApartamentosDoCondo = [];
    let aptoSelecionadoAtual = null;

    actApartamentos.addEventListener("click", abrirModalApartamentos);

    async function abrirModalApartamentos() {
        abrirModal(modalApartamentos);
        mostrarVisaoLista();

        try {
            const respCondos = await fetch("/api/v1/apartamentos/condominios", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            condominiosCadastrados = await respCondos.json();

            selectCondoFilter.innerHTML = "";
            condominiosCadastrados.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c;
                opt.textContent = `🏢 ${c}`;
                selectCondoFilter.appendChild(opt);
            });

            const condoAtivo = selectCondoFilter.value || condominiosCadastrados[0] || "Residencial das Palmeiras";
            await carregarApartamentosPorCondominio(condoAtivo);
        } catch (e) {
            modalAptosGrid.innerHTML = "<p>Erro ao carregar dados dos condomínios.</p>";
        }
    }

    if (selectCondoFilter) {
        selectCondoFilter.addEventListener("change", async () => {
            await carregarApartamentosPorCondominio(selectCondoFilter.value);
        });
    }

    if (inputBuscaApto) {
        inputBuscaApto.addEventListener("input", () => {
            const termo = inputBuscaApto.value.trim().toLowerCase();
            const filtrados = todosApartamentosDoCondo.filter(a => a.numero.toLowerCase().includes(termo));
            renderizarGridApartamentos(filtrados);
        });
    }

    async function carregarApartamentosPorCondominio(condoNome) {
        modalAptosGrid.innerHTML = "Carregando apartamentos...";
        try {
            const url = `/api/v1/apartamentos?condominio=${encodeURIComponent(condoNome)}`;
            const resp = await fetch(url, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            todosApartamentosDoCondo = await resp.json();
            renderizarGridApartamentos(todosApartamentosDoCondo);
        } catch (e) {
            modalAptosGrid.innerHTML = "<p>Erro ao listar apartamentos.</p>";
        }
    }

    function renderizarGridApartamentos(aptos) {
        if (!aptos || aptos.length === 0) {
            modalAptosGrid.innerHTML = "<p style='grid-column: 1/-1; text-align: center; color: #888; padding: 20px 0;'>Nenhum apartamento encontrado neste condomínio.</p>";
            return;
        }

        modalAptosGrid.innerHTML = "";
        aptos.forEach(a => {
            const chip = document.createElement("div");
            chip.className = "apto-chip";
            chip.innerHTML = `
                <span>${a.numero}</span>
                <span class="apto-chip-sub">${a.bloco || "Bloco A"}</span>
            `;
            chip.title = `Clique para ver histórico do Apto ${a.numero}`;
            chip.addEventListener("click", () => {
                abrirDetalheApartamento(a);
            });
            modalAptosGrid.appendChild(chip);
        });
    }

    // VISÃO 2: Abrir Detalhe e Histórico de Leituras do Apartamento
    async function abrirDetalheApartamento(apto) {
        aptoSelecionadoAtual = apto;
        mostrarVisaoDetalhe();

        detailAptoBadge.textContent = `Apto ${apto.numero}`;
        detailAptoTitle.textContent = `Apartamento ${apto.numero}`;
        detailAptoSub.textContent = `${apto.bloco || "Bloco A"} • ${apto.condominio || "Condomínio"}`;
        detailLastReading.textContent = "...";
        detailTotalReadings.textContent = "...";
        detailAptoHistoryList.innerHTML = "<p style='color: #888; text-align: center;'>Buscando histórico...</p>";

        try {
            const resp = await fetch(`/api/v1/apartamentos/${apto.numero}/historico`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await resp.json();

            detailLastReading.textContent = data.ultima_leitura ? `${data.ultima_leitura} m³` : "Sem leitura";
            detailTotalReadings.textContent = `${data.total_leituras}`;

            if (!data.leituras || data.leituras.length === 0) {
                detailAptoHistoryList.innerHTML = `
                    <div class="empty-recent" style="padding: 18px 12px;">
                        <p>Nenhuma leitura registrada para o apartamento ${apto.numero}.</p>
                    </div>
                `;
                return;
            }

            detailAptoHistoryList.innerHTML = "";
            data.leituras.forEach(l => {
                const card = document.createElement("div");
                card.className = "apto-reading-card";
                card.innerHTML = `
                    <div class="reading-card-left">
                        <span class="reading-val-text">${l.leitura} m³</span>
                        <span class="reading-date-text">Por ${l.operador} • ${l.data}</span>
                        ${l.observacoes ? `<span style="font-size: 11px; color: #666;">${l.observacoes}</span>` : ""}
                    </div>
                    <span class="recent-badge">${l.confianca}</span>
                `;
                detailAptoHistoryList.appendChild(card);
            });
        } catch (e) {
            detailAptoHistoryList.innerHTML = "<p style='color: #dc2626;'>Erro ao carregar histórico deste apartamento.</p>";
        }
    }

    if (btnBackToAptos) {
        btnBackToAptos.addEventListener("click", () => {
            mostrarVisaoLista();
        });
    }

    if (btnMeasureThisApto) {
        btnMeasureThisApto.addEventListener("click", () => {
            if (!aptoSelecionadoAtual) return;
            fecharModal(modalApartamentos);
            window.location.href = `/leitor?apto=${encodeURIComponent(aptoSelecionadoAtual.numero)}`;
        });
    }

    function mostrarVisaoLista() {
        if (modalAptosTitle) modalAptosTitle.textContent = "Apartamentos";
        if (modalAptosViewList) modalAptosViewList.style.display = "block";
        if (modalAptoViewDetail) modalAptoViewDetail.style.display = "none";
        if (modalAptosFooter) modalAptosFooter.style.display = "block";
    }

    function mostrarVisaoDetalhe() {
        if (modalAptosTitle) modalAptosTitle.textContent = "Histórico do Apartamento";
        if (modalAptosViewList) modalAptosViewList.style.display = "none";
        if (modalAptoViewDetail) modalAptoViewDetail.style.display = "block";
        if (modalAptosFooter) modalAptosFooter.style.display = "none";
    }

    closeModalApartamentos.addEventListener("click", () => {
        fecharModal(modalApartamentos);
    });

    btnNovoAptoModal.addEventListener("click", async () => {
        const condoAtual = selectCondoFilter ? selectCondoFilter.value : "Residencial das Palmeiras";
        const num = prompt(`Número do novo apartamento para ${condoAtual} (ex: 501):`);
        if (!num || !num.trim()) return;

        const bloco = prompt("Bloco (ex: Bloco A, Bloco B):", "Bloco A") || "Bloco A";

        try {
            const resp = await fetch("/api/v1/apartamentos", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    numero: num.trim(),
                    bloco: bloco.trim(),
                    condominio: condoAtual
                })
            });
            const resData = await resp.json();
            if (resp.ok) {
                showToast(`Apto ${num.trim()} cadastrado em ${condoAtual}!`, true);
                await carregarApartamentosPorCondominio(condoAtual);
                carregarDashboard();
            } else {
                showToast(resData.detail || "Erro ao cadastrar apartamento.", false);
            }
        } catch (e) {
            showToast("Erro: " + e.message, false);
        }
    });

    // 6. Guia e Ajuda da IA
    if (actGuiaIA) {
        actGuiaIA.addEventListener("click", () => {
            alert("💡 Dicas para leitura perfeita com IA:\n\n1. Aproxime a câmera a 15-20cm do hidrômetro.\n2. Certifique-se de que o mostrador de roletes está bem iluminado.\n3. O YOLO recorta o visor e o Gemini Vision lê os números pretos e vermelhos automaticamente.");
        });
    }

    if (btnHelp) {
        btnHelp.addEventListener("click", () => {
            alert("💧 HidroReader Mobile v1.0.0\n\nSistema para condomínios e inspeção predial.\nPara dúvidas ou suporte, consulte o administrador.");
        });
    }

    // Fechar modais ao clicar no fundo
    [modalHistorico, modalApartamentos].forEach(m => {
        m.addEventListener("click", (e) => {
            if (e.target === m) fecharModal(m);
        });
    });

    carregarDashboard();
});
