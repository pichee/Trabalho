document.addEventListener("DOMContentLoaded", () => {
    // Valida o token com o backend antes de redirecionar para evitar loops infinitos
    const token = localStorage.getItem("hidroreader_token");
    if (token) {
        fetch("/api/v1/auth/me", {
            headers: { "Authorization": `Bearer ${token}` }
        }).then(resp => {
            if (resp.ok) {
                window.location.href = "/dashboard";
            } else {
                // Token inválido ou expirado: limpa a sessão para permitir login novo
                localStorage.removeItem("hidroreader_token");
                localStorage.removeItem("hidroreader_user");
                localStorage.removeItem("hidroreader_name");
            }
        }).catch(() => {
            localStorage.removeItem("hidroreader_token");
        });
    }

    const loginForm = document.getElementById("loginForm");
    const usuarioInput = document.getElementById("usuario");
    const senhaInput = document.getElementById("senha");
    const togglePassword = document.getElementById("togglePassword");
    const eyeIcon = document.getElementById("eyeIcon");
    const loginError = document.getElementById("login-error");
    const btnSubmit = document.getElementById("btnSubmit");
    const btnText = document.getElementById("btnText");
    const toast = document.getElementById("toast");

    function showToast(msg, isSuccess = true) {
        toast.textContent = msg;
        toast.style.background = isSuccess ? "#0a0a0a" : "#dc2626";
        toast.classList.add("show");
        setTimeout(() => {
            toast.classList.remove("show");
        }, 3200);
    }

    // Alternar visibilidade da senha
    if (togglePassword && senhaInput) {
        togglePassword.addEventListener("click", (e) => {
            e.preventDefault();
            const isPassword = senhaInput.type === "password";
            senhaInput.type = isPassword ? "text" : "password";

            if (isPassword) {
                eyeIcon.innerHTML = `
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                `;
            } else {
                eyeIcon.innerHTML = `
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                `;
            }
        });
    }

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        loginError.style.display = "none";
        btnSubmit.disabled = true;
        btnText.textContent = "Acessando...";

        const usuario = usuarioInput.value.trim();
        const senha = senhaInput.value;

        try {
            const response = await fetch("/api/v1/auth/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ usuario, senha })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Usuário ou senha inválidos.");
            }

            // Salvar token e dados do usuário no localStorage
            localStorage.setItem("hidroreader_token", data.access_token);
            localStorage.setItem("hidroreader_user", data.usuario);
            localStorage.setItem("hidroreader_name", data.nome || data.usuario);

            showToast(`Bem-vindo, ${data.nome || data.usuario}!`, true);

            // Redireciona com leve delay para efeito visual agradável
            setTimeout(() => {
                window.location.href = "/dashboard";
            }, 600);
        } catch (err) {
            loginError.textContent = err.message;
            loginError.style.display = "block";
            showToast(err.message, false);
            btnSubmit.disabled = false;
            btnText.textContent = "Entrar";
        }
    });

    // Helper global para preencher contas de teste com 1 clique
    window.preencherLogin = function (user, pass) {
        usuarioInput.value = user;
        senhaInput.value = pass;
        loginError.style.display = "none";
        usuarioInput.focus();
    };
});
