from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class TarefaCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    prioridade: str = "Média"
    data_vencimento: Optional[datetime] = None
    tags: Optional[List[str]] = None
    atribuido_a_id: Optional[int] = None  # só tem efeito se quem cria for admin de um grupo


class TarefaUpdate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    prioridade: str
    data_vencimento: Optional[datetime] = None
    tags: Optional[List[str]] = None
    atribuido_a_id: Optional[int] = None  # só tem efeito se quem edita for admin de um grupo


class TarefaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descricao: Optional[str] = None
    status: str
    prioridade: str
    data_vencimento: Optional[datetime] = None
    tags: Optional[List[str]] = None
    usuario_id: int
    atribuido_a_id: Optional[int] = None
    atribuido_a_username: Optional[str] = None
    grupo_id: Optional[int] = None


class GrupoCreate(BaseModel):
    nome: str


class GrupoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    codigo_convite: str


class EntrarGrupoRequest(BaseModel):
    codigo_convite: str


class MembroResponse(BaseModel):
    id: int
    username: str
    papel: str


class AlterarPapelRequest(BaseModel):
    papel: str
