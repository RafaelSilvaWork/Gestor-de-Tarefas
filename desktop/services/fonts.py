"""
Carrega as fontes embutidas do app (arquivos em desktop/assets/fonts) via
QFontDatabase e devolve os nomes de família reais registrados, para usar no
QSS (ex: font-family: '{fontes["poppins_bold"]}').
"""
import os

from PyQt5.QtGui import QFontDatabase

_ARQUIVOS = {
    "poppins_bold": "Poppins-Bold.ttf",
    "poppins_semibold": "Poppins-SemiBold.ttf",
    "poppins_regular": "Poppins-Regular.ttf",
    "inter": "Inter-Variable.ttf",
    "jetbrains_mono": "JetBrainsMono-Variable.ttf",
}

_FALLBACK = "Segoe UI"


def carregar_fontes(fonts_dir):
    familias = {}
    for chave, nome_arquivo in _ARQUIVOS.items():
        caminho = os.path.join(fonts_dir, nome_arquivo)
        font_id = QFontDatabase.addApplicationFont(caminho)
        if font_id == -1:
            familias[chave] = _FALLBACK
            continue
        nomes = QFontDatabase.applicationFontFamilies(font_id)
        familias[chave] = nomes[0] if nomes else _FALLBACK
    return familias
