import streamlit as st
from src.db import get_user_group_predictions, get_teams_by_id, get_matches, get_group_results
from src.bracket import generate_bracket
from src.utils import team_html

# ── Auth guard ────────────────────────────────────────────────────────────────
user = st.session_state.get("user")
if not user:
    st.warning("Faça seu cadastro para participar.", icon=":material/lock:")
    st.page_link("app_pages/register.py", label="Ir para cadastro", icon=":material/login:")
    st.stop()

st.markdown("## 🗂️ Chave Mata-Mata")

picks = get_user_group_predictions(user["id"])
teams_by_id = get_teams_by_id()
completed_groups = sum(1 for g in picks.values() if len(g) == 3)

tab_mine, tab_official = st.tabs(["Meu palpite", "Chave oficial"])


# ── Helpers ───────────────────────────────────────────────────────────────────
def render_match_slot(home: dict, away: dict, label: str = "", result_home: int | None = None, result_away: int | None = None) -> None:
    h_html = team_html(home.get("flag_emoji", ""), home.get("name", "?"), size=20, bold=True)
    a_html = team_html(away.get("flag_emoji", ""), away.get("name", "?"), size=20, bold=True)
    score  = f"<strong>{result_home} × {result_away}</strong>" if result_home is not None else "vs"
    with st.container(border=True):
        if label:
            st.caption(label)
        c1, c2, c3 = st.columns([5, 1, 5])
        c1.markdown(h_html, unsafe_allow_html=True)
        c2.markdown(f"<div style='text-align:center'>{score}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='text-align:right'>{a_html}</div>", unsafe_allow_html=True)


def render_bracket(r32: list[dict]) -> None:
    if not r32:
        st.info("Nenhum confronto gerado ainda.")
        return
    cols = st.columns(2)
    for i, m in enumerate(r32):
        with cols[i % 2]:
            render_match_slot(m["home"], m["away"], m.get("label", ""))


# ── Tab: meu palpite ──────────────────────────────────────────────────────────
with tab_mine:
    if completed_groups < 12:
        st.info(
            f"Você preencheu **{completed_groups}/12** grupos. "
            "Preencha todos os grupos para ver sua chave completa.",
            icon=":material/info:",
        )
        st.page_link("app_pages/groups.py", label="Ir para palpites de grupos", icon=":material/emoji_events:")
    else:
        bracket = generate_bracket(picks, teams_by_id)
        r32 = bracket["round_of_32"]

        st.markdown(f"### Rodada de 32 ({len(r32)} jogos)")
        st.caption("Times que você previu no top 3 de cada grupo.")
        render_bracket(r32)

        st.markdown("---")
        st.markdown(f"**32 classificados no seu palpite:**")
        adv = bracket.get("advancing", [])
        cols = st.columns(4)
        for i, t in enumerate(adv):
            cols[i % 4].markdown(
                team_html(t.get("flag_emoji", ""), t.get("name", "?"), size=20),
                unsafe_allow_html=True,
            )


# ── Tab: chave oficial ────────────────────────────────────────────────────────
with tab_official:
    group_results = get_group_results()
    if not group_results:
        st.info("Os resultados oficiais ainda não foram inseridos pelo administrador.")
    else:
        official_picks: dict[str, dict[int, int]] = {}
        for gc, positions in group_results.items():
            official_picks[gc] = {pos: tid for pos, tid in positions.items()}

        if len(official_picks) < 12:
            st.warning(f"Resultados de {len(official_picks)}/12 grupos disponíveis.", icon=":material/hourglass_top:")

        if official_picks:
            official_bracket = generate_bracket(official_picks, teams_by_id)
            r32_official = official_bracket["round_of_32"]
            st.markdown(f"### Rodada de 32 — Chave oficial ({len(r32_official)} jogos)")
            render_bracket(r32_official)

    # Jogos KO já cadastrados
    ko_matches = [m for m in get_matches() if m["stage"] not in ("group",)]
    if ko_matches:
        st.markdown("---")
        st.markdown("### Resultados do mata-mata")
        for m in ko_matches:
            home = m.get("home_team") or {}
            away = m.get("away_team") or {}
            rh = m.get("home_score")
            ra = m.get("away_score")
            render_match_slot(home, away, m.get("stage", ""), rh, ra)
