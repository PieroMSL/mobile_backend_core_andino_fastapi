from datetime import datetime, timezone, date
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.mdl_cartera import CarteraDiaria
from app.models.mdl_clientes import Cliente

def listar_por_asesor(
    db: Session, asesor_id: str, fecha: date | None
) -> list[dict]:
    query = (
        db.query(CarteraDiaria, Cliente)
        .join(Cliente, Cliente.id == CarteraDiaria.cliente_id)
        .filter(CarteraDiaria.asesor_id == asesor_id)
    )
    if fecha is not None:
        query = query.filter(CarteraDiaria.fecha_asignacion == fecha)
        filas = query.order_by(desc(CarteraDiaria.score_prioridad)).all()
    else:
        filas_historicas = query.order_by(
            desc(CarteraDiaria.fecha_asignacion),
            desc(CarteraDiaria.score_prioridad),
        ).all()
        filas = []
        clientes_vistos = set()
        for cartera, cliente in filas_historicas:
            cliente_id = str(cartera.cliente_id)
            if cliente_id in clientes_vistos:
                continue
            clientes_vistos.add(cliente_id)
            filas.append((cartera, cliente))

    return [
        {
            "id": str(c.id),
            "cliente_id": str(c.cliente_id),
            "cliente_nombre": f"{cli.nombres} {cli.apellidos}",
            "documento": cli.numero_documento,
            "tipo_gestion": c.tipo_gestion,
            "prioridad": c.prioridad,
            "score_prioridad": c.score_prioridad or 0,
            "monto_credito": float(c.monto_credito or 0),
            "estado_visita": c.estado_visita,
            "orden_manual": c.orden_manual,
            "lat": float(cli.lat) if cli.lat is not None else None,
            "lng": float(cli.lng) if cli.lng is not None else None,
        }
        for c, cli in filas
    ]

def marcar_visita(db: Session, asesor_id: str, cartera_id: str, data: dict) -> bool:
    fila = (
        db.query(CarteraDiaria)
        .filter(CarteraDiaria.id == cartera_id, CarteraDiaria.asesor_id == asesor_id)
        .first()
    )
    if not fila:
        return False
    fila.estado_visita = "visitado" if data["resultado"] == "visitado" else data["resultado"]
    fila.resultado_visita = data["resultado"]
    fila.observacion_visita = data.get("observacion", "")
    fila.timestamp_visita = datetime.now(timezone.utc)
    fila.lat_visita = data.get("lat")
    fila.lng_visita = data.get("lng")
    db.commit()
    return True
