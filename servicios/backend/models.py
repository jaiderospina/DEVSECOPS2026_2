from sqlalchemy import Column, Integer, String, Text
from database import Base


class Tarea(Base):
    __tablename__ = "tareas"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, nullable=False)
    objetivo = Column(String, nullable=False)
    estado = Column(String, default="pendiente")
    resultado = Column(Text, nullable=True)