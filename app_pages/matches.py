from datetime import datetime, timezone

import streamlit as st

from src.db import (
    get_matches,
    get_user_match_predictions,
    upsert_match_prediction,
)
from src.utils import team_html

# ── Auth guard ────────────────────────────────────────────────────────────────
user = st.session_state.get("user")
if not user:
    st.warning("Faça seu cadastro para participar.", icon=":material/lock:")
    st.page_link("app_pages/register.py", label="Ir para cadastro", icon=":material/login:")
    st.stop()

st.markdown("## ⚽ Palpites de Placar")
st.caption("Palpite o placar de cada jogo. Placar exato vale 3 pts; acertar o resultado (V/E/D) vale 1 pt.")

# ── Dados ─────────────────────────────────────────────────────────────────────
all_matches = get_matches()
user_preds = get_user_match_predictions(user["id"])
now = datetime.now(tz=timezone.utc)

group_matches = [m for m in all_matches if m["stage"] == "group"]
ko_matches    = [m for m in all_matches if m["stage"] != "group"]

total_preds = len(user_preds)
st.caption(f"Palpites enviados: **{total_preds}** de {len(all_matches)} jogos")


def result_icon(pred: tuple[int, int] | None, match: dict) -> str:
    if not match["is_finished"] or pred is None:
        return ""
    ph, pa = pred
    rh, ra = match["home_score"], match["away_score"]
    if ph == rh and pa == ra:
        return "🎯"
    if (ph > pa) == (rh > ra) or (ph == pa) == (rh == ra):
        return "✅"
    return "❌"


@st.fragment
def render_match_card(match: dict) -> None:
    home = match.get("home_team") or {}
    away = match.get("away_team") or {}
    h_html = team_html(home.get("flag_emoji", ""), home.get("name", "?"), size=22, bold=True)
    a_html = team_html(away.get("flag_emoji", ""), away.get("name", "?"), size=22, bold=True)

    pred = user_preds.get(match["id"])

    # Jogo encerrado → mostra resultado e ícone de acerto
    if match["is_finished"]:
        icon = result_icon(pred, match)
        pts = ""
        if pred:
            ph, pa = pred
            rh, ra = match["home_score"], match["away_score"]
            if ph == rh and pa == ra:
                pts = " · <strong>3 pts</strong>"
            elif (ph > pa) == (rh > ra) or (ph == pa) == (rh == ra):
                pts = " · <strong>1 pt</strong>"
        palpite = (
            f"<br><small style='color:#888'>Seu palpite: {pred[0]}×{pred[1]}{pts}</small>"
            if pred else ""
        )
        st.markdown(
            f"<div style='padding:6px 0'>{icon} {h_html}"
            f"&nbsp;<strong>{match['home_score']} × {match['away_score']}</strong>&nbsp;"
            f"{a_html}{palpite}</div>",
            unsafe_allow_html=True,
        )
        return

    # Jogo bloqueado (já começou mas sem resultado)
    match_dt = None
    if match.get("match_date"):
        match_dt = datetime.fromisoformat(match["match_date"].replace("Z", "+00:00"))

    locked = bool(match_dt and now >= match_dt)

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
        with c1:
            st.markdown(h_html, unsafe_allow_html=True)
        with c2:
            h_val = pred[0] if pred else 0
            home_score = st.number_input(
                "Casa", min_value=0, max_value=20, value=h_val,
                key=f"h_{match['id']}", label_visibility="collapsed", disabled=locked,
            )
        with c3:
            st.markdown("<div style='text-align:center;padding-top:6px'>×</div>", unsafe_allow_html=True)
        with c4:
            a_val = pred[1] if pred else 0
            away_score = st.number_input(
                "Fora", min_value=0, max_value=20, value=a_val,
                key=f"a_{match['id']}", label_visibility="collapsed", disabled=locked,
            )
        with c5:
            st.markdown(
                f"<div style='text-align:right'>{a_html}</div>",
                unsafe_allow_html=True,
            )

        if not locked:
            saved = pred is not None
            lbl = ":material/check: Salvo" if saved else "Salvar"
            if st.button(lbl, key=f"save_m_{match['id']}", type="primary"):
                upsert_match_prediction(user["id"], match["id"], home_score, away_score)
                st.toast("Palpite salvo!", icon=":material/check_circle:")
                st.rerun(scope="fragment")
        else:
            st.caption(":material/lock: Jogo bloqueado")


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_groups, tab_ko = st.tabs(["Fase de grupos", "Mata-mata"])

with tab_groups:
    if not group_matches:
        st.info("Os jogos serão carregados em breve.")
    else:
        by_group: dict[str, list] = {}
        for m in group_matches:
            by_group.setdefault(m.get("group_code", "?"), []).append(m)

        for gc in sorted(by_group.keys()):
            with st.expander(f"Grupo {gc}", expanded=True):
                for match in by_group[gc]:
                    render_match_card(match)

with tab_ko:
    if not ko_matches:
        st.info("Os jogos do mata-mata serão gerados após a fase de grupos.")
    else:
        for match in ko_matches:
            render_match_card(match)
