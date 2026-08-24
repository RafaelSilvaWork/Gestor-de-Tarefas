from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QFrame
from PyQt5.QtCore import Qt
import requests
from services.api_client import registrar_usuario

CARD_MARGINS = (32, 28, 32, 28)


class RegisterWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Criar Nova Conta")
        self.setFixedSize(360, 320)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("AuthCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(*CARD_MARGINS)
        lay.setSpacing(10)

        title = QLabel("Criar Conta")
        title.setObjectName("ModalTitle")
        subtitle = QLabel("Preencha os dados para se cadastrar")
        subtitle.setObjectName("AppSubtitle")
        lay.addWidget(title)
        lay.addWidget(subtitle)
        lay.addSpacing(10)

        self.u = QLineEdit()
        self.u.setPlaceholderText("Novo usuário")
        self.p = QLineEdit()
        self.p.setPlaceholderText("Senha")
        self.p.setEchoMode(QLineEdit.Password)
        self.p.returnPressed.connect(self.fazer_cadastro)

        lay.addWidget(self.u)
        lay.addWidget(self.p)
        lay.addSpacing(6)

        self.btn_cadastrar = QPushButton("CADASTRAR")
        self.btn_cadastrar.setObjectName("BtnPrimary")
        self.btn_cadastrar.setCursor(Qt.PointingHandCursor)
        lay.addWidget(self.btn_cadastrar)

        outer.addWidget(card)

        self.btn_cadastrar.clicked.connect(self.fazer_cadastro)

    def fazer_cadastro(self):
        user = self.u.text().strip()
        pwd = self.p.text().strip()

        if not user or not pwd:
            QMessageBox.warning(self, "Aviso", "Preencha todos os campos!")
            return

        if registrar_usuario(user, pwd):
            QMessageBox.information(self, "Sucesso", "Conta criada com sucesso! Faça login.")
            self.accept()
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível criar a conta (usuário já existe?).")


class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Acesso ao Sistema")
        self.setFixedSize(360, 360)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("AuthCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(*CARD_MARGINS)
        lay.setSpacing(10)

        title = QLabel("Gestor de Tarefas")
        title.setObjectName("ModalTitle")
        subtitle = QLabel("Entre com sua conta para continuar")
        subtitle.setObjectName("AppSubtitle")
        lay.addWidget(title)
        lay.addWidget(subtitle)
        lay.addSpacing(14)

        self.u = QLineEdit()
        self.u.setPlaceholderText("Usuário")
        self.u.returnPressed.connect(self.auth)
        self.p = QLineEdit()
        self.p.setPlaceholderText("Senha")
        self.p.setEchoMode(QLineEdit.Password)
        self.p.returnPressed.connect(self.auth)

        lay.addWidget(self.u)
        lay.addWidget(self.p)
        lay.addSpacing(6)

        self.btn_login = QPushButton("ENTRAR")
        self.btn_login.setObjectName("BtnPrimary")
        self.btn_login.setCursor(Qt.PointingHandCursor)

        self.btn_registro = QPushButton("CRIAR NOVA CONTA")
        self.btn_registro.setObjectName("BtnSecondary")
        self.btn_registro.setCursor(Qt.PointingHandCursor)

        lay.addWidget(self.btn_login)
        lay.addWidget(self.btn_registro)

        outer.addWidget(card)

        self.btn_login.clicked.connect(self.auth)
        self.btn_registro.clicked.connect(self.abrir_registro)
        self.token = None

    def auth(self):
        try:
            r = requests.post("http://127.0.0.1:8000/token", data={"username": self.u.text(), "password": self.p.text()})
            if r.status_code == 200:
                self.token = r.json()["access_token"]
                self.accept()
            else:
                QMessageBox.critical(self, "Erro", "Usuário ou senha inválidos")
        except Exception as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

    def abrir_registro(self):
        reg_win = RegisterWindow()
        reg_win.exec_()
