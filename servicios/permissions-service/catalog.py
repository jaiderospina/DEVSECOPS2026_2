"""Catálogo cerrado de vistas académicas, no operaciones financieras reales."""
CATALOG = (
    ("facturacion.aprobaciones.consultar", "LIDER_FACTURACION", "Facturación", "Facturas pendientes por aprobación", "Documentos en proceso de revisión", "▤"),
    ("facturacion.pagos.consultar", "LIDER_FACTURACION", "Facturación", "Facturas pendientes por pagar", "Compromisos de pago del período", "$"),
    ("facturacion.impuestos.consultar", "LIDER_FACTURACION", "Facturación", "Declaración de impuestos", "Calendario y obligaciones tributarias", "%"),
    ("logistica.despachos.consultar", "LIDER_LOGISTICA", "Logística", "Despachos", "Seguimiento visual de despachos pendientes", "→"),
    ("logistica.entregas.consultar", "LIDER_LOGISTICA", "Logística", "Entregas", "Programación visual de entregas", "✓"),
    ("logistica.inventario.consultar", "LIDER_LOGISTICA", "Logística", "Inventario y movimientos", "Referencia visual de existencias y movimientos", "▦"),
    ("gestion_humana.colaboradores.consultar", "LIDER_GESTION_HUMANA", "Gestión Humana", "Colaboradores", "Referencia visual del equipo de trabajo", "◎"),
    ("gestion_humana.novedades.consultar", "LIDER_GESTION_HUMANA", "Gestión Humana", "Novedades de personal", "Ambientación de novedades organizacionales", "◇"),
    ("gestion_humana.vacaciones.consultar", "LIDER_GESTION_HUMANA", "Gestión Humana", "Vacaciones y permisos", "Referencia visual de solicitudes del personal", "□"),
)
PERMISSIONS = {
    code: {"codigo": code, "rol": role, "area": area, "titulo": title,
           "descripcion": description, "icono": icon}
    for code, role, area, title, description, icon in CATALOG
}
LEADER_ROLES = {item[1] for item in CATALOG}
