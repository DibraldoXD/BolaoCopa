"""
Seed data para o Bolão Copa do Mundo 2026.

Grupos baseados no sorteio oficial de 5/dez/2024, Miami.
Fonte: https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/final-draw-results
"""

from itertools import combinations

# 48 seleções — 12 grupos de 4 times (sorteio oficial)
TEAMS: list[dict] = [
    # GRUPO A  (sede: México)
    {"name": "México",                    "group_code": "A", "flag_emoji": "🇲🇽", "confederation": "CONCACAF"},
    {"name": "África do Sul",             "group_code": "A", "flag_emoji": "🇿🇦", "confederation": "CAF"},
    {"name": "Coreia do Sul",             "group_code": "A", "flag_emoji": "🇰🇷", "confederation": "AFC"},
    {"name": "República Checa",           "group_code": "A", "flag_emoji": "🇨🇿", "confederation": "UEFA"},
    # GRUPO B  (sede: Canadá)
    {"name": "Canadá",                    "group_code": "B", "flag_emoji": "🇨🇦", "confederation": "CONCACAF"},
    {"name": "Bósnia e Herzegovina",      "group_code": "B", "flag_emoji": "🇧🇦", "confederation": "UEFA"},
    {"name": "Catar",                     "group_code": "B", "flag_emoji": "🇶🇦", "confederation": "AFC"},
    {"name": "Suíça",                     "group_code": "B", "flag_emoji": "🇨🇭", "confederation": "UEFA"},
    # GRUPO C
    {"name": "Brasil",                    "group_code": "C", "flag_emoji": "🇧🇷", "confederation": "CONMEBOL"},
    {"name": "Marrocos",                  "group_code": "C", "flag_emoji": "🇲🇦", "confederation": "CAF"},
    {"name": "Haiti",                     "group_code": "C", "flag_emoji": "🇭🇹", "confederation": "CONCACAF"},
    {"name": "Escócia",                   "group_code": "C", "flag_emoji": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "confederation": "UEFA"},
    # GRUPO D  (sede: EUA)
    {"name": "Estados Unidos",            "group_code": "D", "flag_emoji": "🇺🇸", "confederation": "CONCACAF"},
    {"name": "Paraguai",                  "group_code": "D", "flag_emoji": "🇵🇾", "confederation": "CONMEBOL"},
    {"name": "Austrália",                 "group_code": "D", "flag_emoji": "🇦🇺", "confederation": "AFC"},
    {"name": "Turquia",                   "group_code": "D", "flag_emoji": "🇹🇷", "confederation": "UEFA"},
    # GRUPO E
    {"name": "Alemanha",                  "group_code": "E", "flag_emoji": "🇩🇪", "confederation": "UEFA"},
    {"name": "Curaçau",                   "group_code": "E", "flag_emoji": "🇨🇼", "confederation": "CONCACAF"},
    {"name": "Costa do Marfim",           "group_code": "E", "flag_emoji": "🇨🇮", "confederation": "CAF"},
    {"name": "Equador",                   "group_code": "E", "flag_emoji": "🇪🇨", "confederation": "CONMEBOL"},
    # GRUPO F
    {"name": "Países Baixos",             "group_code": "F", "flag_emoji": "🇳🇱", "confederation": "UEFA"},
    {"name": "Japão",                     "group_code": "F", "flag_emoji": "🇯🇵", "confederation": "AFC"},
    {"name": "Suécia",                    "group_code": "F", "flag_emoji": "🇸🇪", "confederation": "UEFA"},
    {"name": "Tunísia",                   "group_code": "F", "flag_emoji": "🇹🇳", "confederation": "CAF"},
    # GRUPO G
    {"name": "Bélgica",                   "group_code": "G", "flag_emoji": "🇧🇪", "confederation": "UEFA"},
    {"name": "Egito",                     "group_code": "G", "flag_emoji": "🇪🇬", "confederation": "CAF"},
    {"name": "Irã",                       "group_code": "G", "flag_emoji": "🇮🇷", "confederation": "AFC"},
    {"name": "Nova Zelândia",             "group_code": "G", "flag_emoji": "🇳🇿", "confederation": "OFC"},
    # GRUPO H
    {"name": "Espanha",                   "group_code": "H", "flag_emoji": "🇪🇸", "confederation": "UEFA"},
    {"name": "Cabo Verde",                "group_code": "H", "flag_emoji": "🇨🇻", "confederation": "CAF"},
    {"name": "Arábia Saudita",            "group_code": "H", "flag_emoji": "🇸🇦", "confederation": "AFC"},
    {"name": "Uruguai",                   "group_code": "H", "flag_emoji": "🇺🇾", "confederation": "CONMEBOL"},
    # GRUPO I
    {"name": "França",                    "group_code": "I", "flag_emoji": "🇫🇷", "confederation": "UEFA"},
    {"name": "Senegal",                   "group_code": "I", "flag_emoji": "🇸🇳", "confederation": "CAF"},
    {"name": "Iraque",                    "group_code": "I", "flag_emoji": "🇮🇶", "confederation": "AFC"},
    {"name": "Noruega",                   "group_code": "I", "flag_emoji": "🇳🇴", "confederation": "UEFA"},
    # GRUPO J
    {"name": "Argentina",                 "group_code": "J", "flag_emoji": "🇦🇷", "confederation": "CONMEBOL"},
    {"name": "Argélia",                   "group_code": "J", "flag_emoji": "🇩🇿", "confederation": "CAF"},
    {"name": "Áustria",                   "group_code": "J", "flag_emoji": "🇦🇹", "confederation": "UEFA"},
    {"name": "Jordânia",                  "group_code": "J", "flag_emoji": "🇯🇴", "confederation": "AFC"},
    # GRUPO K
    {"name": "Portugal",                  "group_code": "K", "flag_emoji": "🇵🇹", "confederation": "UEFA"},
    {"name": "Rep. Dem. do Congo",        "group_code": "K", "flag_emoji": "🇨🇩", "confederation": "CAF"},
    {"name": "Uzbequistão",               "group_code": "K", "flag_emoji": "🇺🇿", "confederation": "AFC"},
    {"name": "Colômbia",                  "group_code": "K", "flag_emoji": "🇨🇴", "confederation": "CONMEBOL"},
    # GRUPO L
    {"name": "Inglaterra",                "group_code": "L", "flag_emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "confederation": "UEFA"},
    {"name": "Croácia",                   "group_code": "L", "flag_emoji": "🇭🇷", "confederation": "UEFA"},
    {"name": "Gana",                      "group_code": "L", "flag_emoji": "🇬🇭", "confederation": "CAF"},
    {"name": "Panamá",                    "group_code": "L", "flag_emoji": "🇵🇦", "confederation": "CONCACAF"},
]

GROUP_STAGE_START = "2026-06-11"


def get_group_matchups() -> dict[str, list[tuple[str, str]]]:
    """Retorna os 6 confrontos round-robin de cada grupo."""
    groups: dict[str, list[str]] = {}
    for t in TEAMS:
        groups.setdefault(t["group_code"], []).append(t["name"])

    matchups = {}
    for g, teams in groups.items():
        # Ordem padrão FIFA: MD1=(0v1,2v3), MD2=(0v2,1v3), MD3=(0v3,1v2)
        ordered = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
        matchups[g] = [(teams[a], teams[b]) for a, b in ordered]
    return matchups


def seed_teams(client) -> dict[str, int]:
    """Insere as 48 seleções e retorna {name: id}."""
    result = client.table("teams").upsert(TEAMS, on_conflict="name").execute()
    all_teams = client.table("teams").select("id, name").execute()
    return {t["name"]: t["id"] for t in all_teams.data}


def seed_matches(client, team_ids: dict[str, int]) -> None:
    """Insere os 72 jogos da fase de grupos se ainda não existirem."""
    existing = client.table("matches").select("id").eq("stage", "group").execute()
    if existing.data:
        return  # já seeded

    matchups = get_group_matchups()
    records = []
    match_num = 1
    for group_code in sorted(matchups.keys()):
        for home_name, away_name in matchups[group_code]:
            records.append({
                "stage": "group",
                "group_code": group_code,
                "match_number": match_num,
                "home_team_id": team_ids[home_name],
                "away_team_id": team_ids[away_name],
            })
            match_num += 1

    client.table("matches").insert(records).execute()


def run_seed(client) -> None:
    """Executa seed completo: times + jogos da fase de grupos."""
    team_ids = seed_teams(client)
    seed_matches(client, team_ids)
