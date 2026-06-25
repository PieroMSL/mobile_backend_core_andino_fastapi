from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date, timedelta
import uuid
import random

def ejecutar_comite(db: Session):
    """
    Simula el Motor de Comité.
    Casos 1-24: aprobado, monto completo
    Casos 25-27: condicionado, monto reducido
    Casos 28-30: rechazado, registrar motivo
    """
    solicitudes = db.execute(
        text("""
            SELECT id, monto_solicitado 
            FROM solicitudes_credito 
            WHERE estado IN ('borrador', 'enviado', 'recibido_comite', 'en_evaluacion')
            ORDER BY created_at ASC
        """)
    ).mappings().all()

    resultados = {"aprobados": 0, "condicionados": 0, "rechazados": 0}

    for i, s in enumerate(solicitudes):
        caso = i + 1
        sid = s["id"]
        monto = float(s["monto_solicitado"])

        if caso <= 24:
            # Aprobado, monto completo
            db.execute(
                text("""
                    UPDATE solicitudes_credito 
                    SET estado = 'aprobado', monto_aprobado = :monto 
                    WHERE id = :sid
                """),
                {"monto": monto, "sid": sid}
            )
            resultados["aprobados"] += 1
        elif caso <= 27:
            # Condicionado, monto reducido
            monto_red = monto * 0.8
            db.execute(
                text("""
                    UPDATE solicitudes_credito 
                    SET estado = 'condicionado', monto_aprobado = :monto, 
                        condicion_adicional = 'Aprobado con monto reducido por política.' 
                    WHERE id = :sid
                """),
                {"monto": monto_red, "sid": sid}
            )
            resultados["condicionados"] += 1
        else:
            # Rechazado
            db.execute(
                text("""
                    UPDATE solicitudes_credito 
                    SET estado = 'rechazado', motivo_rechazo = 'Exceso de endeudamiento o política de riesgo.' 
                    WHERE id = :sid
                """),
                {"sid": sid}
            )
            resultados["rechazados"] += 1

    db.commit()
    return resultados

def ejecutar_sincronizacion_retorno(db: Session):
    """
    Simula la Sincronización de Retorno desde el core.
    - Actualizar: solicitudes_credito (a desembolsado)
    - Insertar: cr_creditos
    - Generar: cr_cronograma_pagos
    - Registrar: sync_log
    """
    solicitudes = db.execute(
        text("""
            SELECT s.id, s.cod_solicitud_core, s.cliente_id, s.monto_aprobado, s.plazo_meses, s.tea_referencial 
            FROM solicitudes_credito s
            LEFT JOIN cr_creditos c ON c.cliente_id = s.cliente_id 
                AND c.cod_cuenta_credito = 'CRED-' || UPPER(substr(s.id::text, 1, 8))
            WHERE s.estado IN ('aprobado', 'condicionado')
              AND c.id IS NULL
        """)
    ).mappings().all()

    procesados = 0

    for s in solicitudes:
        cod_cuenta = 'CRED-' + str(s["id"])[:8].upper()
        cliente_id = s["cliente_id"]
        monto = float(s["monto_aprobado"] or 0)
        plazo = s["plazo_meses"] or 12
        tea = float(s["tea_referencial"] or 35.0)
        fecha_desembolso = date.today()

        # Insertar cr_creditos
        db.execute(
            text("""
                INSERT INTO cr_creditos (
                    cod_cuenta_credito, cliente_id, producto, monto_desembolsado, 
                    saldo_capital, saldo_total, dias_mora, calificacion_interna, 
                    estado, fecha_desembolso, tea, cuotas_total, cuotas_pagadas
                ) VALUES (
                    :cod, :cli, 'Credito Negocio', :monto,
                    :monto, :monto_total, 0, 'Normal',
                    'vigente', :fecha, :tea, :plazo, 0
                )
            """),
            {
                "cod": cod_cuenta, "cli": cliente_id, "monto": monto,
                "monto_total": monto * (1 + (tea/100) * (plazo/12)), 
                "fecha": fecha_desembolso, "tea": tea, "plazo": plazo
            }
        )

        # Generar cr_cronograma_pagos
        monto_cuota = (monto * (1 + (tea/100) * (plazo/12))) / plazo
        monto_capital = monto / plazo
        monto_interes = monto_cuota - monto_capital

        saldo = monto * (1 + (tea/100) * (plazo/12))

        def add_months(sourcedate, months):
            month = sourcedate.month - 1 + months
            year = sourcedate.year + month // 12
            month = month % 12 + 1
            day = min(sourcedate.day, [31, 29 if year % 4 == 0 and not year % 100 == 0 or year % 400 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            return date(year, month, day)

        for nro in range(1, plazo + 1):
            fecha_vencimiento = add_months(fecha_desembolso, nro)
            saldo -= monto_cuota
            db.execute(
                text("""
                    INSERT INTO cr_cronograma_pagos (
                        cod_cuenta_credito, nro_cuota, fecha_vencimiento, 
                        monto_cuota, monto_capital, monto_interes, saldo, estado_cuota
                    ) VALUES (
                        :cod, :nro, :fvenc, :cuota, :cap, :int, :saldo, 'pendiente'
                    )
                """),
                {
                    "cod": cod_cuenta, "nro": nro, "fvenc": fecha_vencimiento,
                    "cuota": monto_cuota, "cap": monto_capital, "int": monto_interes,
                    "saldo": max(0, saldo)
                }
            )

        # Actualizar solicitudes_credito a desembolsado
        db.execute(
            text("""
                UPDATE solicitudes_credito 
                SET estado = 'desembolsado' 
                WHERE id = :sid
            """),
            {"sid": s["id"]}
        )

        # Registrar sync_log
        db.execute(
            text("""
                INSERT INTO sync_log (direccion, entidad, referencia, resultado, detalle)
                VALUES ('core_a_mobile', 'cr_creditos', :ref, 'ok', 'Credito y cronograma generados desde Core')
            """),
            {"ref": cod_cuenta}
        )
        
        procesados += 1

    db.commit()
    return {"creditos_sincronizados": procesados}
