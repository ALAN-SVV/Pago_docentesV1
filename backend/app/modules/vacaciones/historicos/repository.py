# Consultas compartidas sin dependencias de servicios: evita importaciones circulares.
from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.aprobaciones.model import Aprobacion
from app.modules.vacaciones.permisos.model import Permiso
from app.modules.vacaciones.reservas.model import Descuento, Reserva
from app.modules.vacaciones.saldos.model import Saldo
from app.modules.vacaciones.solicitudes.model import Solicitud


# función para consultar apertura
async def consultar_apertura(sesion: AsyncSession, id_empleado: int):
    valores = await sesion.scalars(
        select(Saldo.apertura_historica).where(Saldo.id_empleado == id_empleado)
    )
    aperturas = [v for v in valores if v is not None]
    if len(aperturas) > 1:
        raise HTTPException(
            409, "Hay más de una apertura para este empleado; revisa la integridad."
        )
    return aperturas[0] if aperturas else None


# función para contar actividad
async def contar_actividad(sesion: AsyncSession, id_empleado: int):
    resultado = {}
    for modelo in (Solicitud, Permiso, Reserva, Descuento, Aprobacion):
        resultado[modelo.__tablename__] = await sesion.scalar(
            select(func.count())
            .select_from(modelo)
            .where(modelo.id_empleado == id_empleado)
        )
    return resultado


# función para validar fecha posterior
async def validar_fecha_posterior(sesion: AsyncSession, id_empleado: int, fecha):
    apertura = await consultar_apertura(sesion, id_empleado)
    if apertura and fecha <= date.fromisoformat(apertura["datos"]["fecha_corte"]):
        raise HTTPException(
            409,
            "La fecha debe ser posterior al corte histórico; ese consumo ya pertenece a la apertura.",
        )


# consultamos los consumos y devoluciones para compararlos con el saldo de apertura
async def consultar_movimientos_por_empleado(
    sesion: AsyncSession, id_empleado: int
) -> list[Descuento]:
    consulta = select(Descuento).where(Descuento.id_empleado == id_empleado)
    resultado = await sesion.scalars(consulta)
    return list(resultado.all())
