import sys
import os
from PyQt5.QtWidgets import QApplication, QDialog

if getattr(sys, "frozen", False):
    # Executável gerado pelo PyInstaller: os arquivos de código ficam em
    # sys._MEIPASS (modo --onefile) em vez de ao lado deste script.
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from views.login_window import LoginWindow
from views.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    style_path = os.path.join(BASE_DIR, "assets", "styles.qss")
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Aviso: Arquivo assets/styles.qss não foi encontrado!")

    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        win = MainWindow(token=login.token)
        win.show()
        sys.exit(app.exec_())
