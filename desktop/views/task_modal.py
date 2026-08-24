from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QComboBox, QPushButton, QFrame, QMessageBox,
)


class TaskModal(QDialog):
    """Modal de criar/editar tarefa. Passe `tarefa` para pré-popular (modo edição)."""

    def __init__(self, parent=None, tarefa=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setFixedWidth(520)
        self._modo_edicao = tarefa is not None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("ModalCard")
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(4)

        cabecalho = QHBoxLayout()
        titulo_modal = QLabel("Editar Tarefa" if self._modo_edicao else "Nova Tarefa")
        titulo_modal.setObjectName("ModalTitle")
        cabecalho.addWidget(titulo_modal)
        cabecalho.addStretch()
        btn_fechar = QPushButton("✕")
        btn_fechar.setObjectName("ModalClose")
        btn_fechar.setCursor(Qt.PointingHandCursor)
        btn_fechar.setFixedSize(28, 28)
        btn_fechar.clicked.connect(self.reject)
        cabecalho.addWidget(btn_fechar)
        layout.addLayout(cabecalho)
        layout.addSpacing(16)

        layout.addWidget(self._label_campo("TÍTULO"))
        self.input_titulo = QLineEdit()
        self.input_titulo.setObjectName("ModalInput")
        self.input_titulo.setPlaceholderText("Ex: Revisar proposta comercial")
        layout.addWidget(self.input_titulo)
        layout.addSpacing(14)

        layout.addWidget(self._label_campo("DESCRIÇÃO"))
        self.input_descricao = QTextEdit()
        self.input_descricao.setObjectName("ModalInput")
        self.input_descricao.setPlaceholderText("Detalhes opcionais sobre a tarefa...")
        self.input_descricao.setFixedHeight(90)
        layout.addWidget(self.input_descricao)
        layout.addSpacing(14)

        layout.addWidget(self._label_campo("PRIORIDADE"))
        self.combo_prioridade = QComboBox()
        self.combo_prioridade.setObjectName("ModalInput")
        self.combo_prioridade.addItems(["Baixa", "Média", "Alta", "Urgente"])
        layout.addWidget(self.combo_prioridade)

        if tarefa:
            self.input_titulo.setText(tarefa.get("titulo", ""))
            self.input_descricao.setPlainText(tarefa.get("descricao") or "")
            idx = self.combo_prioridade.findText(tarefa.get("prioridade", "Média"))
            if idx >= 0:
                self.combo_prioridade.setCurrentIndex(idx)

        botoes = QHBoxLayout()
        botoes.setContentsMargins(0, 24, 0, 0)
        botoes.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("ModalBtnSecondary")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)

        btn_salvar = QPushButton("Salvar Tarefa")
        btn_salvar.setObjectName("AddButton")
        btn_salvar.setCursor(Qt.PointingHandCursor)
        btn_salvar.clicked.connect(self._validar_e_aceitar)

        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_salvar)
        layout.addLayout(botoes)

        self.input_titulo.returnPressed.connect(self._validar_e_aceitar)

    def _label_campo(self, texto):
        lbl = QLabel(texto)
        lbl.setObjectName("ModalFieldLabel")
        return lbl

    def _validar_e_aceitar(self):
        if not self.input_titulo.text().strip():
            QMessageBox.warning(self, "Aviso", "O título da tarefa não pode estar vazio!")
            return
        self.accept()

    def dados(self):
        return {
            "titulo": self.input_titulo.text().strip(),
            "descricao": self.input_descricao.toPlainText().strip(),
            "prioridade": self.combo_prioridade.currentText(),
        }
