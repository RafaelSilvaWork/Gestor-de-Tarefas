"""
Sobe o backend (FastAPI) embutido no próprio processo do app desktop, em uma
thread separada, para que o usuário final baixe e rode um único executável.
"""
import socket
import threading
import time


def porta_disponivel(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


class ServidorEmbutido(threading.Thread):
    """
    Roda um `uvicorn.Server` em background. O uvicorn, ao falhar em subir o
    socket (porta ocupada), captura o OSError internamente e chama
    ``sys.exit()`` em vez de propagar a exceção — por isso a checagem de
    porta livre é feita ANTES de instanciar esta classe (veja
    `porta_disponivel`), e não depende de capturar esse erro aqui dentro.
    """

    def __init__(self, app, host: str = "127.0.0.1", port: int = 8000):
        super().__init__(daemon=True)
        import uvicorn

        self._config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        self.server = uvicorn.Server(self._config)
        self.erro = None

    def run(self):
        try:
            self.server.run()
        except SystemExit:
            if self.erro is None:
                self.erro = RuntimeError(
                    "O servidor local encerrou inesperadamente durante a inicialização."
                )
        except Exception as e:
            self.erro = e

    def aguardar_pronto(self, timeout: float = 10.0) -> bool:
        inicio = time.time()
        while time.time() - inicio < timeout:
            if self.erro is not None:
                return False
            if self.server.started:
                return True
            time.sleep(0.05)
        return False

    def parar(self):
        self.server.should_exit = True
        self.join(timeout=5)
