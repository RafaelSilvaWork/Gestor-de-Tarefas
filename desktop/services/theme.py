"""Paleta e helpers de cor compartilhados pelo app (spec de design premium)."""

# --- Primárias / secundárias ---
INDIGO = "#6366f1"
MAGENTA = "#ec4899"
TEAL = "#14b8a6"
VIOLETA = "#7c3aed"
LARANJA = "#f97316"
ROSA_CLARO = "#f472b6"

# --- Background & texto ---
BG = "#0f172a"
BG_2 = "#1e293b"
CARD_BG_A = "#1a2847"
CARD_BG_B = "#1e293b"
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#cbd5e1"
TEXT_MUTED = "#94a3b8"
BORDER = "#334155"

# --- Prioridades / status ---
PRIORIDADES = {
    "Urgente": "#ef4444",
    "Alta": "#f97316",
    "Média": "#eab308",
    "Baixa": "#14b8a6",
}
COMPLETA = "#10b981"


def rgba(hex_color, alpha):
    """
    Converte "#RRGGBB" para "rgba(r, g, b, a)".

    Qt Style Sheets interpretam hex de 8 dígitos como #AARRGGBB (alpha
    primeiro) — diferente do #RRGGBBAA do CSS3. Usar hex+alpha "solto"
    (ex: f"{cor}33") dá cor errada silenciosamente. rgba() evita essa
    ambiguidade.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"
