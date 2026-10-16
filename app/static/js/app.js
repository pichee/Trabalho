document.addEventListener("DOMContentLoaded", () => {
    // 1. Verificação de Autenticação
    const token = localStorage.getItem("hidroreader_token");
    if (!token) {
        window.location.href = "/login";
        return;     
    }

    // Exibir nome do operador logado
    let userName = localStorage.getItem("hidroreader_name") || localStorage.getItem("hidroreader_user") || "Administrador";
    if (userName.includes("Administrador")) {
        userName = "Administrador";
        localStorage.setItem("hidroreader_name", userName);
    }
    const userNameText = document.getElementById("user-name-text");
    const userDisplay = document.getElementById("user-display");
    if (userNameText) {
        userNameText.textContent = userName;
    } else if (userDisplay) {
        userDisplay.textContent = userName;
    }

    // Botão de Logout
    const btnLogout = document.getElementById("btn-logout");
    if (btnLogout) {
        btnLogout.addEventListener("click", () => {
            localStorage.removeItem("hidroreader_token");
            localStorage.removeItem("hidroreader_user");
            localStorage.removeItem("hidroreader_name");
            window.location.href = "/login";
        });
    }

    // 2. Elementos da Interface
    const selectApartamento = document.getElementById("select-apartamento");
    const btnAddApto = document.getElementById("btn-add-apto");
    const fileInput = document.getElementById("file-input");
    const btnCamera = document.getElementById("btn-camera");
    const btnGallery = document.getElementById("btn-gallery");
    const btnProcess = document.getElementById("btn-process");
    const previewImg = document.getElementById("preview-img");
    const placeholderView = document.getElementById("placeholder-view");
    const loadingView = document.getElementById("loading-view");
    const resultCard = document.getElementById("result-card");
    const readingApto = document.getElementById("reading-apto");
    const readingVal = document.getElementById("reading-val");
    const readingMeta = document.getElementById("reading-meta");
    const digitsContainer = document.getElementById("digits-container");
    const alertsContainer = document.getElementById("alerts-container");

    let currentFile = null;

    // 3. Carregar lista de apartamentos do SQLite
    async function carregarApartamentos() {
        try {
            const resp = await fetch("/api/v1/apartamentos", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (resp.status === 401) {
                window.location.href = "/login";
                return;
            }
            const aptos = await resp.json();
            selectApartamento.innerHTML = '<option value="">-- Selecione o Apartamento --</option>';
            aptos.forEach(ap => {
                const opt = document.createElement("option");
                opt.value = ap.numero;
                opt.textContent = `Apartamento ${ap.numero} (${ap.bloco || "Geral"})`;
                selectApartamento.appendChild(opt);
            });
        } catch (e) {
            selectApartamento.innerHTML = '<option value="">Erro ao carregar lista</option>';
        }
    }

    carregarApartamentos();

    // Botão para cadastrar novo apartamento rapidamente
    btnAddApto.addEventListener("click", async () => {
        const novoNumero = prompt("Digite o número do novo apartamento (ex: 501):");
        if (!novoNumero || !novoNumero.trim()) return;

        try {
            const resp = await fetch("/api/v1/apartamentos", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ numero: novoNumero.trim() })
            });

            const data = await resp.json();
            if (!resp.ok) {
                alert(data.detail || "Erro ao cadastrar apartamento.");
                return;
            }

            await carregarApartamentos();
            selectApartamento.value = data.numero;
            alert(`Apartamento ${data.numero} cadastrado com sucesso!`);
        } catch (err) {
            alert("Erro: " + err.message);
        }
    });

    // 4. Captura de Foto
    btnCamera.addEventListener("click", () => {
        fileInput.setAttribute("capture", "environment"); // Câmera traseira do smartphone
        fileInput.click();
    });

    btnGallery.addEventListener("click", () => {
        fileInput.removeAttribute("capture");
        fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;

        currentFile = file;
        const reader = new FileReader();
        reader.onload = (event) => {
            previewImg.src = event.target.result;
            previewImg.style.display = "block";
            placeholderView.style.display = "none";
            btnProcess.disabled = false;
            resultCard.classList.remove("active");
        };
        reader.readAsDataURL(file);
    });

    // 5. Processamento e Leitura
    btnProcess.addEventListener("click", async () => {
        if (!currentFile) return;

        const aptoSelecionado = selectApartamento.value;
        if (!aptoSelecionado) {
            alert("Por favor, selecione o apartamento antes de realizar a leitura!");
            selectApartamento.focus();
            return;
        }

        loadingView.style.display = "flex";
        resultCard.classList.remove("active");
        btnProcess.disabled = true;

        const formData = new FormData();
        formData.append("foto", currentFile);
        formData.append("apartamento", aptoSelecionado);

        try {
            const response = await fetch("/api/v1/leituras/processar", {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                },
                body: formData
            });

            if (response.status === 401) {
                localStorage.removeItem("hidroreader_token");
                alert("Sessão expirada. Faça login novamente.");
                window.location.href = "/login";
                return;
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Erro ao processar imagem");
            }

            exibirResultado(data, aptoSelecionado);
        } catch (err) {
            alert("Erro: " + err.message);
        } finally {
            loadingView.style.display = "none";
            btnProcess.disabled = false;
        }
    });

    function exibirResultado(data, apto) {
        readingApto.textContent = `Apartamento ${apto}`;
        const valorFinal = data.leitura_completa || data.leitura_yolo;
        readingVal.textContent = valorFinal;
        
        let metaTexto = `Modelo: ${data.modelo_utilizado || "IA"} | Qualidade: ${data.qualidade_visor}`;
        if (data.digitos_pretos) {
            metaTexto += ` | Pretos: ${data.digitos_pretos} m³ | Vermelhos: ${data.digitos_vermelhos} L`;
        }
        readingMeta.textContent = metaTexto;

        digitsContainer.innerHTML = "";
        data.digitos.forEach(d => {
            const box = document.createElement("div");
            box.className = `digit-box ${d.incerto ? "warning" : ""}`;
            box.innerHTML = `
                <div class="digit-pos">#${d.posicao}</div>
                <div class="digit-char">${d.valor_yolo}</div>
                <div class="digit-conf">${d.confianca_yolo ? d.confianca_yolo + '%' : 'IA'}</div>
            `;
            digitsContainer.appendChild(box);
        });

        if (data.avisos && data.avisos.length > 0) {
            alertsContainer.style.display = "flex";
            alertsContainer.innerHTML = `
                <strong>
                    <svg class="icon-inline-sm" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                        <path d="M12 4L3.5 19H20.5L12 4Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
                        <path d="M12 10V14M12 16.5H12.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                    </svg>
                    Posições com Baixa Certeza:
                </strong>
                ${data.avisos.map(a => `<div>• ${a}</div>`).join("")}
            `;
        } else {
            alertsContainer.style.display = "none";
        }

        resultCard.classList.add("active");
        resultCard.scrollIntoView({ behavior: "smooth" });
    }
});
