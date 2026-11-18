from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session as obtener_sesion
from app.modules.vacaciones.ajustes.schema import (
    AjusteRespuesta,
    CorreccionPermisoCrear,
    CorreccionSolicitudCrear,
    ReversoCrear,
)
from app.modules.vacaciones.ajustes.service import ajustar_documento, obtener_historial

router = APIRouter(
    prefix="/ajustes",
    tags=["Ajustes auditados de Talento Humano"],
)


# recibimos la petición y llamamos al servicio para revertir solicitud
@router.post(
    "/solicitudes/{id_solicitud}/reverso",
    response_model=AjusteRespuesta,
    status_code=201,
)
async def revertir_solicitud(
    id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: ReversoCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> AjusteRespuesta:
    return await ajustar_documento(sesion, id_solicitud, datos)


# recibimos la petición y llamamos al servicio para corregir solicitud
@router.post(
    "/solicitudes/{id_solicitud}/correccion",
    response_model=AjusteRespuesta,
    status_code=201,
)
async def corregir_solicitud(
    id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: CorreccionSolicitudCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> AjusteRespuesta:
    return await ajustar_documento(sesion, id_solicitud, datos, corregir=True)


# recibimos la petición y llamamos al servicio para revertir permiso
@router.post(
    "/permisos/{id_permiso}/reverso", response_model=AjusteRespuesta, status_code=201
)
async def revertir_permiso(
    id_permiso: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: ReversoCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> AjusteRespuesta:
    return await ajustar_documento(sesion, id_permiso, datos, horas=True)


# recibimos la petición y llamamos al servicio para corregir permiso
@router.post(
    "/permisos/{id_permiso}/correccion", response_model=AjusteRespuesta, status_code=201
)
async def corregir_permiso(
    id_permiso: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: CorreccionPermisoCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> AjusteRespuesta:
    return await ajustar_documento(sesion, id_permiso, datos, horas=True, corregir=True)


# recibimos la petición y llamamos al servicio para historial
@router.get(
    "/empleados/{id_empleado}",
    response_model=list[AjusteRespuesta],
)
async def historial(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> list[AjusteRespuesta]:
    return await obtener_historial(sesion, id_empleado)
