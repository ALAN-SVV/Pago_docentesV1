# Acumulación exacta y reserva común de permisos. El llamador abre la transacción
# y bloquea al empleado antes de modificar permisos, reservas o saldos.
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.aprobaciones.model import Aprobacion
from app.modules.vacaciones.historicos.repository import consultar_apertura
from app.modules.vacaciones.permisos.repository import (
    consultar_reservas_horas,
    consultar_total_descontado,
    consultar_totales,
)
from app.modules.vacaciones.reservas.model import Descuento, Reserva
from app.modules.vacaciones.reservas.repository import bloquear_saldos
from app.modules.vacaciones.saldos.service import distribuir_dias, obtener_resumen_saldo

MINUTOS_POR_DIA = 480


# comprobamos que las horas, los descuentos y las reservas coincidan
async def consultar_acumulacion(
    sesion: AsyncSession, id_empleado: int, verificar_reserva=True
):
    aprobados, pendientes, dias = await consultar_totales(sesion, id_empleado)

    apertura = await consultar_apertura(sesion, id_empleado)
    # Solo el sobrante certificado: los días históricos ya están incluidos en saldos.
    aprobados += apertura["datos"]["minutos_sobrantes"] if apertura else 0
    restantes = aprobados - dias * MINUTOS_POR_DIA
    descontados = await consultar_total_descontado(sesion, id_empleado)
    if not 0 <= restantes < MINUTOS_POR_DIA or descontados != dias:
        raise HTTPException(
            status_code=409,
            detail="Revisa el historial de conversiones y descuentos de permisos.",
        )
    reservas = await consultar_reservas_horas(sesion, id_empleado)
    total_reservado = sum((r.dias_reservados for r in reservas), Decimal("0.00"))
    # Los pendientes no son horas aprobadas: solo respaldan los días que completarían.
    necesarios = (restantes + pendientes) // MINUTOS_POR_DIA
    if verificar_reserva and total_reservado != necesarios:
        raise HTTPException(
            status_code=409,
            detail="La reserva común de permisos no coincide con las horas pendientes.",
        )
    return aprobados, pendientes, dias, restantes, reservas


# función para liberar reserva comun
async def liberar_reserva_comun(sesion: AsyncSession, permiso):
    ahora = datetime.now(timezone.utc)
    for reserva in await consultar_reservas_horas(sesion, permiso.id_empleado):
        reserva.estado = "LIBERADA"
        reserva.fecha_cierre = ahora
        reserva.id_permiso_cierre = permiso.id_permiso
    # Cierra el índice único parcial antes de insertar la nueva distribución.
    await sesion.flush()


# calculamos los días que deben quedar reservados por los permisos pendientes
async def recalcular_reserva_comun(sesion: AsyncSession, permiso):
    await bloquear_saldos(sesion, permiso.id_empleado)
    await liberar_reserva_comun(sesion, permiso)
    _, pendientes, _, restantes, _ = await consultar_acumulacion(
        sesion,
        permiso.id_empleado,
        verificar_reserva=False,
    )
    dias = Decimal((restantes + pendientes) // MINUTOS_POR_DIA)
    resumen = await obtener_resumen_saldo(sesion, permiso.id_empleado)
    reparto, faltan = distribuir_dias(resumen, dias)
    if faltan > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Saldo insuficiente para los permisos: faltan {faltan} días, incluyendo el anticipo permitido.",
        )
    ahora = datetime.now(timezone.utc)
    for parte in reparto:
        sesion.add(
            Reserva(
                ambito="HORAS",
                id_empleado=permiso.id_empleado,
                id_saldo=parte.id_saldo,
                id_permiso_cambio=permiso.id_permiso,
                dias_reservados=parte.dias_a_descontar,
                es_anticipo=parte.es_anticipo,
                estado="ACTIVA",
                fecha_registro=ahora,
            )
        )
    await sesion.flush()


# convertimos cada ocho horas aprobadas en un día y conservamos los minutos sobrantes
async def convertir_horas_aprobadas(sesion: AsyncSession, permiso, datos):
    saldos = {s.id_saldo: s for s in await bloquear_saldos(sesion, permiso.id_empleado)}
    # Comprueba que las reservas de vacaciones y horas aún estén respaldadas.
    await obtener_resumen_saldo(sesion, permiso.id_empleado)
    _, _, _, anteriores, _ = await consultar_acumulacion(sesion, permiso.id_empleado)
    dias, restantes = divmod(anteriores + permiso.total_minutos, MINUTOS_POR_DIA)
    await liberar_reserva_comun(sesion, permiso)
    resumen = await obtener_resumen_saldo(sesion, permiso.id_empleado)
    reparto, faltan = distribuir_dias(resumen, Decimal(dias))
    if faltan:
        raise HTTPException(
            status_code=409,
            detail="El saldo ya no respalda la conversión de horas. Revisa los ajustes.",
        )
    ahora = datetime.now(timezone.utc)
    for parte in reparto:
        saldo = saldos[parte.id_saldo]
        saldo.dias_utilizados += parte.dias_a_descontar
        saldo.dias_disponibles -= parte.dias_a_descontar
        sesion.add(
            Descuento(
                id_empleado=permiso.id_empleado,
                id_permiso=permiso.id_permiso,
                id_saldo=saldo.id_saldo,
                dias_descontados=parte.dias_a_descontar,
                es_anticipo=parte.es_anticipo,
                fecha_registro=ahora,
            )
        )
    sesion.add(
        Aprobacion(
            id_empleado=permiso.id_empleado,
            id_permiso=permiso.id_permiso,
            id_aprobador=datos.id_aprobador,
            tipo_intervencion="DECISION",
            decision="APROBADA",
            observacion=datos.observacion,
            fecha=ahora.replace(tzinfo=None),
        )
    )
    permiso.estado = "APROBADO"
    permiso.minutos_restantes_antes = anteriores
    permiso.minutos_restantes_despues = restantes
    permiso.dias_convertidos = dias
    permiso.id_aprobador = datos.id_aprobador
    permiso.observacion_decision = datos.observacion
    permiso.fecha_cierre = ahora
    await sesion.flush()
    await recalcular_reserva_comun(sesion, permiso)
