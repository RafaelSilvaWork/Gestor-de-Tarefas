from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./tarefas.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def aplicar_migracoes_leves():
    """
    Base.metadata.create_all() só cria tabelas que ainda não existem — não
    adiciona colunas novas a uma tabela já existente. Para não perder o
    tarefas.db de quem já usa o app ao adicionar uma coluna nova, checa e
    aplica ALTER TABLE ADD COLUMN quando necessário (suficiente para colunas
    nullable em SQLite; não substitui uma ferramenta como Alembic para casos
    mais complexos).
    """
    inspetor = inspect(engine)
    if "tarefas" not in inspetor.get_table_names():
        return

    colunas_existentes = {c["name"] for c in inspetor.get_columns("tarefas")}
    colunas_novas = {
        "data_vencimento": "DATETIME",
        "tags": "JSON",
    }

    with engine.begin() as conexao:
        for nome, tipo_sql in colunas_novas.items():
            if nome not in colunas_existentes:
                conexao.execute(text(f"ALTER TABLE tarefas ADD COLUMN {nome} {tipo_sql}"))
