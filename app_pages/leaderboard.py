import pandas as pd
import streamlit as st

from src.db import get_leaderboard

# ── Auth guard ────────────────────────────────────────────────────────────────
user = st.session_state.get("user")
if not user:
    st.warning("Faça seu cadastro para participar.", icon=":material/lock:")
    st.page_link("app_pages/register.py", label="Ir para cadastro", icon=":material/login:")
    st.stop()

st.markdown("## 🏅 Classificação")

tab_rank, tab_ia = st.tabs(["🏅 Ranking", "🤖 Previsão IA"])

# ── Aba 1: Ranking dos participantes ─────────────────────────────────────────
with tab_rank:
    @st.fragment(run_every="60s")
    def render_leaderboard() -> None:
        data = get_leaderboard()

        if not data:
            st.info("Nenhum palpite registrado ainda. Seja o primeiro!", icon=":material/info:")
            return

        df = pd.DataFrame(data)
        df = df[["name", "group_points", "match_points", "total_points"]].copy()
        df.insert(0, "pos", range(1, len(df) + 1))

        def medal(pos: int) -> str:
            return {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, str(pos))

        df["pos"] = df["pos"].apply(medal)

        current_email = user["email"]
        highlight_idx = None
        for i, row in enumerate(data):
            if row.get("email") == current_email:
                highlight_idx = i
                break

        df = df.rename(columns={
            "pos": "Pos",
            "name": "Participante",
            "group_points": "Grupos",
            "match_points": "Jogos",
            "total_points": "Total",
        })

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Pos":          st.column_config.TextColumn("Pos", width="small"),
                "Participante": st.column_config.TextColumn("Participante"),
                "Grupos":       st.column_config.NumberColumn("Grupos (pts)", format="%d"),
                "Jogos":        st.column_config.NumberColumn("Jogos (pts)", format="%d"),
                "Total":        st.column_config.NumberColumn("Total", format="%d"),
            },
            height=min(400, 38 + 35 * len(df)),
        )

        if highlight_idx is not None:
            st.info(
                f"Você está em **{medal(highlight_idx + 1)}** lugar com "
                f"**{data[highlight_idx]['total_points']} pts**.",
                icon=":material/person:",
            )

        st.caption("Atualizado automaticamente a cada 60 segundos.")

    render_leaderboard()

    with st.expander("Como funciona a pontuação?"):
        st.markdown("""
        | Palpite | Pontos |
        |---|---|
        | Time certo na posição exata do grupo (1°, 2° ou 3°) | **10 pts** |
        | Time certo em posição errada no grupo | **5 pts** |
        | Placar exato do jogo | **3 pts** |
        | Resultado certo do jogo (V/E/D) | **1 pt** |

        Máximo por grupos: 12 grupos × 3 posições × 10 = **360 pts**
        """)


# ── Aba 2: Previsão IA por grupo ──────────────────────────────────────────────
with tab_ia:
    st.markdown(
        "Projeção do modelo IA para a fase de grupos, baseada em **1.000 simulações Monte Carlo**. "
        "Use para comparar com os seus palpites."
    )

    @st.cache_data(ttl=3600)
    def load_previsao_grupos() -> pd.DataFrame:
        from pg_conn import get_engine
        gold = pd.read_sql("SELECT * FROM gold_probabilidades_copa", get_engine())
        grupos = pd.read_csv("data/grupos_copa2026.csv")
        return gold.merge(grupos, left_on="selecao", right_on="nation", how="left")

    try:
        merged = load_previsao_grupos()
    except Exception as e:
        st.warning(
            f"Previsão IA indisponível — pipeline ML não configurado. ({e})",
            icon=":material/info:",
        )
        st.stop()

    from bandeiras import team_flag_html

    grupos_order = sorted(merged["group"].dropna().unique())
    cols_per_row = 4
    n_grupos = len(grupos_order)

    for row_start in range(0, n_grupos, cols_per_row):
        row_grupos = grupos_order[row_start: row_start + cols_per_row]
        cols = st.columns(cols_per_row)

        for col_idx, g in enumerate(row_grupos):
            gdf = (
                merged[merged["group"] == g]
                .sort_values("prob_grupo", ascending=False)
                .reset_index(drop=True)
            )

            with cols[col_idx]:
                st.markdown(f"**Grupo {g}**")

                rows_html = ""
                for rank_i, (_, r) in enumerate(gdf.iterrows(), 1):
                    # Destaque visual: top 2 têm maior prob de avançar
                    style = "font-weight:bold" if rank_i <= 2 else "color:#888"
                    bar_w = int(r["prob_grupo"] * 100)
                    bar_html = (
                        f"<div style='background:#C8960C;height:4px;"
                        f"width:{bar_w}%;border-radius:2px;margin-top:2px'></div>"
                    )
                    rows_html += (
                        f"<tr style='{style}'>"
                        f"<td style='padding:3px 4px;width:20px'>{rank_i}</td>"
                        f"<td style='padding:3px 4px'>"
                        f"{team_flag_html(r['selecao'], 14)}</td>"
                        f"<td style='padding:3px 4px;text-align:right;"
                        f"font-size:0.85em;color:#666'>{r['prob_grupo']:.0%}</td>"
                        f"</tr>"
                        f"<tr><td></td><td colspan='2'>{bar_html}</td></tr>"
                    )

                st.markdown(
                    f"<table style='width:100%;border-collapse:collapse;"
                    f"font-size:0.85em'><tbody>{rows_html}</tbody></table>",
                    unsafe_allow_html=True,
                )

    st.caption(
        "% = probabilidade de avançar para o mata-mata (top 2 do grupo). "
        "Top 8 terceiros colocados também avançam."
    )
