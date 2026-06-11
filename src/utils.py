"""Helpers de renderização visual — bandeiras e times."""

# Bandeiras de subdivisão (England, Scotland) precisam de código especial
_SUBDIVISION_FLAGS = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿": "gb-eng",
    "🏴󠁧󠁢󠁳󠁣󠁴󠁿": "gb-sct",
    "🏴󠁧󠁢󠁷󠁬󠁳󠁿": "gb-wls",
}


def _emoji_to_code(emoji: str) -> str:
    """Converte emoji de bandeira (🇧🇷) para código ISO lowercase (br)."""
    if emoji in _SUBDIVISION_FLAGS:
        return _SUBDIVISION_FLAGS[emoji]
    code = "".join(
        chr(ord(c) - 0x1F1A5)
        for c in emoji
        if "\U0001F1E6" <= c <= "\U0001F1FF"
    ).lower()
    return code if len(code) == 2 else ""


_SUPPORTED_WIDTHS = [20, 40, 80, 160, 320, 640, 1280, 2560]


def _snap_width(size: int) -> int:
    return min(_SUPPORTED_WIDTHS, key=lambda w: abs(w - size))


def flag_img(emoji: str, size: int = 20) -> str:
    """Retorna tag <img> da bandeira via flagcdn.com."""
    code = _emoji_to_code(emoji)
    if not code:
        return emoji
    w = _snap_width(size)
    h = int(size * 0.75)
    return (
        f'<img src="https://flagcdn.com/w{w}/{code}.png" '
        f'style="height:{h}px;vertical-align:middle;'
        f'border-radius:2px;margin-right:5px">'
    )


def team_html(emoji: str, name: str, size: int = 24, bold: bool = False) -> str:
    """Retorna HTML com bandeira + nome do time."""
    tag = "strong" if bold else "span"
    return f'{flag_img(emoji, size)}<{tag}>{name}</{tag}>'
