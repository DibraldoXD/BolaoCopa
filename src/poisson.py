"""
Módulo compartilhado de probabilidades Poisson (features 06/07/08).
"""

import numpy as np
from scipy.stats import poisson as sp_poisson

MAX_GOLS = 10


def probabilidades_resultado(
    lc: float, lv: float, max_gols: int = MAX_GOLS
) -> tuple[float, float, float]:
    """Retorna (p_vitoria, p_empate, p_derrota) via grade de Poisson."""
    g = np.arange(0, max_gols + 1)
    grade = np.outer(sp_poisson.pmf(g, lc), sp_poisson.pmf(g, lv))
    return float(np.tril(grade, -1).sum()), float(np.trace(grade)), float(np.triu(grade, 1).sum())


def resultado_previsto(lc: float, lv: float) -> str:
    pv, pe, pd_ = probabilidades_resultado(lc, lv)
    return ["V", "E", "D"][int(np.argmax([pv, pe, pd_]))]


def resultado_real(gc: int, gv: int) -> str:
    if gc > gv:
        return "V"
    if gc == gv:
        return "E"
    return "D"
