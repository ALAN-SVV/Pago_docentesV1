from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session as obtener_sesion
from app.modules.vacaciones.historicos.schema import (
    AperturaConfirmar,
    AperturaCrear,
    AperturaHistoricaRespuesta,
    ConciliacionHistoricaRespuesta,
    ConfirmacionHistoricaRespuesta,
    RevisionHistoricaRespuesta,
)
from app.modules.vacaciones.historicos.service import conciliar as conciliar_servicio
from app.modules.vacaciones.historicos.service import confirmar as confirmar_servicio
from app.modules.vacaciones.historicos.service import consultar as consultar_servicio
from app.modules.vacaciones.historicos.service import (
    previsualizar as previsualizar_servicio,
)

router = APIRouter(
    prefix="/historicos",
    tags=["Apertura y conciliación histórica"],
)


# ruta para comparar la fuente histórica con los saldos, sin guardar
@router.post(
    "/{id_empleado}/revision",
    response_model=RevisionHistoricaRespuesta,
    summary="Comparar la fuente histórica con los saldos, sin guardar",
)
async def revisar(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: AperturaCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> RevisionHistoricaRespuesta:
    return await previsualizar_servicio(sesion, id_empleado, datos)


# ruta para confirmar una apertura histórica única
@router.post(
    "/{id_empleado}/apertura",
    response_model=ConfirmacionHistoricaRespuesta,
    summary="Confirmar una apertura histórica única",
)
async def confirmar(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: AperturaConfirmar,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> ConfirmacionHistoricaRespuesta:
    return await confirmar_servicio(sesion, id_empleado, datos)


# ruta para consultar el comprobante original de apertura
@router.get(
    "/{id_empleado}/apertura",
    response_model=AperturaHistoricaRespuesta,
    summary="Consultar el comprobante original de apertura",
)
async def consultar(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> AperturaHistoricaRespuesta:
    return await consultar_servicio(sesion, id_empleado)


# ruta para verificar apertura más movimientos contra los saldos actuales
@router.get(
    "/{id_empleado}/conciliacion",
    response_model=ConciliacionHistoricaRespuesta,
    summary="Verificar apertura más movimientos contra los saldos actuales",
)
async def conciliar(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> ConciliacionHistoricaRespuesta:
    return await conciliar_servicio(sesion, id_empleado)
