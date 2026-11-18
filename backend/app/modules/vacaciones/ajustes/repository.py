from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.aprobaciones.model import Aprobacion
from app.modules.vacaciones.reservas.model import Descuento


# función para consultar ajuste documento
async def consultar_ajuste_documento(sesion: AsyncSession, identificador, horas=False):
    campo = Aprobacion.id_permiso if horas else Aprobacion.id_solicitud
    return await sesion.scalar(
        select(Aprobacion).where(
            campo == identificador,
            Aprobacion.tipo_intervencion.in_(["REVERSO", "CORRECCION"]),
        )
    )


# función para consultar historial
async def consultar_historial(sesion: AsyncSession, id_empleado: int):
    return list(
        (
            await sesion.scalars(
                select(Aprobacion)
                .where(
                    Aprobacion.id_empleado == id_empleado,
                    Aprobacion.tipo_intervencion.in_(["REVERSO", "CORRECCION"]),
                )
                .order_by(Aprobacion.id_aprobacion)
            )
        ).all()
    )


# función para consultar reintegros
async def consultar_reintegros(sesion: AsyncSession, id_aprobacion: int):
    return list(
        (
            await sesion.scalars(
                select(Descuento)
                .where(
                    Descuento.id_aprobacion == id_aprobacion,
                    Descuento.tipo_movimiento == "REINTEGRO",
                )
                .order_by(Descuento.id_descuento)
            )
        ).all()
    )


# función para consultar total reintegrado horas
async def consultar_total_reintegrado_horas(sesion: AsyncSession, id_empleado: int):
    return await sesion.scalar(
        select(func.coalesce(func.sum(Descuento.dias_descontados), 0)).where(
            Descuento.id_empleado == id_empleado,
            Descuento.id_permiso.is_not(None),
            Descuento.tipo_movimiento == "REINTEGRO",
        )
    )


# consultamos cuánto queda por devolver de cada descuento original
async def consultar_descuentos_reintegrables(
    sesion: AsyncSession, id_empleado: int, id_solicitud: int | None = None
):
    # Consumos originales menos sus devoluciones. En horas: los últimos primero.
    devueltos = (
        select(
            Descuento.id_descuento_origen.label("id"),
            func.sum(Descuento.dias_descontados).label("dias"),
        )
        .where(Descuento.tipo_movimiento == "REINTEGRO")
        .group_by(Descuento.id_descuento_origen)
        .subquery()
    )
    consulta = (
        select(Descuento, func.coalesce(devueltos.c.dias, 0))
        .outerjoin(devueltos, devueltos.c.id == Descuento.id_descuento)
        .where(
            Descuento.id_empleado == id_empleado,
            Descuento.tipo_movimiento == "DESCUENTO",
        )
    )
    if id_solicitud is None:
        consulta = consulta.where(Descuento.id_permiso.is_not(None)).order_by(
            Descuento.fecha_registro.desc(), Descuento.id_descuento.desc()
        )
    else:
        consulta = consulta.where(Descuento.id_solicitud == id_solicitud).order_by(
            Descuento.id_descuento
        )
    return [
        (d, d.dias_descontados - Decimal(devuelto))
        for d, devuelto in (await sesion.execute(consulta)).all()
    ]
