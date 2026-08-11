from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional

# Certifique-se de que os imports abaixo correspondem à estrutura da sua pasta backend/app
from .database import engine, Base, get_db
from . import models, schemas
from .security import verify_password, get_password_hash, create_access_token, get_current_user
# Cria as tabelas no banco de dados se não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gestor de Tarefas API", version="1.0")

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

# --- ROTA DE LISTAGEM DE TAREFAS ---
@app.get("/tarefas", response_model=List[schemas.TarefaResponse])
def listar_tarefas(
    status: Optional[str] = None,
    prioridade: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    query = db.query(models.Tarefa).filter(models.Tarefa.usuario_id == current_user.id)
    
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
    nova_tarefa = models.Tarefa(
        titulo=tarefa.titulo,
        descricao=tarefa.descricao,
        prioridade=tarefa.prioridade,
        status="Pendente",
        usuario_id=current_user.id
    )
    db.add(nova_tarefa)
    db.commit()
    db.refresh(nova_tarefa)
    return nova_tarefa

# --- ROTA DE ATUALIZAÇÃO DE STATUS ---
@app.patch("/tarefas/{tarefa_id}/status", response_model=schemas.TarefaResponse)
def atualizar_status_tarefa(
    tarefa_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    tarefa = db.query(models.Tarefa).filter(
        models.Tarefa.id == tarefa_id,
        models.Tarefa.usuario_id == current_user.id
    ).first()
    
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
    tarefa.status = status
    db.commit()
    db.refresh(tarefa)
    return tarefa