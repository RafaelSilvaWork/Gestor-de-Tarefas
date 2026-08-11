from typing import Optional

from pydantic import BaseModel, ConfigDict


class TarefaCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    prioridade: str = "Média"


class TarefaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    descricao: Optional[str] = None
    status: str
    prioridade: str
