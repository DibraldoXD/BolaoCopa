import os
import sys

import streamlit as st

# Adiciona src/ ao path para que as páginas de IA possam usar imports flat
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Expõe DATABASE_URL ao ambiente (necessário para o pipeline ML)
try:
    if "DATABASE_URL" in st.secrets and "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
except Exception:
    pass

from src.db import ensure_seeded  # noqa: E402

st.set_page_config(
    page_title="Copa 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_seeded()

st.session_state.setdefault("user", None)
user = st.session_state.get("user")

bolao_pages = [
    st.Page("app_pages/groups.py",      title="Grupos (Top 3)",    icon=":material/emoji_events:"),
    st.Page("app_pages/matches.py",     title="Palpites de Jogos", icon=":material/sports_soccer:"),
    st.Page("app_pages/chave.py",        title="Chave Mata-Mata",   icon=":material/account_tree:"),
    st.Page("app_pages/leaderboard.py", title="Classificação",     icon=":material/leaderboard:"),
]

ia_pages = [
    st.Page("app_pages/probabilidades.py", title="Probabilidades",       icon=":material/bar_chart:"),
    st.Page("app_pages/simulacao.py",      title="Simulação ao Vivo",    icon=":material/casino:"),
    st.Page("app_pages/explorador.py",     title="Explorador de Partidas", icon=":material/search:"),
]

pages: dict = {
    "": [st.Page("app_pages/register.py", title="Entrar", icon=":material/login:")],
    "Bolão": bolao_pages,
    "Previsões IA": ia_pages,
}

if user and user.get("is_admin"):
    pages["Admin"] = [st.Page("app_pages/admin.py", title="Resultados", icon=":material/edit:")]

pg = st.navigation(pages)

with st.sidebar:
    if user:
        st.markdown(f"**{user['name']}**")
        st.caption(user["email"])
        if st.button("Sair", type="tertiary", icon=":material/logout:"):
            st.session_state.user = None
            st.rerun()
    else:
        st.caption("Faça seu cadastro para participar.")

pg.run()
