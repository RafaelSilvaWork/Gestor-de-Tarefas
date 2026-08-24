from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class TarefaCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    prioridade: str = "Média"
    data_vencimento: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TarefaUpdate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    prioridade: str
    data_vencimento: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TarefaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descricao: Optional[str] = None
    status: str
    prioridade: str
    data_vencimento: Optional[datetime] = None
    tags: Optional[List[str]] = None
