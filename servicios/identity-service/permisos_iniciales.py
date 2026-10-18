"""Vistas iniciales de nuevos líderes; la grilla administra cambios posteriores."""
from sqlalchemy import text

VISTAS_POR_ROL = {
    "LIDER_FACTURACION": (
        "facturacion.aprobaciones.consultar",
        "facturacion.pagos.consultar",
        "facturacion.impuestos.consultar",
    ),
    "LIDER_LOGISTICA": (
        "logistica.despachos.consultar",
        "logistica.entregas.consultar",
        "logistica.inventario.consultar",
    ),
    "LIDER_GESTION_HUMANA": (
        "gestion_humana.colaboradores.consultar",
        "gestion_humana.novedades.consultar",
        "gestion_humana.vacaciones.consultar",
    ),
}

def asignar_vistas_iniciales(conexion, usuario_id, compania_id, rol, actor_id):
    """Dentro de la transacción de creación. Nunca reactivar una concesión existente."""
    codigos = VISTAS_POR_ROL.get(rol, ())
    if not codigos:
        return []
    if compania_id is None:
        raise ValueError("Un líder requiere compañía para sus vistas iniciales.")
    conexion.execute(text("""
        INSERT INTO permisos_usuario_compania(
            usuario_id, compania_id, codigo, habilitado, version, modificado_por)
        VALUES (:uid, :cid, :codigo, TRUE, 1, :actor)
        ON CONFLICT (usuario_id, compania_id, codigo) DO NOTHING
    """), [{"uid": usuario_id, "cid": compania_id, "codigo": codigo, "actor": actor_id}
           for codigo in codigos])
    return list(codigos)
