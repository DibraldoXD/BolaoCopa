"""
Feature 01 — Bronze: ingestão do results.csv

Lê data/results.csv, renomeia colunas para português, faz conversões mínimas
de tipo e grava na tabela bronze_jogos via COPY (idempotente).
"""

import argparse
import io
import os

import pandas as pd

from src.pg_conn import get_raw_connection

COLUMN_MAP = {
    "date":        "data",
    "home_team":   "time_casa",
    "away_team":   "time_visitante",
    "home_score":  "gols_casa",
    "away_score":  "gols_visitante",
    "tournament":  "torneio",
    "city":        "cidade",
    "country":     "pais",
    "neutral":     "neutro",
}

CREATE_SQL = """
CREATE TABLE bronze_jogos (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data            DATE,
    time_casa       TEXT,
    time_visitante  TEXT,
    gols_casa       INTEGER,
    gols_visitante  INTEGER,
    torneio         TEXT,
    cidade          TEXT,
    pais            TEXT,
    neutro          BOOLEAN
);
"""


def resolve_csv_path(cli_path: str | None) -> str:
    return cli_path or os.environ.get("CAMINHO_CSV", "data/results.csv")


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df["home_score"] = df["home_score"].astype("Int64")
    df["away_score"] = df["away_score"].astype("Int64")
    df["neutral"] = df["neutral"].astype(bool)
    return df.rename(columns=COLUMN_MAP)


def print_inventory(df: pd.DataFrame) -> None:
    print(f"\n{'='*50}")
    print(f"Linhas: {len(df):,}")
    print("\nTipos:")
    print(df.dtypes.to_string())
    null_pct = (df.isnull().mean() * 100).round(2)
    print("\n% de nulos por coluna:")
    print(null_pct.to_string())
    print("=" * 50)


def load_to_db(df: pd.DataFrame) -> None:
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS bronze_jogos;")
            cur.execute(CREATE_SQL)

            buf = io.StringIO()
            df.to_csv(buf, index=False, na_rep="")
            buf.seek(0)

            cols = ", ".join(df.columns)
            cur.copy_expert(
                f"COPY bronze_jogos ({cols}) FROM STDIN "
                f"WITH (FORMAT CSV, HEADER TRUE, NULL '')",
                buf,
            )
        conn.commit()
        print(f"\nTabela bronze_jogos criada com {len(df):,} linhas.")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestão bronze: results.csv → bronze_jogos")
    parser.add_argument("--csv", dest="csv_path", default=None, help="Caminho para o results.csv")
    args = parser.parse_args()

    csv_path = resolve_csv_path(args.csv_path)
    print(f"Lendo {csv_path} ...")

    df = load_csv(csv_path)
    print_inventory(df)
    load_to_db(df)


if __name__ == "__main__":
    main()
