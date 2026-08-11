import sys
import os
from PyQt5.QtWidgets import QApplication, QDialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from views.login_window import LoginWindow
from views.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "styles.qss")
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
