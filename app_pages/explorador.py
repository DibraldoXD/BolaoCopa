import streamlit as st
from bandeiras import team_flag_html, traduzir

try:
    from previsao import PESO_TORNEIO_COPA, carregar_modelos, prever_jogo
    _ML_OK = True
except Exception as _e:
    _ML_OK = False
    _ML_ERRO = str(_e)

if not _ML_OK:
    st.error(f"Pipeline ML não disponível: {_ML_ERRO}", icon=":material/error:")
    st.info("Verifique se DATABASE_URL está configurado nos secrets do Streamlit Cloud.")
    st.stop()


@st.cache_resource
def get_modelos() -> tuple:
    return carregar_modelos()


st.title("🔍 Explorador de Partidas")

with st.expander("Como funciona a previsão?"):
    st.markdown("""
    O modelo prevê o resultado de qualquer confronto entre seleções da Copa 2026:

    | Componente | Detalhe |
    |---|---|
    | **Modelo** | GLM Poisson separado para gols do time da casa e do visitante |
    | **xG** | Gols esperados (expected goals) — saída direta do modelo |
    | **ELO** | Rating histórico da seleção como principal feature preditiva |
    | **Campo neutro** | Remove a vantagem estimada de jogar em casa (~100 pts ELO) |
    | **V/E/D** | Probabilidades calculadas via distribuição conjunta Poisson |

    As previsões são baseadas no desempenho histórico; resultados reais podem surpreender.
    """)

mc, mv, elo_dict = get_modelos()
todos = sorted(elo_dict.keys())

col1, col2 = st.columns(2)
with col1:
    casa = st.selectbox("Time da casa", todos, format_func=traduzir)
with col2:
    fora = st.selectbox("Visitante", todos, index=1, format_func=traduzir)

neutro = st.checkbox("Campo neutro")

if st.button("⚽ Prever"):
    if casa == fora:
        st.warning("Escolha dois times diferentes.")
    else:
        p = prever_jogo(casa, fora, neutro, PESO_TORNEIO_COPA, elo_dict, mc, mv)

        # Cabeçalho com bandeiras
        st.markdown(
            f"**{team_flag_html(casa, 24)}** vs **{team_flag_html(fora, 24)}**",
            unsafe_allow_html=True,
        )

        # Métricas numéricas
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("xG Casa",     f"{p['gols_esperados_casa']:.2f}")
        m2.metric("xG Visitante",f"{p['gols_esperados_visitante']:.2f}")
        m3.metric("% Vitória",   f"{p['prob_vitoria']:.1%}")
        m4.metric("% Empate",    f"{p['prob_empate']:.1%}")
        m5.metric("% Derrota",   f"{p['prob_derrota']:.1%}")
