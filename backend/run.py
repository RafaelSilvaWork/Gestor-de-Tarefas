"""
Ponto de entrada usado para empacotar o backend como executável (PyInstaller).

Diferente de `app.security` (que falha alto se SECRET_KEY não existir, para
forçar boas práticas em desenvolvimento), este launcher gera um .env com uma
chave aleatória automaticamente caso um usuário final apenas baixe e execute
o .exe, sem precisar configurar nada manualmente.
"""
import os
import secrets
import sys


def _diretorio_base():
    # Ao rodar como .exe (PyInstaller), usa a pasta onde o executável está;
    # ao rodar a partir do código-fonte, usa a pasta deste arquivo.
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _garantir_env(base_dir):
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        return

    chave = secrets.token_hex(32)
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"SECRET_KEY={chave}\n")
    print(f"[setup] Arquivo .env criado automaticamente em: {env_path}")


def main():
    base_dir = _diretorio_base()
    os.chdir(base_dir)  # garante que tarefas.db e .env fiquem ao lado do executável
    _garantir_env(base_dir)

    import uvicorn
    from app.main import app

    print("Gestor de Tarefas - API")
    print("Documentação interativa: http://127.0.0.1:8000/docs")
    print("Mantenha esta janela aberta enquanto usa o aplicativo desktop.")
    print()

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
