from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel


class EmptyState(QWidget):
    def __init__(self, titulo, descricao, icone="🗂️", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 60, 32, 60)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        icone_lbl = QLabel(icone)
        icone_lbl.setObjectName("EmptyIcon")
        icone_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icone_lbl)
        layout.addSpacing(12)

        titulo_lbl = QLabel(titulo)
        titulo_lbl.setObjectName("EmptyTitle")
        titulo_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo_lbl)

        desc_lbl = QLabel(descricao)
        desc_lbl.setObjectName("EmptyDesc")
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setMaximumWidth(360)
        layout.addWidget(desc_lbl, alignment=Qt.AlignHCenter)
