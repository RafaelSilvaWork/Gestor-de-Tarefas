from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QMessageBox, QApplication,
)

from services.api_client import (
    buscar_meu_usuario, buscar_meu_grupo, criar_grupo, entrar_no_grupo, sair_do_grupo,
    buscar_membros, alterar_papel_membro, remover_membro,
)
from services.theme import INDIGO, TEAL, rgba


class TeamPage(QWidget):
    """
    Página "Equipe": sem grupo, mostra opções de criar/entrar; com grupo,
    mostra código de convite, lista de membros e controles de admin.
    `on_grupo_alterado` é chamado após qualquer mudança (criar/entrar/sair/
    promover/remover), para o MainWindow atualizar sidebar e permissões.
    """

    def __init__(self, token, on_grupo_alterado=None, parent=None):
        super().__init__(parent)
        self.token = token
        self.on_grupo_alterado = on_grupo_alterado

        self.layout_raiz = QVBoxLayout(self)
        self.layout_raiz.setContentsMargins(0, 0, 0, 0)
        self.layout_raiz.setSpacing(16)

        self.conteudo = QVBoxLayout()
        self.layout_raiz.addLayout(self.conteudo)
        self.layout_raiz.addStretch()

        self.recarregar()

    def _limpar_conteudo(self):
        while self.conteudo.count():
            item = self.conteudo.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            layout_filho = item.layout()
            if layout_filho:
                self._limpar_layout(layout_filho)

    def _limpar_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def recarregar(self):
        self._limpar_conteudo()

        self.meu_usuario = buscar_meu_usuario(self.token) or {}
        if self.meu_usuario.get("grupo_id"):
            self.meu_grupo = buscar_meu_grupo(self.token) or {}
            self._montar_com_grupo()
        else:
            self._montar_sem_grupo()

    def _card(self):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        return card, layout

    # ------------------------------------------------------------------
    # Sem grupo: criar ou entrar
    # ------------------------------------------------------------------
    def _montar_sem_grupo(self):
        card_criar, layout_criar = self._card()
        titulo = QLabel("CRIAR UM GRUPO")
        titulo.setObjectName("SectionTitle")
        layout_criar.addWidget(titulo)
        desc = QLabel("Crie uma equipe e vire administrador dela — você poderá atribuir e acompanhar as tarefas de quem entrar.")
        desc.setWordWrap(True)
        layout_criar.addWidget(desc)

        linha = QHBoxLayout()
        self.input_nome_grupo = QLineEdit()
        self.input_nome_grupo.setPlaceholderText("Nome do grupo (ex: Equipe de Vendas)")
        linha.addWidget(self.input_nome_grupo, stretch=1)
        btn_criar = QPushButton("Criar Grupo")
        btn_criar.setObjectName("BtnPrimary")
        btn_criar.setCursor(Qt.PointingHandCursor)
        btn_criar.clicked.connect(self._criar_grupo)
        linha.addWidget(btn_criar)
        layout_criar.addLayout(linha)

        self.conteudo.addWidget(card_criar)

        card_entrar, layout_entrar = self._card()
        titulo2 = QLabel("ENTRAR EM UM GRUPO")
        titulo2.setObjectName("SectionTitle")
        layout_entrar.addWidget(titulo2)
        desc2 = QLabel("Já recebeu um código de convite de alguém? Digite abaixo para entrar como funcionário.")
        desc2.setWordWrap(True)
        layout_entrar.addWidget(desc2)

        linha2 = QHBoxLayout()
        self.input_codigo = QLineEdit()
        self.input_codigo.setPlaceholderText("Código de convite (ex: AB3D9F2K)")
        linha2.addWidget(self.input_codigo, stretch=1)
        btn_entrar = QPushButton("Entrar")
        btn_entrar.setObjectName("BtnSecondary")
        btn_entrar.setCursor(Qt.PointingHandCursor)
        btn_entrar.clicked.connect(self._entrar_grupo)
        linha2.addWidget(btn_entrar)
        layout_entrar.addLayout(linha2)

        self.conteudo.addWidget(card_entrar)

    def _criar_grupo(self):
        nome = self.input_nome_grupo.text().strip()
        if not nome:
            QMessageBox.warning(self, "Aviso", "Digite um nome para o grupo.")
            return

        grupo, erro = criar_grupo(self.token, nome)
        if not grupo:
            QMessageBox.critical(self, "Erro", erro)
            return

        self.recarregar()
        if self.on_grupo_alterado:
            self.on_grupo_alterado()

    def _entrar_grupo(self):
        codigo = self.input_codigo.text().strip()
        if not codigo:
            QMessageBox.warning(self, "Aviso", "Digite o código de convite.")
            return

        grupo, erro = entrar_no_grupo(self.token, codigo)
        if not grupo:
            QMessageBox.critical(self, "Erro", erro)
            return

        self.recarregar()
        if self.on_grupo_alterado:
            self.on_grupo_alterado()

    # ------------------------------------------------------------------
    # Com grupo: código de convite + membros
    # ------------------------------------------------------------------
    def _montar_com_grupo(self):
        sou_admin = self.meu_usuario.get("papel") == "admin"
        membros = buscar_membros(self.token)

        nome_grupo_lbl = QLabel(self.meu_grupo.get("nome") or "")
        nome_grupo_lbl.setObjectName("SectionTitle")
        self.conteudo.addWidget(nome_grupo_lbl)

        if sou_admin:
            card_convite, layout_convite = self._card()
            titulo = QLabel("CÓDIGO DE CONVITE")
            titulo.setObjectName("SectionTitle")
            layout_convite.addWidget(titulo)
            desc = QLabel("Compartilhe este código com quem você quer adicionar ao grupo.")
            desc.setWordWrap(True)
            layout_convite.addWidget(desc)

            linha = QHBoxLayout()
            codigo_lbl = QLabel(self.meu_grupo.get("codigo_convite") or "")
            codigo_lbl.setObjectName("PriorityBadge")
            codigo_lbl.setStyleSheet(
                f"background-color: {rgba(INDIGO, 0.15)}; color: {INDIGO};"
                f"border: 1px solid {rgba(INDIGO, 0.4)}; font-size: 16px; padding: 8px 16px;"
            )
            linha.addWidget(codigo_lbl)
            btn_copiar = QPushButton("Copiar")
            btn_copiar.setObjectName("BtnSecondary")
            btn_copiar.setCursor(Qt.PointingHandCursor)
            btn_copiar.clicked.connect(self._copiar_codigo)
            linha.addWidget(btn_copiar)
            linha.addStretch()
            layout_convite.addLayout(linha)

            self.conteudo.addWidget(card_convite)

        card_membros, layout_membros = self._card()
        titulo_m = QLabel(f"MEMBROS ({len(membros)})")
        titulo_m.setObjectName("SectionTitle")
        layout_membros.addWidget(titulo_m)

        for membro in membros:
            layout_membros.addWidget(self._linha_membro(membro, sou_admin))

        self.conteudo.addWidget(card_membros)

        btn_sair = QPushButton("Sair do Grupo")
        btn_sair.setCursor(Qt.PointingHandCursor)
        btn_sair.clicked.connect(self._sair_grupo)
        self.conteudo.addWidget(btn_sair)

    def _linha_membro(self, membro, sou_admin):
        linha_widget = QFrame()
        linha = QHBoxLayout(linha_widget)
        linha.setContentsMargins(0, 6, 0, 6)

        nome_lbl = QLabel(membro["username"])
        linha.addWidget(nome_lbl)

        cor = INDIGO if membro["papel"] == "admin" else TEAL
        papel_lbl = QLabel(membro["papel"].upper())
        papel_lbl.setObjectName("PriorityBadge")
        papel_lbl.setStyleSheet(
            f"background-color: {rgba(cor, 0.2)}; color: {cor}; border: 1px solid {rgba(cor, 0.4)};"
        )
        linha.addWidget(papel_lbl)
        linha.addStretch()

        eh_eu_mesmo = membro["id"] == self.meu_usuario.get("id")
        if sou_admin and not eh_eu_mesmo:
            btn_alternar = QPushButton("Tornar Funcionário" if membro["papel"] == "admin" else "Tornar Admin")
            btn_alternar.setObjectName("BtnSecondary")
            btn_alternar.setCursor(Qt.PointingHandCursor)
            btn_alternar.clicked.connect(lambda _c=False, m=membro: self._alternar_papel(m))
            linha.addWidget(btn_alternar)

            btn_remover = QPushButton("Remover")
            btn_remover.setCursor(Qt.PointingHandCursor)
            btn_remover.clicked.connect(lambda _c=False, m=membro: self._remover_membro(m))
            linha.addWidget(btn_remover)

        return linha_widget

    def _copiar_codigo(self):
        QApplication.clipboard().setText(self.meu_grupo.get("codigo_convite") or "")

    def _alternar_papel(self, membro):
        novo_papel = "funcionario" if membro["papel"] == "admin" else "admin"
        if alterar_papel_membro(self.token, membro["id"], novo_papel):
            self.recarregar()
            if self.on_grupo_alterado:
                self.on_grupo_alterado()
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível alterar o papel deste membro.")

    def _remover_membro(self, membro):
        resposta = QMessageBox.question(
            self, "Remover membro",
            f'Remover "{membro["username"]}" do grupo? As tarefas atribuídas a ele voltam para quem as criou.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resposta != QMessageBox.Yes:
            return

        if remover_membro(self.token, membro["id"]):
            self.recarregar()
            if self.on_grupo_alterado:
                self.on_grupo_alterado()
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível remover este membro.")

    def _sair_grupo(self):
        resposta = QMessageBox.question(
            self, "Sair do grupo",
            "Tem certeza que deseja sair deste grupo?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resposta != QMessageBox.Yes:
            return

        if sair_do_grupo(self.token):
            self.recarregar()
            if self.on_grupo_alterado:
                self.on_grupo_alterado()
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível sair do grupo.")
