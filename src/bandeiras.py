"""Mapeamento time (inglês, chave ML) → emoji de bandeira e nome em PT-BR."""

BANDEIRAS: dict[str, str] = {
    # Grupo A
    "Mexico":                  "🇲🇽",
    "South Africa":            "🇿🇦",
    "South Korea":             "🇰🇷",
    "Czech Republic":          "🇨🇿",
    # Grupo B
    "Canada":                  "🇨🇦",
    "Bosnia and Herzegovina":  "🇧🇦",
    "Qatar":                   "🇶🇦",
    "Switzerland":             "🇨🇭",
    # Grupo C
    "Brazil":                  "🇧🇷",
    "Morocco":                 "🇲🇦",
    "Haiti":                   "🇭🇹",
    "Scotland":                "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    # Grupo D
    "United States":           "🇺🇸",
    "Paraguay":                "🇵🇾",
    "Australia":               "🇦🇺",
    "Turkey":                  "🇹🇷",
    # Grupo E
    "Germany":                 "🇩🇪",
    "Curaçao":                 "🇨🇼",
    "Ivory Coast":             "🇨🇮",
    "Ecuador":                 "🇪🇨",
    # Grupo F
    "Netherlands":             "🇳🇱",
    "Japan":                   "🇯🇵",
    "Sweden":                  "🇸🇪",
    "Tunisia":                 "🇹🇳",
    # Grupo G
    "Belgium":                 "🇧🇪",
    "Egypt":                   "🇪🇬",
    "Iran":                    "🇮🇷",
    "New Zealand":             "🇳🇿",
    # Grupo H
    "Spain":                   "🇪🇸",
    "Cape Verde":              "🇨🇻",
    "Saudi Arabia":            "🇸🇦",
    "Uruguay":                 "🇺🇾",
    # Grupo I
    "France":                  "🇫🇷",
    "Senegal":                 "🇸🇳",
    "Iraq":                    "🇮🇶",
    "Norway":                  "🇳🇴",
    # Grupo J
    "Argentina":               "🇦🇷",
    "Algeria":                 "🇩🇿",
    "Austria":                 "🇦🇹",
    "Jordan":                  "🇯🇴",
    # Grupo K
    "Portugal":                "🇵🇹",
    "DR Congo":                "🇨🇩",
    "Uzbekistan":              "🇺🇿",
    "Colombia":                "🇨🇴",
    # Grupo L
    "England":                 "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Croatia":                 "🇭🇷",
    "Ghana":                   "🇬🇭",
    "Panama":                  "🇵🇦",
}

# Nomes em PT-BR alinhados com o banco do bolão (Supabase teams.name)
NOMES_PTBR: dict[str, str] = {
    "Mexico":                  "México",
    "South Africa":            "África do Sul",
    "South Korea":             "Coreia do Sul",
    "Czech Republic":          "República Checa",
    "Canada":                  "Canadá",
    "Bosnia and Herzegovina":  "Bósnia e Herzegovina",
    "Qatar":                   "Catar",
    "Switzerland":             "Suíça",
    "Brazil":                  "Brasil",
    "Morocco":                 "Marrocos",
    "Haiti":                   "Haiti",
    "Scotland":                "Escócia",
    "United States":           "Estados Unidos",
    "Paraguay":                "Paraguai",
    "Australia":               "Austrália",
    "Turkey":                  "Turquia",
    "Germany":                 "Alemanha",
    "Curaçao":                 "Curaçau",
    "Ivory Coast":             "Costa do Marfim",
    "Ecuador":                 "Equador",
    "Netherlands":             "Países Baixos",
    "Japan":                   "Japão",
    "Sweden":                  "Suécia",
    "Tunisia":                 "Tunísia",
    "Belgium":                 "Bélgica",
    "Egypt":                   "Egito",
    "Iran":                    "Irã",
    "New Zealand":             "Nova Zelândia",
    "Spain":                   "Espanha",
    "Cape Verde":              "Cabo Verde",
    "Saudi Arabia":            "Arábia Saudita",
    "Uruguay":                 "Uruguai",
    "France":                  "França",
    "Senegal":                 "Senegal",
    "Iraq":                    "Iraque",
    "Norway":                  "Noruega",
    "Argentina":               "Argentina",
    "Algeria":                 "Argélia",
    "Austria":                 "Áustria",
    "Jordan":                  "Jordânia",
    "Portugal":                "Portugal",
    "DR Congo":                "Rep. Dem. do Congo",
    "Uzbekistan":              "Uzbequistão",
    "Colombia":                "Colômbia",
    "England":                 "Inglaterra",
    "Croatia":                 "Croácia",
    "Ghana":                   "Gana",
    "Panama":                  "Panamá",
}


def traduzir(name: str) -> str:
    """Inglês (chave ML) → PT-BR. Retorna o original se não encontrado."""
    return NOMES_PTBR.get(name, name)


def com_bandeira(name: str) -> str:
    """Emoji + nome PT-BR (para uso em texto simples)."""
    return f"{BANDEIRAS.get(name, '🏳️')} {traduzir(name)}"


def team_flag_html(name: str, size: int = 20) -> str:
    """HTML com <img> de bandeira via flagcdn.com + nome PT-BR.
    Requer unsafe_allow_html=True no st.markdown que renderizar o resultado."""
    from utils import flag_img  # lazy import — src/ precisa estar no sys.path
    emoji = BANDEIRAS.get(name, "🏳️")
    return f"{flag_img(emoji, size)}{traduzir(name)}"
