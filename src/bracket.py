"""
Algoritmo de geração da chave mata-mata da Copa 2026.

Formato WC2026:
- 12 grupos de 4 times → 32 times no mata-mata (R32)
- 24 classificados diretos (1° e 2° de cada grupo)
- 8 melhores 3°s colocados (dos 12 disponíveis)
- Simplificação: os 3°s dos grupos A–H avançam (primeiros 8 alfabeticamente)
"""

# Pareamento oficial do R32 WC2026 (pode ser ajustado após anúncio FIFA)
# Estrutura: (1° do grupo X, 2° do grupo Y)
R32_PAIRINGS: list[tuple[str, str, str]] = [
    # (grupo do 1°, grupo do 2°, label do jogo)
    ("A", "B", "Jogo 73"),
    ("C", "D", "Jogo 74"),
    ("E", "F", "Jogo 75"),
    ("G", "H", "Jogo 76"),
    ("I", "J", "Jogo 77"),
    ("K", "L", "Jogo 78"),
    ("B", "A", "Jogo 79"),  # 1°B vs 2°A
    ("D", "C", "Jogo 80"),
    ("F", "E", "Jogo 81"),
    ("H", "G", "Jogo 82"),
    ("J", "I", "Jogo 83"),
    ("L", "K", "Jogo 84"),
]

# Os 8 melhores 3°s (simplificação: grupos A–H)
BEST_THIRDS_GROUPS = list("ABCDEFGH")


def generate_bracket(
    picks: dict[str, dict[int, int]],
    teams_by_id: dict[int, dict],
) -> dict:
    """
    Gera a chave mata-mata a partir dos palpites de grupos do usuário.

    Args:
        picks: {group_code: {1: team_id, 2: team_id, 3: team_id}}
        teams_by_id: {team_id: {id, name, flag_emoji, ...}}

    Returns:
        {
          'round_of_32': [{'home': team_dict, 'away': team_dict, 'label': str}, ...],
          'advancing': [team_dict, ...]   # 32 times
        }
    """
    first  = {g: picks[g][1] for g in picks if 1 in picks[g]}
    second = {g: picks[g][2] for g in picks if 2 in picks[g]}
    thirds = {g: picks[g][3] for g in picks if 3 in picks[g]}

    best_thirds = [thirds[g] for g in BEST_THIRDS_GROUPS if g in thirds]

    r32 = []
    for first_group, second_group, label in R32_PAIRINGS:
        home_id = first.get(first_group)
        away_id = second.get(second_group)
        if home_id and away_id:
            r32.append({
                "home": teams_by_id.get(home_id, {"name": "?", "flag_emoji": "❓"}),
                "away": teams_by_id.get(away_id, {"name": "?", "flag_emoji": "❓"}),
                "label": label,
            })

    # Jogos dos melhores 3°s (4 pares)
    for i in range(0, min(len(best_thirds), 8), 2):
        if i + 1 < len(best_thirds):
            h_id, a_id = best_thirds[i], best_thirds[i + 1]
            r32.append({
                "home": teams_by_id.get(h_id, {"name": "?", "flag_emoji": "❓"}),
                "away": teams_by_id.get(a_id, {"name": "?", "flag_emoji": "❓"}),
                "label": f"Jogo {85 + i // 2}",
            })

    advancing = (
        list(first.values()) +
        list(second.values()) +
        best_thirds
    )
    unique_advancing = list(dict.fromkeys(advancing))  # preserva ordem, remove dup

    return {
        "round_of_32": r32,
        "advancing": [teams_by_id.get(tid, {}) for tid in unique_advancing],
    }
