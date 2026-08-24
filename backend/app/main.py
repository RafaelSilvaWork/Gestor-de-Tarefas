import secrets
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# Certifique-se de que os imports abaixo correspondem à estrutura da sua pasta backend/app
from .database import engine, Base, get_db, aplicar_migracoes_leves
from . import models, schemas
from .security import verify_password, get_password_hash, create_access_token, get_current_user
# Cria as tabelas no banco de dados se não existirem
Base.metadata.create_all(bind=engine)
# Adiciona colunas novas a um tarefas.db já existente (ver database.py)
aplicar_migracoes_leves()

app = FastAPI(title="Gestor de Tarefas API", version="1.0")

CODIGO_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem caracteres ambíguos (0/O, 1/I)


def _gerar_codigo_convite():
    return "".join(secrets.choice(CODIGO_ALFABETO) for _ in range(8))


def _eh_admin_de_grupo(usuario: models.Usuario) -> bool:
    return usuario.papel == "admin" and usuario.grupo_id is not None


def _tarefa_visivel_e_editavel(tarefa: models.Tarefa, usuario: models.Usuario) -> bool:
    """Responsável pela tarefa, ou admin do grupo dela."""
    if tarefa.atribuido_a_id == usuario.id:
        return True
    return _eh_admin_de_grupo(usuario) and tarefa.grupo_id == usuario.grupo_id


def _tarefa_excluivel(tarefa: models.Tarefa, usuario: models.Usuario) -> bool:
    """Excluir é ação de gestão: admin do grupo, ou dono de tarefa solo (sem grupo)."""
    if _eh_admin_de_grupo(usuario) and tarefa.grupo_id == usuario.grupo_id:
        return True
    return tarefa.grupo_id is None and tarefa.usuario_id == usuario.id


# --- ROTA DE REGISTRO DE USUÁRIO ---
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(username: str, password: str, db: Session = Depends(get_db)):
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Usuário já existe")

    hashed_password = get_password_hash(password)
    novo_usuario = models.Usuario(username=username, hashed_password=hashed_password)
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return {"msg": "Usuário criado com sucesso"}

# --- ROTA DE AUTENTICAÇÃO (TOKEN JWT) ---
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.username == form_data.username).first()
    if not usuario or not verify_password(form_data.password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": usuario.username})
    return {"access_token": access_token, "token_type": "bearer"}


# ==================== GRUPOS (equipes) ====================

# --- ROTA DE CRIAÇÃO DE GRUPO (quem cria vira admin) ---
@app.post("/grupos", response_model=schemas.GrupoResponse, status_code=status.HTTP_201_CREATED)
def criar_grupo(
    dados: schemas.GrupoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if current_user.grupo_id is not None:
        raise HTTPException(status_code=400, detail="Você já faz parte de um grupo")

    codigo = _gerar_codigo_convite()
    while db.query(models.Grupo).filter(models.Grupo.codigo_convite == codigo).first():
        codigo = _gerar_codigo_convite()

    novo_grupo = models.Grupo(nome=dados.nome, codigo_convite=codigo)
    db.add(novo_grupo)
    db.flush()

    current_user.grupo_id = novo_grupo.id
    current_user.papel = "admin"

    db.commit()
    db.refresh(novo_grupo)
    return novo_grupo

# --- ROTA DE ENTRADA EM GRUPO VIA CÓDIGO DE CONVITE ---
@app.post("/grupos/entrar", response_model=schemas.GrupoResponse)
def entrar_no_grupo(
    dados: schemas.EntrarGrupoRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if current_user.grupo_id is not None:
        raise HTTPException(status_code=400, detail="Você já faz parte de um grupo")

    codigo = dados.codigo_convite.strip().upper()
    grupo = db.query(models.Grupo).filter(models.Grupo.codigo_convite == codigo).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Código de convite inválido")

    current_user.grupo_id = grupo.id
    current_user.papel = "funcionario"

    db.commit()
    db.refresh(grupo)
    return grupo

# --- ROTA DE SAÍDA DO GRUPO ---
@app.post("/grupos/sair", status_code=status.HTTP_204_NO_CONTENT)
def sair_do_grupo(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    current_user.grupo_id = None
    current_user.papel = None
    db.commit()

# --- ROTA DE DADOS DO PRÓPRIO GRUPO ---
@app.get("/grupos/meu", response_model=schemas.GrupoResponse)
def meu_grupo(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if current_user.grupo_id is None:
        raise HTTPException(status_code=404, detail="Você não faz parte de um grupo")
    return db.query(models.Grupo).filter(models.Grupo.id == current_user.grupo_id).first()

# --- ROTA DE LISTAGEM DE MEMBROS DO GRUPO ---
@app.get("/grupos/membros", response_model=List[schemas.MembroResponse])
def listar_membros(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if current_user.grupo_id is None:
        raise HTTPException(status_code=404, detail="Você não faz parte de um grupo")
    return db.query(models.Usuario).filter(models.Usuario.grupo_id == current_user.grupo_id).all()

# --- ROTA DE ALTERAÇÃO DE PAPEL DE UM MEMBRO (só admin) ---
@app.patch("/grupos/membros/{usuario_id}/papel", response_model=schemas.MembroResponse)
def alterar_papel_membro(
    usuario_id: int,
    dados: schemas.AlterarPapelRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if not _eh_admin_de_grupo(current_user):
        raise HTTPException(status_code=403, detail="Apenas administradores podem alterar papéis")
    if dados.papel not in ("admin", "funcionario"):
        raise HTTPException(status_code=400, detail="Papel inválido")

    membro = db.query(models.Usuario).filter(
        models.Usuario.id == usuario_id,
        models.Usuario.grupo_id == current_user.grupo_id,
    ).first()
    if not membro:
        raise HTTPException(status_code=404, detail="Membro não encontrado")

    membro.papel = dados.papel
    db.commit()
    db.refresh(membro)
    return membro

# --- ROTA DE REMOÇÃO DE MEMBRO DO GRUPO (só admin) ---
@app.delete("/grupos/membros/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_membro(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    if not _eh_admin_de_grupo(current_user):
        raise HTTPException(status_code=403, detail="Apenas administradores podem remover membros")
    if usuario_id == current_user.id:
        raise HTTPException(status_code=400, detail="Use /grupos/sair para sair do grupo")

    membro = db.query(models.Usuario).filter(
        models.Usuario.id == usuario_id,
        models.Usuario.grupo_id == current_user.grupo_id,
    ).first()
    if not membro:
        raise HTTPException(status_code=404, detail="Membro não encontrado")

    membro.grupo_id = None
    membro.papel = None

    # Tarefas do grupo atribuídas a esse membro voltam para quem as criou.
    db.query(models.Tarefa).filter(
        models.Tarefa.atribuido_a_id == membro.id,
        models.Tarefa.grupo_id == current_user.grupo_id,
    ).update({"atribuido_a_id": models.Tarefa.usuario_id})

    db.commit()


# ==================== TAREFAS ====================

# --- ROTA DE LISTAGEM DE TAREFAS ---
@app.get("/tarefas", response_model=List[schemas.TarefaResponse])
def listar_tarefas(
    status: Optional[str] = None,
    prioridade: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    if _eh_admin_de_grupo(current_user):
        # Admin vê todas as tarefas do grupo, não só as próprias.
        query = db.query(models.Tarefa).filter(models.Tarefa.grupo_id == current_user.grupo_id)
    else:
        query = db.query(models.Tarefa).filter(models.Tarefa.atribuido_a_id == current_user.id)

    if status and status != "Todos":
        query = query.filter(models.Tarefa.status == status)
    if prioridade and prioridade != "Todas":
        query = query.filter(models.Tarefa.prioridade == prioridade)

    return query.all()

# --- ROTA DE CRIAÇÃO DE TAREFAS (POST) ---
@app.post("/tarefas", response_model=schemas.TarefaResponse)
def criar_tarefa(
    tarefa: schemas.TarefaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    atribuido_a_id = current_user.id

    if tarefa.atribuido_a_id and _eh_admin_de_grupo(current_user):
        membro_alvo = db.query(models.Usuario).filter(
            models.Usuario.id == tarefa.atribuido_a_id,
            models.Usuario.grupo_id == current_user.grupo_id,
        ).first()
        if not membro_alvo:
            raise HTTPException(status_code=400, detail="Usuário atribuído inválido para este grupo")
        atribuido_a_id = membro_alvo.id

    nova_tarefa = models.Tarefa(
        titulo=tarefa.titulo,
        descricao=tarefa.descricao,
        prioridade=tarefa.prioridade,
        data_vencimento=tarefa.data_vencimento,
        tags=tarefa.tags,
        status="Pendente",
        usuario_id=current_user.id,
        atribuido_a_id=atribuido_a_id,
        grupo_id=current_user.grupo_id,
    )
    db.add(nova_tarefa)
    db.commit()
    db.refresh(nova_tarefa)
    return nova_tarefa

# --- ROTA DE EDIÇÃO DE TAREFA (título, descrição, prioridade, prazo, tags e, se admin, responsável) ---
@app.put("/tarefas/{tarefa_id}", response_model=schemas.TarefaResponse)
def editar_tarefa(
    tarefa_id: int,
    dados: schemas.TarefaUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    tarefa = db.query(models.Tarefa).filter(models.Tarefa.id == tarefa_id).first()

    if not tarefa or not _tarefa_visivel_e_editavel(tarefa, current_user):
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    tarefa.titulo = dados.titulo
    tarefa.descricao = dados.descricao
    tarefa.prioridade = dados.prioridade
    tarefa.data_vencimento = dados.data_vencimento
    tarefa.tags = dados.tags

    if dados.atribuido_a_id and _eh_admin_de_grupo(current_user):
        membro_alvo = db.query(models.Usuario).filter(
            models.Usuario.id == dados.atribuido_a_id,
            models.Usuario.grupo_id == current_user.grupo_id,
        ).first()
        if not membro_alvo:
            raise HTTPException(status_code=400, detail="Usuário atribuído inválido para este grupo")
        tarefa.atribuido_a_id = membro_alvo.id

    db.commit()
    db.refresh(tarefa)
    return tarefa

# --- ROTA DE EXCLUSÃO DE TAREFA ---
@app.delete("/tarefas/{tarefa_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_tarefa(
    tarefa_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    tarefa = db.query(models.Tarefa).filter(models.Tarefa.id == tarefa_id).first()

    if not tarefa or not _tarefa_excluivel(tarefa, current_user):
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    db.delete(tarefa)
    db.commit()

# --- ROTA DE ATUALIZAÇÃO DE STATUS ---
@app.patch("/tarefas/{tarefa_id}/status", response_model=schemas.TarefaResponse)
def atualizar_status_tarefa(
    tarefa_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    tarefa = db.query(models.Tarefa).filter(models.Tarefa.id == tarefa_id).first()

    if not tarefa or not _tarefa_visivel_e_editavel(tarefa, current_user):
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    tarefa.status = status
    db.commit()
    db.refresh(tarefa)
    return tarefa
