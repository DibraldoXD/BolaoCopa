"""Scoring helpers. Cálculo principal está na SQL view `leaderboard`."""

from src.db import get_leaderboard


def get_user_rank(user_id: str) -> tuple[int, dict] | None:
    """Retorna (posição_1based, dados_do_usuário) ou None se não encontrado."""
    rows = get_leaderboard()
    for i, row in enumerate(rows):
        if row["user_id"] == user_id:
            return i + 1, row
    return None
