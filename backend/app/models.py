from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship

from .database import Base


class Grupo(Base):
    __tablename__ = "grupos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    codigo_convite = Column(String, unique=True, index=True, nullable=False)

    membros = relationship("Usuario", back_populates="grupo")
    tarefas = relationship("Tarefa", back_populates="grupo")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    grupo_id = Column(Integer, ForeignKey("grupos.id"), nullable=True)
    papel = Column(String, nullable=True)  # "admin" | "funcionario" | None (sem grupo)

    grupo = relationship("Grupo", back_populates="membros")
    tarefas = relationship(
        "Tarefa", back_populates="usuario", foreign_keys="Tarefa.usuario_id",
        cascade="all, delete-orphan",
    )


class Tarefa(Base):
    __tablename__ = "tarefas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True, nullable=False)
    descricao = Column(String, nullable=True)
    status = Column(String, default="Pendente")
    prioridade = Column(String, default="Média")
    data_vencimento = Column(DateTime, nullable=True)
    tags = Column(JSON, nullable=True)  # lista de strings, ex: ["Vendas", "Cliente-X"]

    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)  # quem criou
    atribuido_a_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)  # responsável pela execução
    grupo_id = Column(Integer, ForeignKey("grupos.id"), nullable=True)  # herdado do criador, se houver

    usuario = relationship("Usuario", back_populates="tarefas", foreign_keys=[usuario_id])
    atribuido_a = relationship("Usuario", foreign_keys=[atribuido_a_id])
    grupo = relationship("Grupo", back_populates="tarefas")

    @property
    def atribuido_a_username(self):
        return self.atribuido_a.username if self.atribuido_a else None
