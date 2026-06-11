import streamlit as st
from src.db import (
    get_teams_by_group,
    get_group_results,
    upsert_group_result,
    get_matches,
    save_match_result,
)
from src.utils import flag_img

# ── Auth guard ────────────────────────────────────────────────────────────────
user = st.session_state.get("user")
if not user or not user.get("is_admin"):
    st.error("Acesso restrito ao administrador.", icon=":material/block:")
    st.stop()

st.markdown("## ⚙️ Administração — Resultados")

tab_groups, tab_matches = st.tabs(["Classificação por grupo", "Resultados de jogos"])

# ── Tab: resultados por grupo ─────────────────────────────────────────────────
with tab_groups:
    st.markdown("### Inserir classificação oficial por grupo")
    teams_by_group = get_teams_by_group()
    current_results = get_group_results()

    for gc in sorted(teams_by_group.keys()):
        with st.expander(f"Grupo {gc}", expanded=False):
            teams = teams_by_group[gc]
            # Selectbox usa só o nome (sem emoji — Windows não renderiza bandeiras)
            team_names = [t["name"] for t in teams]
            team_by_name = {t["name"]: t["id"] for t in teams}
            id_to_name   = {t["id"]: t["name"] for t in teams}
            existing = current_results.get(gc, {})

            def pick(pos: int, names: list[str]) -> int:
                tid = existing.get(pos)
                if tid:
                    n = id_to_name.get(tid)
                    return names.index(n) if n in names else 0
                return 0

            c1, c2, c3 = st.columns(3)
            with c1:
                s1 = st.selectbox("🥇 1°", team_names, index=pick(1, team_names), key=f"ar_{gc}_1")
            with c2:
                opts2 = [n for n in team_names if n != s1]
                s2 = st.selectbox("🥈 2°", opts2, index=pick(2, opts2), key=f"ar_{gc}_2")
            with c3:
                opts3 = [n for n in team_names if n not in (s1, s2)]
                s3 = st.selectbox("🥉 3°", opts3, index=pick(3, opts3), key=f"ar_{gc}_3")

            if st.button(f"Salvar grupo {gc}", key=f"save_ar_{gc}", type="primary"):
                upsert_group_result(gc, 1, team_by_name[s1])
                upsert_group_result(gc, 2, team_by_name[s2])
                upsert_group_result(gc, 3, team_by_name[s3])
                st.toast(f"Grupo {gc} salvo!", icon=":material/check_circle:")
                st.rerun()

# ── Tab: resultados de jogos ──────────────────────────────────────────────────
with tab_matches:
    st.markdown("### Inserir resultado de jogo")
    all_matches = get_matches()
    unfinished = [m for m in all_matches if not m["is_finished"]]

    if not unfinished:
        st.success("Todos os jogos cadastrados já têm resultado!")
    else:
        match_labels = {}
        for m in unfinished:
            home = m.get("home_team") or {}
            away = m.get("away_team") or {}
            lbl = f"#{m['match_number']} — {home.get('name','?')} × {away.get('name','?')}"
            match_labels[lbl] = m

        selected_label = st.selectbox("Selecione o jogo", list(match_labels.keys()))
        selected_match = match_labels[selected_label]

        from src.utils import team_html as _th
        c1, c2, c3 = st.columns([3, 1, 3])
        home = selected_match.get("home_team") or {}
        away = selected_match.get("away_team") or {}
        with c1:
            st.markdown(_th(home.get("flag_emoji",""), home.get("name","?"), bold=True), unsafe_allow_html=True)
            hs = st.number_input("Gols", min_value=0, max_value=20, value=0, key="admin_hs")
        with c2:
            st.markdown("<div style='text-align:center;padding-top:28px'>×</div>", unsafe_allow_html=True)
        with c3:
            st.markdown(_th(away.get("flag_emoji",""), away.get("name","?"), bold=True), unsafe_allow_html=True)
            as_ = st.number_input("Gols", min_value=0, max_value=20, value=0, key="admin_as")

        if st.button("Salvar resultado", type="primary"):
            save_match_result(selected_match["id"], hs, as_)
            st.toast("Resultado salvo!", icon=":material/check_circle:")
            st.rerun()
