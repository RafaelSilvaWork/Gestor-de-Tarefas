from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from .database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    tarefas = relationship("Tarefa", back_populates="usuario", cascade="all, delete-orphan")


class Tarefa(Base):
    __tablename__ = "tarefas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True, nullable=False)
    descricao = Column(String, nullable=True)
    status = Column(String, default="Pendente")
    prioridade = Column(String, default="Média")
    data_vencimento = Column(DateTime, nullable=True)
    tags = Column(JSON, nullable=True)  # lista de strings, ex: ["Vendas", "Cliente-X"]
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    usuario = relationship("Usuario", back_populates="tarefas")
