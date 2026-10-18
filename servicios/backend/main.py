from fastapi import FastAPI, HTTPException
from database import engine, SessionLocal
from models import Base, Tarea
from schemas import TareaCrear, ResultadoTarea

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.get("/")
def inicio():
    return {
        "servicio": "IAM Secure Platform API",
        "estado": "funcionando"
    }


@app.get("/tasks")
def obtener_tareas():
    db = SessionLocal()

    try:
        tareas = db.query(Tarea).all()

        return {
            "tareas": [
                {
                    "id": tarea.id,
                    "tipo": tarea.tipo,
                    "objetivo": tarea.objetivo,
                    "estado": tarea.estado,
                    "resultado": tarea.resultado
                }
                for tarea in tareas
            ]
        }

    finally:
        db.close()

@app.post("/tasks")
def crear_tarea(tarea: TareaCrear):
    db = SessionLocal()

    try:
        nueva_tarea = Tarea(
            tipo=tarea.tipo,
            objetivo=tarea.objetivo,
            estado="pendiente"
        )

        db.add(nueva_tarea)
        db.commit()
        db.refresh(nueva_tarea)

        return {
                 "id": nueva_tarea.id,
                 "tipo": nueva_tarea.tipo,
                 "objetivo": nueva_tarea.objetivo,
                 "estado": nueva_tarea.estado,
                 "resultado": nueva_tarea.resultado
        }

    finally:
        db.close()

@app.put("/tasks/{task_id}/status/{nuevo_estado}")
def actualizar_estado(task_id: int, nuevo_estado: str):
    db = SessionLocal()

    try:
        tarea = db.query(Tarea).filter(Tarea.id == task_id).first()

        if tarea is None:
            raise HTTPException(
                status_code=404,
                detail="Tarea no encontrada"
            )

        tarea.estado = nuevo_estado

        db.commit()
        db.refresh(tarea)

        return {
            "mensaje": "Estado actualizado correctamente",
            "id": tarea.id,
            "estado": tarea.estado
        }

    finally:
        db.close()


@app.put("/tasks/{task_id}/resultado")
def guardar_resultado(task_id: int, datos: ResultadoTarea):
    db = SessionLocal()

    try:
        tarea = db.query(Tarea).filter(Tarea.id == task_id).first()

        if tarea is None:
            raise HTTPException(
                status_code=404,
                detail="Tarea no encontrada"
            )

        tarea.resultado = datos.resultado

        db.commit()
        db.refresh(tarea)

        return {
            "mensaje": "Resultado guardado correctamente",
            "id": tarea.id,
            "resultado": tarea.resultado
        }

    finally:
        db.close()