from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
)

from services.theme import PRIORIDADES, INDIGO, rgba


class TaskCard(QFrame):
    """
    Card de tarefa no estilo Linear/Superhuman. QSS cuida do visual estático
    (gradiente, borda, radius); o hover (elevação via glow + revelar ações) é
    feito em código com QGraphicsDropShadowEffect animado, já que QSS não tem
    transform/box-shadow.
    """

    concluir_clicado = pyqtSignal(int)
    editar_clicado = pyqtSignal(int)
    excluir_clicado = pyqtSignal(int)

    def __init__(self, tarefa, parent=None):
        super().__init__(parent)
        self.tarefa_id = tarefa["id"]
        self.setObjectName("TaskCard")
        self.setAttribute(Qt.WA_Hover, True)

        self._sombra = QGraphicsDropShadowEffect(self)
        self._sombra.setBlurRadius(20)
        self._sombra.setOffset(0, 8)
        self._sombra.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(self._sombra)

        self._anim_blur = QPropertyAnimation(self._sombra, b"blurRadius")
        self._anim_blur.setDuration(300)
        self._anim_blur.setEasingCurve(QEasingCurve.OutCubic)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 16, 18)
        layout.setSpacing(16)

        concluida = tarefa.get("status") == "Concluído"

        self.checkbox = QPushButton()
        self.checkbox.setObjectName("TaskCheckbox")
        self.checkbox.setCheckable(True)
        self.checkbox.setChecked(concluida)
        self.checkbox.setFixedSize(24, 24)
        self.checkbox.setCursor(Qt.PointingHandCursor)
        self.checkbox.clicked.connect(lambda: self.concluir_clicado.emit(self.tarefa_id))
        layout.addWidget(self.checkbox, alignment=Qt.AlignTop)

        corpo = QVBoxLayout()
        corpo.setSpacing(6)

        titulo_lbl = QLabel(tarefa["titulo"])
        titulo_lbl.setObjectName("TaskTitle")
        titulo_lbl.setProperty("concluida", concluida)
        titulo_lbl.setWordWrap(True)
        corpo.addWidget(titulo_lbl)

        descricao = tarefa.get("descricao") or ""
        if descricao:
            desc_lbl = QLabel(descricao)
            desc_lbl.setObjectName("TaskDesc")
            desc_lbl.setWordWrap(True)
            corpo.addWidget(desc_lbl)

        linha_meta = QHBoxLayout()
        linha_meta.setSpacing(10)

        prioridade = tarefa.get("prioridade", "Média")
        cor_prioridade = PRIORIDADES.get(prioridade, INDIGO)
        badge = QLabel(prioridade.upper())
        badge.setObjectName("PriorityBadge")
        badge.setStyleSheet(
            f"background-color: {rgba(cor_prioridade, 0.2)};"
            f"color: {cor_prioridade};"
            f"border: 1px solid {rgba(cor_prioridade, 0.4)};"
        )
        linha_meta.addWidget(badge)

        status_lbl = QLabel("✓ CONCLUÍDA" if concluida else "PENDENTE")
        status_lbl.setObjectName("StatusBadge")
        status_lbl.setProperty("concluida", concluida)
        linha_meta.addWidget(status_lbl)

        linha_meta.addStretch()
        corpo.addLayout(linha_meta)

        layout.addLayout(corpo, stretch=1)

        acoes = QHBoxLayout()
        acoes.setSpacing(6)
        self.btn_editar = QPushButton("✎")
        self.btn_editar.setObjectName("TaskAction")
        self.btn_editar.setToolTip("Editar tarefa")
        self.btn_editar.clicked.connect(lambda: self.editar_clicado.emit(self.tarefa_id))

        self.btn_excluir = QPushButton("🗑")
        self.btn_excluir.setObjectName("TaskAction")
        self.btn_excluir.setToolTip("Excluir tarefa")
        self.btn_excluir.clicked.connect(lambda: self.excluir_clicado.emit(self.tarefa_id))

        for b in (self.btn_editar, self.btn_excluir):
            b.setFixedSize(30, 30)
            b.setCursor(Qt.PointingHandCursor)
            acoes.addWidget(b)

        self._acoes_widget = QWidget()
        self._acoes_widget.setLayout(acoes)
        self._opacidade_acoes = QGraphicsOpacityEffect(self._acoes_widget)
        self._opacidade_acoes.setOpacity(0.55)
        self._acoes_widget.setGraphicsEffect(self._opacidade_acoes)
        self._anim_opacidade = QPropertyAnimation(self._opacidade_acoes, b"opacity")
        self._anim_opacidade.setDuration(200)

        layout.addWidget(self._acoes_widget, alignment=Qt.AlignTop)

    def enterEvent(self, event):
        self.setProperty("hover", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self._animar_para(blur=36, opacidade=1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self._animar_para(blur=20, opacidade=0.55)
        super().leaveEvent(event)

    def _animar_para(self, blur, opacidade):
        self._anim_blur.stop()
        self._anim_blur.setStartValue(self._sombra.blurRadius())
        self._anim_blur.setEndValue(blur)
        self._anim_blur.start()

        self._anim_opacidade.stop()
        self._anim_opacidade.setStartValue(self._opacidade_acoes.opacity())
        self._anim_opacidade.setEndValue(opacidade)
        self._anim_opacidade.start()
