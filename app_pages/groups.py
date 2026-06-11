from datetime import datetime, timezone

import streamlit as st

from src.db import (
    get_teams_by_group,
    get_user_group_predictions,
    upsert_group_predictions,
    count_completed_groups,
)
from src.utils import flag_img, team_html

# ── Auth guard ────────────────────────────────────────────────────────────────
user = st.session_state.get("user")
if not user:
    st.warning("Faça seu cadastro para participar.", icon=":material/lock:")
    st.page_link("app_pages/register.py", label="Ir para cadastro", icon=":material/login:")
    st.stop()

# Torneio iniciou 11/jun/2026 00:00 BRT (UTC-3) = 03:00 UTC
TOURNAMENT_START = datetime(2026, 6, 11, 3, 0, 0, tzinfo=timezone.utc)
locked = datetime.now(tz=timezone.utc) >= TOURNAMENT_START

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🏆 Palpites — Top 3 de cada grupo")
st.caption(
    "Escolha as 3 seleções que você acha que vão avançar em cada grupo (1°, 2° e 3° lugar). "
    "Sua chave mata-mata será gerada automaticamente."
)

if locked:
    st.warning(
        "O torneio já começou — os palpites de grupos estão bloqueados.",
        icon=":material/lock:",
    )

# ── Dados ─────────────────────────────────────────────────────────────────────
teams_by_group = get_teams_by_group()
user_picks = get_user_group_predictions(user["id"])
completed = count_completed_groups(user_picks)
total = len(teams_by_group)

st.progress(completed / total if total else 0, text=f"{completed} de {total} grupos preenchidos")
st.divider()


# ── Card de grupo ─────────────────────────────────────────────────────────────
@st.fragment
def render_group_card(group_code: str, teams: list[dict]) -> None:
    picks = get_user_group_predictions(user["id"]).get(group_code, {})

    # Selectboxes usam apenas o nome (sem emoji — não renderiza no Windows)
    team_names = [t["name"] for t in teams]
    team_by_name = {t["name"]: t["id"] for t in teams}
    id_to_name  = {t["id"]: t["name"] for t in teams}
    emoji_map   = {t["name"]: t["flag_emoji"] for t in teams}

    def default(pos: int) -> int:
        tid = picks.get(pos)
        if tid:
            name = id_to_name.get(tid)
            return team_names.index(name) if name in team_names else 0
        return 0

    with st.container(border=True):
        # Cabeçalho dourado com nome do grupo
        st.markdown(
            f"<div style='background:#C8960C;color:#fff;padding:4px 10px;"
            f"border-radius:8px 8px 0 0;font-weight:700;font-size:0.9rem;margin-bottom:8px'>"
            f"GRUPO {group_code}</div>",
            unsafe_allow_html=True,
        )

        # Times do grupo com bandeiras reais
        flags_html = "&nbsp;&nbsp;".join(
            team_html(t["flag_emoji"], t["name"], size=20) for t in teams
        )
        st.markdown(
            f"<div style='font-size:0.85rem;margin-bottom:8px'>{flags_html}</div>",
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            sel1 = st.selectbox("🥇 1° lugar", team_names, index=default(1),
                                key=f"g{group_code}_1", disabled=locked)
        with c2:
            opts2 = [n for n in team_names if n != sel1]
            name2 = id_to_name.get(picks.get(2))
            idx2 = opts2.index(name2) if name2 in opts2 else 0
            sel2 = st.selectbox("🥈 2° lugar", opts2, index=idx2,
                                key=f"g{group_code}_2", disabled=locked)
        with c3:
            opts3 = [n for n in team_names if n not in (sel1, sel2)]
            name3 = id_to_name.get(picks.get(3))
            idx3 = opts3.index(name3) if name3 in opts3 else 0
            sel3 = st.selectbox("🥉 3° lugar", opts3, index=idx3,
                                key=f"g{group_code}_3", disabled=locked)

        # Eliminado com bandeira
        eliminated = [t for t in teams if t["name"] not in (sel1, sel2, sel3)]
        if eliminated:
            elim_html = "Eliminado: " + ", ".join(
                team_html(t["flag_emoji"], t["name"], size=16) for t in eliminated
            )
            st.markdown(
                f"<div style='font-size:0.8rem;color:#888;margin-top:4px'>{elim_html}</div>",
                unsafe_allow_html=True,
            )

        if not locked:
            saved = len(picks) == 3
            btn_label = ":material/check: Salvo" if saved else "Salvar grupo"
            if st.button(btn_label, key=f"save_{group_code}", type="primary", use_container_width=True):
                upsert_group_predictions(user["id"], group_code, {
                    1: team_by_name[sel1],
                    2: team_by_name[sel2],
                    3: team_by_name[sel3],
                })
                st.toast(f"Grupo {group_code} salvo!", icon=":material/check_circle:")
                st.rerun(scope="fragment")


# ── Grid 3 colunas × 4 linhas ────────────────────────────────────────────────
group_codes = sorted(teams_by_group.keys())
rows = [group_codes[i:i+3] for i in range(0, len(group_codes), 3)]

for row in rows:
    cols = st.columns(len(row))
    for col, gc in zip(cols, row):
        with col:
            render_group_card(gc, teams_by_group[gc])
