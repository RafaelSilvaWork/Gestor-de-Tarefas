import sys
import os
import secrets
import traceback

# Em um build --windowed do PyInstaller não existe console, então
# sys.stdout/sys.stderr são None (não apenas "não é um terminal"). Várias
# bibliotecas (uvicorn incluso) presumem que sempre são objetos de arquivo
# válidos e quebram com "AttributeError: 'NoneType' object has no attribute
# ...". Substituir por um destino nulo antes de qualquer outro import evita
# essa classe inteira de erro.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

if getattr(sys, "frozen", False):
    # Executável gerado pelo PyInstaller (--onefile): o código-fonte fica
    # extraído em sys._MEIPASS; o que deve ficar ao lado do .exe (banco de
    # dados, .env) vai na pasta real do executável.
    RESOURCE_DIR = sys._MEIPASS
    WRITABLE_DIR = os.path.dirname(sys.executable)
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
    WRITABLE_DIR = RESOURCE_DIR
    # Em modo código-fonte, o pacote do backend (backend/app) mora fora da
    # pasta desktop/ — adiciona ao sys.path para "from app.main import app" funcionar.
    BACKEND_DIR = os.path.abspath(os.path.join(RESOURCE_DIR, "..", "backend"))
    sys.path.insert(0, BACKEND_DIR)

sys.path.insert(0, RESOURCE_DIR)

from views.login_window import LoginWindow
from views.main_window import MainWindow
from services.embedded_server import ServidorEmbutido, porta_disponivel
from services.fonts import carregar_fontes

HOST_API = "127.0.0.1"
PORTA_API = 8000


def _garantir_env(base_dir):
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        return
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"SECRET_KEY={secrets.token_hex(32)}\n")


def _exibir_erro_fatal(titulo, texto, erro=None):
    caixa = QMessageBox()
    caixa.setIcon(QMessageBox.Critical)
    caixa.setWindowTitle(titulo)
    caixa.setText(texto)
    if erro is not None:
        detalhes = "".join(traceback.format_exception(type(erro), erro, erro.__traceback__))
        caixa.setDetailedText(detalhes)
    caixa.setStandardButtons(QMessageBox.Ok)
    caixa.exec_()


def _iniciar_backend_embutido():
    if not porta_disponivel(HOST_API, PORTA_API):
        _exibir_erro_fatal(
            "Não foi possível iniciar",
            f"A porta {PORTA_API} já está em uso.\n\n"
            "Feche outras instâncias do Gestor de Tarefas (ou qualquer outro "
            "programa usando essa porta) e tente novamente.",
        )
        return None

    try:
        from app.main import app as backend_app
        servidor = ServidorEmbutido(backend_app, host=HOST_API, port=PORTA_API)
        servidor.start()
    except Exception as e:
        _exibir_erro_fatal(
            "Não foi possível iniciar",
            "Falha ao carregar o servidor local do Gestor de Tarefas.\n"
            "O aplicativo será fechado.",
            erro=e,
        )
        return None

    if not servidor.aguardar_pronto(timeout=10):
        _exibir_erro_fatal(
            "Não foi possível iniciar",
            "O servidor local do Gestor de Tarefas não respondeu a tempo.\n"
            "O aplicativo será fechado.",
            erro=servidor.erro,
        )
        return None

    return servidor


if __name__ == "__main__":
    os.chdir(WRITABLE_DIR)
    _garantir_env(WRITABLE_DIR)

    app = QApplication(sys.argv)

    # Precisa carregar as fontes ANTES de aplicar o stylesheet, senão o QSS
    # referencia famílias ainda não registradas e cai no fallback do sistema.
    carregar_fontes(os.path.join(RESOURCE_DIR, "assets", "fonts"))

    style_path = os.path.join(RESOURCE_DIR, "assets", "styles.qss")
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Aviso: Arquivo assets/styles.qss não foi encontrado!")

    servidor = _iniciar_backend_embutido()
    if servidor is None:
        sys.exit(1)

    app.aboutToQuit.connect(servidor.parar)

    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        win = MainWindow(token=login.token)
        win.show()
        sys.exit(app.exec_())
