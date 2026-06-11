import streamlit as st
from bandeiras import team_flag_html

try:
    from monte_carlo import NOMES_RODADA, preparar, simular_torneio_detalhado
    _ML_OK = True
except Exception as _e:
    _ML_OK = False
    _ML_ERRO = str(_e)

if not _ML_OK:
    st.error(f"Pipeline ML não disponível: {_ML_ERRO}", icon=":material/error:")
    st.info("Verifique se DATABASE_URL está configurado nos secrets do Streamlit Cloud.")
    st.stop()


@st.cache_resource
def get_preparado() -> dict:
    return preparar()


st.title("🎲 Simulação ao Vivo")

with st.expander("Como funciona a simulação?"):
    st.markdown("""
    Cada execução roda **1 simulação completa** do torneio Copa 2026 (48 → 1):

    | Etapa | Método |
    |---|---|
    | **Fase de grupos** | Gols simulados via distribuição Poisson com λ do modelo GLM |
    | **Classificação** | Pontos → saldo de gols → gols pró → sorteio aleatório |
    | **Top 8 terceiros** | Bipartite matching para respeitar os slots do R32 da FIFA |
    | **Mata-mata** | Gols Poisson; empate no placar → pênaltis por coin flip |
    | **Variação** | Cada clique em "Simular novamente" gera um cenário diferente |

    As probabilidades *médias* de 1.000 simulações estão na página **Probabilidades**.
    """)

try:
    preparado = get_preparado()
except Exception as e:
    st.warning(f"Simulação indisponível — configure DATABASE_URL nos secrets do Streamlit Cloud. ({e})")
    st.stop()

if st.button("🔄 Simular novamente") or "sim_result" not in st.session_state:
    with st.spinner("Simulando o torneio completo..."):
        st.session_state.sim_result = simular_torneio_detalhado(preparado)

res = st.session_state.sim_result

# ── Pódio ─────────────────────────────────────────────────────────────────────
st.subheader("🏅 Pódio")
c1, c2, c3 = st.columns(3)

with c2:
    st.markdown("**🥇 Campeã**")
    st.markdown(team_flag_html(res["campea"], 28), unsafe_allow_html=True)

with c1:
    st.markdown("**🥈 Vice**")
    st.markdown(team_flag_html(res["vice"], 28), unsafe_allow_html=True)

with c3:
    st.markdown("**🥉 3º lugar**")
    terceiro = res.get("terceiro")
    if terceiro:
        st.markdown(team_flag_html(terceiro, 28), unsafe_allow_html=True)
    else:
        st.markdown("—")

# ── Mata-mata ─────────────────────────────────────────────────────────────────
st.subheader("🗓️ Mata-mata")
for round_key, round_name in NOMES_RODADA.items():
    jogos = res["mata_mata"].get(round_key, [])
    if not jogos:
        continue
    st.markdown(f"**{round_name}**")
    for j in jogos:
        pen = " *(pênaltis)*" if j["penaltis"] else ""
        home_html = team_flag_html(j["home"])
        away_html = team_flag_html(j["away"])
        venc_html  = team_flag_html(j["vencedor"])
        st.markdown(
            f"{home_html} {j['gc']} × {j['gv']} {away_html}{pen}"
            f" → <strong>{venc_html}</strong>",
            unsafe_allow_html=True,
        )

# ── Fase de grupos ────────────────────────────────────────────────────────────
st.subheader("📊 Fase de grupos")
grupos_ord = sorted(res["grupos"].items())
cols = st.columns(4)

for i, (g, dados) in enumerate(grupos_ord):
    with cols[i % 4]:
        st.markdown(f"**Grupo {g}**")
        df_class = dados["classificacao"]

        rows_html = ""
        for _, row in df_class.iterrows():
            sg = int(row["saldo_gols"])
            sg_str = f"+{sg}" if sg > 0 else str(sg)
            flag_td = team_flag_html(row["selecao"], 16)
            rows_html += (
                f"<tr>"
                f"<td style='padding:2px 4px;color:#888'>{int(row['posicao'])}</td>"
                f"<td style='padding:2px 4px'>{flag_td}</td>"
                f"<td style='padding:2px 4px;text-align:right'>{int(row['pontos'])}</td>"
                f"<td style='padding:2px 4px;text-align:right;color:#888'>{sg_str}</td>"
                f"</tr>"
            )

        st.markdown(
            f"<table style='width:100%;border-collapse:collapse;font-size:0.82em'>"
            f"<thead><tr>"
            f"<th style='padding:2px 4px'>#</th>"
            f"<th style='padding:2px 4px'>Seleção</th>"
            f"<th style='padding:2px 4px;text-align:right'>Pts</th>"
            f"<th style='padding:2px 4px;text-align:right'>SG</th>"
            f"</tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            f"</table>",
            unsafe_allow_html=True,
        )
