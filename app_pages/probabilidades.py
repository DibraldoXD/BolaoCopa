import altair as alt
import pandas as pd
import streamlit as st
from bandeiras import team_flag_html, traduzir
from pg_conn import get_engine

FASES = {
    "prob_grupo":   "Grupos",
    "prob_oitavas": "Oitavas",
    "prob_quartas": "Quartas",
    "prob_semi":    "Semis",
    "prob_final":   "Final",
    "prob_campea":  "Campeã",
}


@st.cache_data
def load_probabilidades() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT * FROM gold_probabilidades_copa ORDER BY prob_campea DESC LIMIT 12",
        get_engine(),
    )


st.title("🏆 Copa 2026 — Probabilidades de título")

with st.expander("Como essas probabilidades foram calculadas?"):
    st.markdown("""
    As probabilidades são obtidas a partir de **1.000 simulações Monte Carlo** do torneio completo:

    | Componente | Detalhe |
    |---|---|
    | **Modelo** | GLM Poisson treinado em ~13.000 jogos oficiais (2006–2026) |
    | **Features** | Rating ELO de cada seleção, diferença de ELO, campo neutro |
    | **ELO** | Atualizado sequencialmente jogo a jogo; K-factor varia por importância do torneio |
    | **Peso** | Copa do Mundo e finais de continentais têm peso 3×; amistosos são excluídos |
    | **Resultado** | Cada célula = % de simulações em que a seleção atingiu aquela fase |
    """)

df = load_probabilidades()
df["nome_ptbr"] = df["selecao"].apply(traduzir)

# Gráfico de barras — nomes PT-BR no eixo
chart = (
    alt.Chart(df)
    .mark_bar(color="#C8960C")
    .encode(
        x=alt.X("prob_campea:Q", title="Probabilidade de título",
                axis=alt.Axis(format=".0%")),
        y=alt.Y("nome_ptbr:N", sort="-x", title=None),
        tooltip=[
            alt.Tooltip("nome_ptbr:N", title="Seleção"),
            alt.Tooltip("prob_campea:Q", format=".1%", title="% título"),
            alt.Tooltip("prob_final:Q",  format=".1%", title="% final"),
            alt.Tooltip("prob_semi:Q",   format=".1%", title="% semi"),
        ],
    )
    .properties(height=420)
)
st.altair_chart(chart, use_container_width=True)

# Tabela com bandeiras via HTML
header_cols = ["Seleção"] + list(FASES.values())
header_html = "".join(f"<th style='text-align:right;padding:4px 8px'>{c}</th>" for c in header_cols[1:])
rows_html = ""
for _, row in df.iterrows():
    flag_cell = team_flag_html(row["selecao"], 20)  # team_flag_html já usa PT-BR
    vals = "".join(
        f"<td style='text-align:right;padding:4px 8px'>{row[col]:.1%}</td>"
        for col in FASES
    )
    rows_html += f"<tr><td style='padding:4px 8px'>{flag_cell}</td>{vals}</tr>"

st.markdown(
    f"""<table style='width:100%;border-collapse:collapse;font-size:0.9em'>
    <thead><tr>
      <th style='text-align:left;padding:4px 8px'>Seleção</th>{header_html}
    </tr></thead>
    <tbody>{rows_html}</tbody>
    </table>""",
    unsafe_allow_html=True,
)
