from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.aprobaciones.model import Aprobacion
from app.modules.vacaciones.aprobaciones.repository import (
    es_responsable_talento_humano,
    existe_aprobador,
)
from app.modules.vacaciones.historicos.repository import (
    consultar_apertura,
    validar_fecha_posterior,
)
from app.modules.vacaciones.permisos import repository as repo
from app.modules.vacaciones.permisos.contabilidad import (
    consultar_acumulacion,
    convertir_horas_aprobadas,
    recalcular_reserva_comun,
)
from app.modules.vacaciones.permisos.model import Permiso
from app.modules.vacaciones.permisos.schema import (
    DescuentoHorasRespuesta,
    PermisoActualizar,
    PermisoRespuesta,
    ReservaHorasRespuesta,
    ResumenHorasRespuesta,
)
from app.modules.vacaciones.solicitudes.repository import (
    bloquear_empleado,
    consultar_cruce,
    consultar_pendiente_sin_reserva,
)

OBSERVACION = "Horas de permiso a cargo a vacaciones"


# función para transaccion permisos
@asynccontextmanager
async def transaccion_permisos(sesion: AsyncSession):
    # El commit incluye documento, decisión, reservas y descuentos; cualquier fallo revierte todo.
    try:
        async with sesion.begin():
            yield
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="No se pudo guardar el permiso. Revisa sus referencias y la integridad de los datos.",
        ) from None


# función para calcular minutos
def calcular_minutos(datos) -> int:
    return (datos.hora_fin.hour * 60 + datos.hora_fin.minute) - (
        datos.hora_inicio.hour * 60 + datos.hora_inicio.minute
    )


# función para asignar intervalo
def asignar_intervalo(permiso, datos):
    for campo in ("fecha", "hora_inicio", "hora_fin", "motivo"):
        setattr(permiso, campo, getattr(datos, campo))
    permiso.total_minutos = calcular_minutos(datos)
    permiso.total_horas = (Decimal(permiso.total_minutos) / 60).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


# función para validar pendiente
def validar_pendiente(permiso, requiere_gestionado=True):
    if (
        permiso.estado != "PENDIENTE"
        or permiso.id_aprobador is not None
        or permiso.fecha_cierre is not None
    ):
        raise HTTPException(
            status_code=409,
            detail="Solo se modifican permisos pendientes sin decisión previa.",
        )
    if requiere_gestionado and not permiso.gestionado:
        raise HTTPException(
            status_code=409, detail="Concilia primero este permiso pendiente antiguo."
        )


# función para validar responsable
async def validar_responsable(sesion: AsyncSession, id_aprobador: int):
    if not await existe_aprobador(sesion, id_aprobador):
        raise HTTPException(status_code=404, detail="El empleado aprobador no existe.")
    if not await es_responsable_talento_humano(sesion, id_aprobador):
        raise HTTPException(
            status_code=403, detail="El aprobador no está habilitado en Talento Humano."
        )


# función para validar historial
async def validar_historial(sesion: AsyncSession, id_empleado: int):
    historicos = await repo.consultar_historicos_sin_conciliar(sesion, id_empleado)
    if historicos:
        raise HTTPException(
            status_code=409,
            detail=f"Revisa los permisos históricos sin conciliar {historicos}. No se presupone su descuento ni su sobrante.",
        )
    antigua = await consultar_pendiente_sin_reserva(sesion, id_empleado)
    if antigua is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Concilia primero la reserva de la solicitud antigua {antigua}.",
        )


# verificamos el corte histórico y los cruces con otros permisos o vacaciones
async def validar_cruces(sesion: AsyncSession, permiso):

    await validar_fecha_posterior(sesion, permiso.id_empleado, permiso.fecha)
    cruce = await repo.consultar_cruce_horario(
        sesion,
        permiso.id_empleado,
        permiso.fecha,
        permiso.hora_inicio,
        permiso.hora_fin,
        permiso.id_permiso,
    )
    if cruce is not None:
        raise HTTPException(
            status_code=409, detail=f"El horario se cruza con el permiso {cruce}."
        )
    vacaciones = await consultar_cruce(
        sesion, permiso.id_empleado, permiso.fecha, permiso.fecha
    )
    if vacaciones is not None:
        raise HTTPException(
            status_code=409,
            detail=f"La fecha coincide con la solicitud de vacaciones {vacaciones}.",
        )


# función para obtener permisos por empleado
async def obtener_permisos_por_empleado(sesion: AsyncSession, id_empleado: int):
    return [
        PermisoRespuesta.model_validate(p)
        for p in await repo.consultar_permisos_por_empleado(sesion, id_empleado)
    ]


# función para obtener permiso
async def obtener_permiso(sesion: AsyncSession, id_permiso: int):
    permiso = await repo.consultar_permiso(sesion, id_permiso)
    if permiso is None:
        raise HTTPException(status_code=404, detail="El permiso no existe.")
    return PermisoRespuesta.model_validate(permiso)


# función para crear permiso
async def crear_permiso(sesion: AsyncSession, datos):
    async with transaccion_permisos(sesion):
        await bloquear_empleado(sesion, datos.id_empleado)
        await validar_historial(sesion, datos.id_empleado)
        await consultar_acumulacion(sesion, datos.id_empleado)
        permiso = Permiso(
            id_empleado=datos.id_empleado,
            estado="PENDIENTE",
            gestionado=True,
            observacion=OBSERVACION,
            fecha_registro=datetime.now(timezone.utc),
        )
        asignar_intervalo(permiso, datos)
        await validar_cruces(sesion, permiso)
        sesion.add(permiso)
        await sesion.flush()  # Obtiene el ID para referenciar el cambio de reserva.
        await recalcular_reserva_comun(sesion, permiso)
        respuesta = PermisoRespuesta.model_validate(permiso)
    return respuesta


# función para actualizar permiso
async def actualizar_permiso(sesion: AsyncSession, id_permiso: int, datos):
    async with transaccion_permisos(sesion):
        permiso = await repo.bloquear_permiso_y_empleado(sesion, id_permiso)
        validar_pendiente(permiso)
        await validar_historial(sesion, permiso.id_empleado)
        await consultar_acumulacion(sesion, permiso.id_empleado)
        asignar_intervalo(permiso, datos)
        await validar_cruces(sesion, permiso)
        await sesion.flush()
        await recalcular_reserva_comun(sesion, permiso)
        respuesta = PermisoRespuesta.model_validate(permiso)
    return respuesta


# función para cancelar permiso
async def cancelar_permiso(sesion: AsyncSession, id_permiso: int):
    async with transaccion_permisos(sesion):
        permiso = await repo.bloquear_permiso_y_empleado(sesion, id_permiso)
        validar_pendiente(permiso, requiere_gestionado=False)
        await consultar_acumulacion(sesion, permiso.id_empleado)
        permiso.estado = "CANCELADO"
        permiso.fecha_cierre = datetime.now(timezone.utc)
        await sesion.flush()
        if permiso.gestionado:
            await recalcular_reserva_comun(sesion, permiso)
        respuesta = PermisoRespuesta.model_validate(permiso)
    return respuesta


# función para decidir permiso
async def decidir_permiso(sesion: AsyncSession, id_permiso: int, datos, aprobar: bool):
    async with transaccion_permisos(sesion):
        permiso = await repo.bloquear_permiso_y_empleado(sesion, id_permiso)
        validar_pendiente(permiso, requiere_gestionado=aprobar)
        await validar_responsable(sesion, datos.id_aprobador)
        await consultar_acumulacion(sesion, permiso.id_empleado)
        if aprobar:
            await validar_historial(sesion, permiso.id_empleado)
            await validar_cruces(sesion, permiso)
        if aprobar:
            await convertir_horas_aprobadas(sesion, permiso, datos)
        else:
            sesion.add(
                Aprobacion(
                    id_empleado=permiso.id_empleado,
                    id_permiso=permiso.id_permiso,
                    id_aprobador=datos.id_aprobador,
                    tipo_intervencion="DECISION",
                    decision="RECHAZADA",
                    observacion=datos.observacion,
                    fecha=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
            permiso.estado = "RECHAZADO"
            permiso.id_aprobador = datos.id_aprobador
            permiso.observacion_decision = datos.observacion
            permiso.fecha_cierre = datetime.now(timezone.utc)
            await sesion.flush()
            if permiso.gestionado:
                await recalcular_reserva_comun(sesion, permiso)
        respuesta = PermisoRespuesta.model_validate(permiso)
    return respuesta


# función para conciliar permiso
async def conciliar_permiso(sesion: AsyncSession, id_permiso: int, datos):
    async with transaccion_permisos(sesion):
        permiso = await repo.bloquear_permiso_y_empleado(sesion, id_permiso)
        validar_pendiente(permiso, requiere_gestionado=False)
        if permiso.gestionado:
            raise HTTPException(
                status_code=409,
                detail="El permiso ya está incorporado al control de horas.",
            )
        await validar_responsable(sesion, datos.id_responsable)
        await consultar_acumulacion(sesion, permiso.id_empleado)
        try:
            intervalo = PermisoActualizar(
                fecha=permiso.fecha,
                hora_inicio=permiso.hora_inicio,
                hora_fin=permiso.hora_fin,
                motivo=permiso.motivo,
            )
        except ValidationError:
            raise HTTPException(
                status_code=409,
                detail="Revisa fecha, horario y motivo del permiso antiguo antes de conciliar.",
            ) from None
        horas = (Decimal(calcular_minutos(intervalo)) / 60).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if permiso.total_horas is None or permiso.total_horas != horas:
            raise HTTPException(
                status_code=409,
                detail="Las horas antiguas no coinciden con el intervalo. Requieren revisión.",
            )
        await validar_cruces(sesion, permiso)
        asignar_intervalo(permiso, intervalo)
        permiso.gestionado = True
        permiso.observacion = OBSERVACION
        permiso.fecha_registro = datetime.now(timezone.utc)
        await sesion.flush()
        await recalcular_reserva_comun(sesion, permiso)
        respuesta = PermisoRespuesta.model_validate(permiso)
    return respuesta


# función para obtener resumen horas
async def obtener_resumen_horas(sesion: AsyncSession, id_empleado: int):
    # Una lectura coherente de varias tablas, serializada con las escrituras de ese empleado.
    async with sesion.begin():
        await bloquear_empleado(sesion, id_empleado)
        aprobados, pendientes, dias, restantes, reservas = await consultar_acumulacion(
            sesion, id_empleado
        )

        apertura = await consultar_apertura(sesion, id_empleado)
        horas, minutos = divmod(restantes, 60)
        return ResumenHorasRespuesta(
            minutos_apertura=apertura["datos"]["minutos_sobrantes"] if apertura else 0,
            id_empleado=id_empleado,
            minutos_aprobados=aprobados,
            minutos_pendientes=pendientes,
            dias_descontados=dias,
            minutos_restantes=restantes,
            horas_restantes=horas,
            minutos_adicionales=minutos,
            dias_reservados=sum((r.dias_reservados for r in reservas), Decimal("0.00")),
            reservas_activas=[
                ReservaHorasRespuesta.model_validate(r) for r in reservas
            ],
            permisos_historicos_sin_conciliar=await repo.consultar_historicos_sin_conciliar(
                sesion, id_empleado
            ),
        )


# función para obtener descuentos
async def obtener_descuentos(sesion: AsyncSession, id_permiso: int):
    await obtener_permiso(sesion, id_permiso)
    return [
        DescuentoHorasRespuesta.model_validate(d)
        for d in await repo.consultar_descuentos_horas(sesion, id_permiso)
    ]


# función para obtener reservas
async def obtener_reservas(sesion: AsyncSession, id_empleado: int):
    return [
        ReservaHorasRespuesta.model_validate(r)
        for r in await repo.consultar_reservas_horas(
            sesion, id_empleado, solo_activas=False
        )
    ]
