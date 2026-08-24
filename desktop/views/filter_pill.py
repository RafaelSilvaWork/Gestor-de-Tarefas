from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton


class FilterPill(QPushButton):
    def __init__(self, texto, valor=None, ativo=False):
        super().__init__(texto)
        self.valor = valor if valor is not None else texto
        self.setObjectName("FilterPill")
        self.setCheckable(True)
        self.setChecked(ativo)
        self.setCursor(Qt.PointingHandCursor)
