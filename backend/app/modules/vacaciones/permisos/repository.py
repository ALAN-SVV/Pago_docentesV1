from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.ajustes.repository import consultar_total_reintegrado_horas
from app.modules.vacaciones.permisos.model import Permiso
from app.modules.vacaciones.reservas.model import Descuento, Reserva
from app.modules.vacaciones.solicitudes.repository import bloquear_empleado


# función para consultar permisos por empleado
async def consultar_permisos_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[Permiso]:
    consulta = (
        select(Permiso)
        .where(Permiso.id_empleado == id_empleado)
        .order_by(Permiso.fecha.desc().nulls_last(), Permiso.id_permiso.desc())
    )
    return list((await sesion.scalars(consulta)).all())


# función para consultar permiso
async def consultar_permiso(sesion: AsyncSession, id_permiso: int) -> Permiso | None:
    return await sesion.scalar(select(Permiso).where(Permiso.id_permiso == id_permiso))


# función para bloquear permiso y empleado
async def bloquear_permiso_y_empleado(sesion: AsyncSession, id_permiso: int) -> Permiso:
    # Mismo orden de bloqueo que vacaciones: empleado, documento, saldos.
    fila = (
        await sesion.execute(
            select(Permiso.id_empleado).where(Permiso.id_permiso == id_permiso)
        )
    ).first()
    if fila is None:
        raise HTTPException(status_code=404, detail="El permiso no existe.")
    if fila.id_empleado is None:
        raise HTTPException(
            status_code=409, detail="El permiso no tiene empleado asignado."
        )
    await bloquear_empleado(sesion, fila.id_empleado)
    permiso = await sesion.scalar(
        select(Permiso)
        .where(Permiso.id_permiso == id_permiso)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if permiso is None:
        raise HTTPException(status_code=404, detail="El permiso ya no existe.")
    return permiso


# función para consultar cruce horario
async def consultar_cruce_horario(
    sesion: AsyncSession, id_empleado: int, fecha, inicio, fin, excluir=None
):
    # Intervalos [inicio, fin): 08:00-09:00 y 09:00-10:00 no se cruzan.
    consulta = select(Permiso.id_permiso).where(
        Permiso.id_empleado == id_empleado,
        Permiso.fecha == fecha,
        func.upper(func.trim(Permiso.estado)).in_(
            ["PENDIENTE", "APROBADO", "APROBADA"]
        ),
        Permiso.hora_inicio < fin,
        Permiso.hora_fin > inicio,
    )
    if excluir is not None:
        consulta = consulta.where(Permiso.id_permiso != excluir)
    return await sesion.scalar(consulta.order_by(Permiso.id_permiso).limit(1))


# función para consultar cruce con permisos
async def consultar_cruce_con_permisos(
    sesion: AsyncSession, id_empleado: int, inicio, fin
):
    consulta = select(Permiso.id_permiso).where(
        Permiso.id_empleado == id_empleado,
        Permiso.fecha.between(inicio, fin),
        func.upper(func.trim(Permiso.estado)).in_(
            ["PENDIENTE", "APROBADO", "APROBADA"]
        ),
    )
    return await sesion.scalar(consulta.order_by(Permiso.id_permiso).limit(1))


# función para consultar historicos sin conciliar
async def consultar_historicos_sin_conciliar(
    sesion: AsyncSession, id_empleado: int, excluir=None
) -> list[int]:
    # No suponemos que las horas antiguas aprobadas ya estén descontadas.
    consulta = select(Permiso.id_permiso).where(
        Permiso.id_empleado == id_empleado,
        Permiso.gestionado.is_(False),
        (
            Permiso.estado.is_(None)
            | ~func.upper(func.trim(Permiso.estado)).in_(
                ["RECHAZADO", "RECHAZADA", "CANCELADO", "CANCELADA"]
            )
        ),
    )
    if excluir is not None:
        consulta = consulta.where(Permiso.id_permiso != excluir)
    return list((await sesion.scalars(consulta.order_by(Permiso.id_permiso))).all())


# función para consultar totales
async def consultar_totales(sesion: AsyncSession, id_empleado: int):
    consulta = select(
        func.coalesce(
            func.sum(
                case((Permiso.estado == "APROBADO", Permiso.total_minutos), else_=0)
            ),
            0,
        ),
        func.coalesce(
            func.sum(
                case((Permiso.estado == "PENDIENTE", Permiso.total_minutos), else_=0)
            ),
            0,
        ),
        func.coalesce(
            func.sum(
                case(
                    (
                        Permiso.estado.in_(["APROBADO", "ANULADO"]),
                        Permiso.dias_convertidos,
                    ),
                    else_=0,
                )
            ),
            0,
        ),
    ).where(Permiso.id_empleado == id_empleado, Permiso.gestionado.is_(True))

    aprobados, pendientes, convertidos = (await sesion.execute(consulta)).one()
    netos = convertidos - await consultar_total_reintegrado_horas(sesion, id_empleado)
    if netos < 0 or netos != int(netos):
        raise HTTPException(
            status_code=409,
            detail="Los reintegros de horas no forman días completos coherentes.",
        )
    return int(aprobados), int(pendientes), int(netos)


# función para consultar reservas horas
async def consultar_reservas_horas(
    sesion: AsyncSession, id_empleado: int, solo_activas=True
) -> list[Reserva]:
    consulta = select(Reserva).where(
        Reserva.id_empleado == id_empleado, Reserva.ambito == "HORAS"
    )
    if solo_activas:
        consulta = consulta.where(Reserva.estado == "ACTIVA")
    return list((await sesion.scalars(consulta.order_by(Reserva.id_reserva))).all())


# función para consultar descuentos horas
async def consultar_descuentos_horas(
    sesion: AsyncSession, id_permiso: int
) -> list[Descuento]:
    consulta = (
        select(Descuento)
        .where(
            Descuento.id_permiso == id_permiso, Descuento.tipo_movimiento == "DESCUENTO"
        )
        .order_by(Descuento.id_descuento)
    )
    return list((await sesion.scalars(consulta)).all())


# función para consultar total descontado
async def consultar_total_descontado(sesion: AsyncSession, id_empleado: int):

    bruto = await sesion.scalar(
        select(func.coalesce(func.sum(Descuento.dias_descontados), 0)).where(
            Descuento.id_empleado == id_empleado,
            Descuento.id_permiso.is_not(None),
            Descuento.tipo_movimiento == "DESCUENTO",
        )
    )
    return bruto - await consultar_total_reintegrado_horas(sesion, id_empleado)
