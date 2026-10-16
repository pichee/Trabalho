document.addEventListener("DOMContentLoaded", () => {
    // Se o usuário já tiver um token válido salvo, redireciona direto para o leitor
    const token = localStorage.getItem("hidroreader_token");
    if (token) {
        window.location.href = "/leitor";
        return;
    }

    const loginForm = document.getElementById("login-form");
    const usuarioInput = document.getElementById("usuario");
    const senhaInput = document.getElementById("senha");
    const loginError = document.getElementById("login-error");
    const btnLogin = document.getElementById("btn-login");

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        loginError.style.display = "none";
        btnLogin.disabled = true;
        btnLogin.innerHTML = "<span>Entrando...</span>";

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

            // Redirecionar para a tela de leitura de hidrômetro
            window.location.href = "/leitor";
        } catch (err) {
            loginError.textContent = err.message;
            loginError.style.display = "block";
            btnLogin.disabled = false;
            btnLogin.innerHTML = "<span>Entrar no Aplicativo</span>";
        }
    });
});

