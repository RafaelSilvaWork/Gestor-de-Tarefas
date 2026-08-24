import os
import sys
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key-nao-use-em-producao")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, inspect, text


def test_aplicar_migracoes_leves_adiciona_colunas_faltantes(tmp_path):
    """
    Simula um tarefas.db criado pela versão anterior do app (sem
    data_vencimento/tags) e confirma que aplicar_migracoes_leves() adiciona
    as colunas novas sem apagar a tabela nem os dados existentes.
    """
    db_path = tmp_path / "tarefas_legado.db"
    engine_legado = create_engine(f"sqlite:///{db_path}")

    with engine_legado.begin() as conexao:
        conexao.execute(text(
            "CREATE TABLE tarefas ("
            "id INTEGER PRIMARY KEY, titulo VARCHAR, descricao VARCHAR, "
            "status VARCHAR, prioridade VARCHAR, usuario_id INTEGER)"
        ))
        conexao.execute(text(
            "INSERT INTO tarefas (id, titulo, status, prioridade, usuario_id) "
            "VALUES (1, 'Tarefa antiga', 'Pendente', 'Alta', 1)"
        ))

    import app.database as database_module
    engine_original = database_module.engine
    try:
        database_module.engine = engine_legado
        database_module.aplicar_migracoes_leves()
    finally:
        database_module.engine = engine_original

    inspetor = inspect(engine_legado)
    colunas = {c["name"] for c in inspetor.get_columns("tarefas")}
    assert "data_vencimento" in colunas
    assert "tags" in colunas

    with engine_legado.connect() as conexao:
        linha = conexao.execute(text("SELECT titulo, data_vencimento, tags FROM tarefas WHERE id = 1")).first()
    assert linha[0] == "Tarefa antiga"
    assert linha[1] is None
    assert linha[2] is None


def test_aplicar_migracoes_leves_adiciona_colunas_de_grupo(tmp_path):
    """
    Mesma ideia, mas para as colunas de grupo/papel adicionadas em usuarios
    e as de atribuição/grupo adicionadas em tarefas — sem isso, quem já tinha
    o app instalado perderia a conta e as tarefas ao atualizar.
    """
    db_path = tmp_path / "legado_grupos.db"
    engine_legado = create_engine(f"sqlite:///{db_path}")

    with engine_legado.begin() as conexao:
        conexao.execute(text(
            "CREATE TABLE usuarios ("
            "id INTEGER PRIMARY KEY, username VARCHAR, hashed_password VARCHAR)"
        ))
        conexao.execute(text(
            "INSERT INTO usuarios (id, username, hashed_password) VALUES (1, 'legado', 'hash123')"
        ))
        conexao.execute(text(
            "CREATE TABLE tarefas ("
            "id INTEGER PRIMARY KEY, titulo VARCHAR, descricao VARCHAR, "
            "status VARCHAR, prioridade VARCHAR, usuario_id INTEGER)"
        ))

    import app.database as database_module
    engine_original = database_module.engine
    try:
        database_module.engine = engine_legado
        database_module.aplicar_migracoes_leves()
    finally:
        database_module.engine = engine_original

    inspetor = inspect(engine_legado)
    colunas_usuarios = {c["name"] for c in inspetor.get_columns("usuarios")}
    assert "grupo_id" in colunas_usuarios
    assert "papel" in colunas_usuarios

    colunas_tarefas = {c["name"] for c in inspetor.get_columns("tarefas")}
    assert "atribuido_a_id" in colunas_tarefas
    assert "grupo_id" in colunas_tarefas

    with engine_legado.connect() as conexao:
        linha = conexao.execute(text("SELECT username, grupo_id, papel FROM usuarios WHERE id = 1")).first()
    assert linha[0] == "legado"
    assert linha[1] is None
    assert linha[2] is None
