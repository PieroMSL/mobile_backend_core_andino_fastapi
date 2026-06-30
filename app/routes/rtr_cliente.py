"""
Rutas de la **app de clientes** (appbanco / Flutter clientes).

Login con DNI (usuarios_cliente) y consulta de productos del cliente
autenticado: cuentas de ahorro, créditos + cronograma, movimientos,
tarjetas y notificaciones. Todas (excepto login) requieren Bearer token.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_cliente
from app.schemas.sch_cliente import (
    LoginClienteIn, RegisterClienteIn, TokenClienteOut, ClienteOut, CuentaAhorroOut, CreditoOut,
    CuotaOut, MovimientoOut, TarjetaOut, NotificacionOut, OperacionIn, OperacionOut,
)
from app.schemas.sch_solicitudes import SolicitudIn, SolicitudCreada, SolicitudResumen
from app.controllers import ctl_auth_cliente
from app.repositories import rep_cliente, rep_solicitudes
from app.services import svc_promocion

router = APIRouter()


@router.post("/login", response_model=TokenClienteOut)
def login(data: LoginClienteIn, db: Session = Depends(get_db)):
    """Login del cliente (numero_documento + password) -> JWT."""
    result = ctl_auth_cliente.login(db, data.numero_documento, data.password)
    if result and result.get("_bloqueado"):
        raise HTTPException(status_code=423, detail="Cuenta bloqueada")
    if not result:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    return result

@router.post("/register", response_model=TokenClienteOut)
def register(data: RegisterClienteIn, db: Session = Depends(get_db)):
    """Registro del cliente -> JWT."""
    result = ctl_auth_cliente.register(
        db, 
        numero_documento=data.numero_documento, 
        nombres=data.nombres, 
        apellidos=data.apellidos, 
        telefono=data.telefono, 
        password=data.password
    )
    if result and result.get("_error"):
        raise HTTPException(status_code=400, detail=result["_error"])
    if not result:
        raise HTTPException(status_code=500, detail="Error en registro")
    return result


@router.get("/perfil", response_model=ClienteOut)
def perfil(db: Session = Depends(get_db), cli: dict = Depends(get_current_cliente)):
    cliente = rep_cliente.get_cliente(db, cli["cliente_id"])
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.get("/cuentas", response_model=list[CuentaAhorroOut])
def cuentas(db: Session = Depends(get_db), cli: dict = Depends(get_current_cliente)):
    return rep_cliente.cuentas_ahorro(db, cli["cliente_id"])


@router.get("/creditos", response_model=list[CreditoOut])
def creditos(db: Session = Depends(get_db), cli: dict = Depends(get_current_cliente)):
    return rep_cliente.creditos(db, cli["cliente_id"])


@router.get("/creditos/{cod_cuenta_credito}/cronograma", response_model=list[CuotaOut])
def cronograma(
    cod_cuenta_credito: str,
    db: Session = Depends(get_db),
    cli: dict = Depends(get_current_cliente),
):
    if not rep_cliente.credito_pertenece(
        db, cli["cliente_id"], cod_cuenta_credito
    ):
        raise HTTPException(status_code=404, detail="Credito no encontrado")
    return rep_cliente.cronograma(db, cod_cuenta_credito)


@router.get("/movimientos", response_model=list[MovimientoOut])
def movimientos(
    limit: int = 20,
    db: Session = Depends(get_db),
    cli: dict = Depends(get_current_cliente),
):
    return rep_cliente.movimientos(db, cli["cliente_id"], limit)


@router.get("/tarjetas", response_model=list[TarjetaOut])
def tarjetas(db: Session = Depends(get_db), cli: dict = Depends(get_current_cliente)):
    return rep_cliente.tarjetas(db, cli["cliente_id"])


@router.get("/notificaciones", response_model=list[NotificacionOut])
def notificaciones(db: Session = Depends(get_db), cli: dict = Depends(get_current_cliente)):
    return rep_cliente.notificaciones(db, cli["cliente_id"])


@router.post("/operaciones", response_model=OperacionOut)
def crear_operacion(
    data: OperacionIn,
    db: Session = Depends(get_db),
    cli: dict = Depends(get_current_cliente),
):
    """Registra una operación iniciada por el cliente (transferencia / pago)."""
    if not rep_cliente.cuenta_ahorro_pertenece(
        db, cli["cliente_id"], data.cod_cuenta_origen
    ):
        raise HTTPException(status_code=403, detail="Cuenta de origen no autorizada")
    return rep_cliente.crear_operacion(db, cli["cliente_id"], data.model_dump())


@router.post("/solicitudes", response_model=SolicitudCreada)
def crear_solicitud_cliente(
    data: SolicitudIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    cli: dict = Depends(get_current_cliente),
):
    """Permite al cliente registrar una solicitud de crédito desde la App de Clientes (Paso 1)."""
    cliente = rep_cliente.get_cliente(db, cli["cliente_id"])
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    solicitud = data.model_dump()
    solicitud.update(
        {
            "numero_documento": cliente.numero_documento,
            "nombres": cliente.nombres,
            "apellidos": cliente.apellidos,
            "telefono": cliente.telefono,
        }
    )

    row = db.execute(
        text("SELECT asesor_id, agencia_id FROM cartera_diaria WHERE cliente_id = :cid LIMIT 1"),
        {"cid": cli["cliente_id"]}
    ).first()
    
    if row:
        asesor_id = str(row[0])
        agencia_id = str(row[1]) if row[1] else None
    else:
        row_pre = db.execute(
            text("SELECT asesor_id FROM creditos_preaprobados WHERE cliente_id = :cid LIMIT 1"),
            {"cid": cli["cliente_id"]}
        ).first()
        if row_pre:
            asesor_id = str(row_pre[0])
            row_ag = db.execute(
                text("SELECT agencia_id FROM asesores WHERE id = :aid"),
                {"aid": asesor_id}
            ).first()
            agencia_id = str(row_ag[0]) if row_ag and row_ag[0] else None
        else:
            row_fallback = db.execute(
                text("SELECT id, agencia_id FROM asesores WHERE activo = TRUE LIMIT 1")
            ).first()
            if not row_fallback:
                raise HTTPException(status_code=500, detail="No hay asesores disponibles en el sistema")
            asesor_id = str(row_fallback[0])
            agencia_id = str(row_fallback[1]) if row_fallback[1] else None

    res = rep_solicitudes.crear(
        db, asesor_id, agencia_id, solicitud, canal="cliente"
    )
    background_tasks.add_task(svc_promocion.promover, db)
    return res

@router.get("/solicitudes", response_model=list[SolicitudResumen])
def listar_solicitudes_cliente(
    db: Session = Depends(get_db),
    cli: dict = Depends(get_current_cliente),
):
    """Lista las solicitudes previas del cliente autenticado."""
    return rep_solicitudes.listar_por_cliente(db, cli["cliente_id"])
