from pydantic import BaseModel


class TareaCrear(BaseModel):
    tipo: str
    objetivo: str


class ResultadoTarea(BaseModel):
    resultado: str