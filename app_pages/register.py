import streamlit as st
from src.db import upsert_user, check_user_login

st.markdown("# ⚽ Bolão Copa do Mundo 2026")
st.markdown("Faça seu cadastro para participar e enviar seus palpites.")

tab_new, tab_existing = st.tabs(["Novo participante", "Já me cadastrei"])

# ── Cadastro ──────────────────────────────────────────────────────────────────
with tab_new:
    with st.form("form_registro", border=False):
        st.subheader("Cadastro")
        name     = st.text_input("Nome completo",          placeholder="João Silva")
        email    = st.text_input("E-mail",                 placeholder="joao@email.com")
        phone    = st.text_input("Telefone (WhatsApp)",    placeholder="(11) 99999-9999")
        pwd      = st.text_input("Senha",                  type="password")
        pwd2     = st.text_input("Confirmar senha",        type="password")
        submitted = st.form_submit_button(
            "Entrar no bolão", type="primary", use_container_width=True
        )

    if submitted:
        err = None
        if not all([name.strip(), email.strip(), phone.strip(), pwd, pwd2]):
            err = "Preencha todos os campos."
        elif "@" not in email:
            err = "E-mail inválido."
        elif len(pwd) < 6:
            err = "A senha deve ter no mínimo 6 caracteres."
        elif pwd != pwd2:
            err = "As senhas não coincidem."

        if err:
            st.error(err, icon=":material/error:")
        else:
            try:
                user = upsert_user(
                    name.strip(), email.strip().lower(), phone.strip(), pwd
                )
                st.session_state.user = user
                st.toast(f"Bem-vindo, {user['name']}!", icon="⚽")
                st.switch_page("app_pages/groups.py")
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}", icon=":material/error:")

# ── Login ─────────────────────────────────────────────────────────────────────
with tab_existing:
    with st.form("form_login", border=False):
        st.subheader("Acessar minha conta")
        email_login = st.text_input("E-mail cadastrado", placeholder="joao@email.com")
        pwd_login   = st.text_input("Senha",             type="password")
        login = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    if login:
        if not email_login.strip() or not pwd_login:
            st.error("Preencha e-mail e senha.", icon=":material/error:")
        else:
            result = check_user_login(email_login.strip().lower(), pwd_login)
            if result is None:
                st.error(
                    "E-mail não encontrado ou senha incorreta.",
                    icon=":material/person_off:",
                )
            elif result == "no_password":
                st.warning(
                    "Sua conta ainda não possui senha. "
                    "Use a aba **Novo participante** para definir uma.",
                    icon=":material/lock:",
                )
            else:
                st.session_state.user = result
                st.toast(f"Bem-vindo de volta, {result['name']}!", icon="⚽")
                st.switch_page("app_pages/groups.py")
