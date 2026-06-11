"""
Feature 02 — Silver: limpeza + anti-leakage

Lê bronze_jogos, padroniza nomes de seleção, remove duplicatas, deriva
eh_amistoso e grava silver_jogos (histórico >= 2006) e silver_copa2026
(72 jogos futuros com gols nulos) via COPY (idempotente).
"""

import io

import pandas as pd

from src.pg_conn import get_engine, get_raw_connection

# Variantes de nome → nome canônico. Dados do Kaggle já são consistentes;
# dicionário pronto para receber ajustes futuros.
TEAM_NAME_MAP: dict[str, str] = {}

BUSINESS_COLS = [
    "data",
    "time_casa",
    "time_visitante",
    "gols_casa",
    "gols_visitante",
    "torneio",
    "cidade",
    "pais",
    "neutro",
]

CREATE_SQL = """
CREATE TABLE {table} (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data            DATE,
    time_casa       TEXT,
    time_visitante  TEXT,
    gols_casa       INTEGER,
    gols_visitante  INTEGER,
    torneio         TEXT,
    cidade          TEXT,
    pais            TEXT,
    neutro          BOOLEAN,
    eh_amistoso     BOOLEAN
);
"""


def read_bronze() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM bronze_jogos ORDER BY id", get_engine())
    df = df.drop(columns=["id"])
    df["gols_casa"] = df["gols_casa"].astype("Int64")
    df["gols_visitante"] = df["gols_visitante"].astype("Int64")
    return df


def standardize_names(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("time_casa", "time_visitante"):
        df[col] = df[col].str.strip().replace(TEAM_NAME_MAP)
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=BUSINESS_COLS)
    removed = before - len(df)
    if removed:
        print(f"Duplicatas removidas: {removed}")
    return df


def derive_features(df: pd.DataFrame) -> pd.DataFrame:
    df["eh_amistoso"] = df["torneio"] == "Friendly"
    return df


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    mask_copa = df["gols_casa"].isna()
    silver_copa2026 = df[mask_copa].reset_index(drop=True)
    silver_jogos = df[~mask_copa & (df["data"] >= pd.Timestamp("2006-01-01").date())].reset_index(drop=True)
    return silver_jogos, silver_copa2026


def print_inventory(df: pd.DataFrame, label: str) -> None:
    print(f"\n{'='*50}")
    print(f"{label} — Linhas: {len(df):,}")
    print("\nTipos:")
    print(df.dtypes.to_string())
    null_pct = (df.isnull().mean() * 100).round(2)
    print("\n% de nulos por coluna:")
    print(null_pct.to_string())
    print("=" * 50)


def load_table(df: pd.DataFrame, table: str, conn) -> None:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {table};")
        cur.execute(CREATE_SQL.format(table=table))

        buf = io.StringIO()
        df.to_csv(buf, index=False, na_rep="")
        buf.seek(0)

        cols = ", ".join(df.columns)
        cur.copy_expert(
            f"COPY {table} ({cols}) FROM STDIN "
            f"WITH (FORMAT CSV, HEADER TRUE, NULL '')",
            buf,
        )
    print(f"Tabela {table} criada com {len(df):,} linhas.")


def main() -> None:
    print("Lendo bronze_jogos ...")
    df = read_bronze()
    print(f"Bronze: {len(df):,} linhas.")

    df = standardize_names(df)
    df = remove_duplicates(df)
    df = derive_features(df)

    silver_jogos, silver_copa2026 = split(df)

    print_inventory(silver_jogos, "silver_jogos")
    print_inventory(silver_copa2026, "silver_copa2026")

    conn = get_raw_connection()
    try:
        load_table(silver_jogos, "silver_jogos", conn)
        load_table(silver_copa2026, "silver_copa2026", conn)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
