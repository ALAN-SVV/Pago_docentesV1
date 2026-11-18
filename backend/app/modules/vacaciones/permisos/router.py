from typing import Annotated
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session as obtener_sesion
from app.modules.vacaciones.aprobaciones.schema import AprobacionCrear, RechazoCrear
from app.modules.vacaciones.permisos.schema import (
    ConciliacionPermisoCrear,
    DescuentoHorasRespuesta,
    PermisoActualizar,
    PermisoCrear,
    PermisoRespuesta,
    ReservaHorasRespuesta,
    ResumenHorasRespuesta,
)
from app.modules.vacaciones.permisos.service import (
    actualizar_permiso as actualizar_permiso_servicio,
)
from app.modules.vacaciones.permisos.service import (
    cancelar_permiso as cancelar_permiso_servicio,
)
from app.modules.vacaciones.permisos.service import (
    conciliar_permiso as conciliar_permiso_servicio,
)
from app.modules.vacaciones.permisos.service import (
    crear_permiso as crear_permiso_servicio,
)
from app.modules.vacaciones.permisos.service import (
    decidir_permiso as decidir_permiso_servicio,
)
from app.modules.vacaciones.permisos.service import (
    obtener_descuentos as obtener_descuentos_servicio,
)
from app.modules.vacaciones.permisos.service import (
    obtener_permiso as obtener_permiso_servicio,
)
from app.modules.vacaciones.permisos.service import (
    obtener_permisos_por_empleado as obtener_permisos_por_empleado_servicio,
)
from app.modules.vacaciones.permisos.service import (
    obtener_reservas as obtener_reservas_servicio,
)
from app.modules.vacaciones.permisos.service import (
    obtener_resumen_horas as obtener_resumen_horas_servicio,
)

router = APIRouter(
    prefix="/permisos",
    tags=["Permisos por horas"],
)

# ruta para consultar permisos de un trabajador
@router.get(
    "/{id_empleado}",
    response_model=list[PermisoRespuesta],
    summary="Consultar permisos de un trabajador",
)
async def consultar_permisos(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> list[PermisoRespuesta]:
    return await obtener_permisos_por_empleado_servicio(sesion, id_empleado)


# ruta para registrar permiso a cargo de vacaciones
@router.post(
    "",
    response_model=PermisoRespuesta,
    status_code=201,
    summary="Registrar permiso a cargo de vacaciones",
)
async def crear_permiso(
    datos: PermisoCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> PermisoRespuesta:
    return await crear_permiso_servicio(sesion, datos)


# ruta para consultar acumulación, sobrante y reserva común
@router.get(
    "/{id_empleado}/resumen",
    response_model=ResumenHorasRespuesta,
    summary="Consultar acumulación, sobrante y reserva común",
)
async def resumen(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> ResumenHorasRespuesta:
    return await obtener_resumen_horas_servicio(sesion, id_empleado)


# ruta para consultar historial de la reserva común
@router.get(
    "/{id_empleado}/reservas",
    response_model=list[ReservaHorasRespuesta],
    summary="Consultar historial de la reserva común",
)
async def reservas(
    id_empleado: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> list[ReservaHorasRespuesta]:
    return await obtener_reservas_servicio(sesion, id_empleado)


# ruta para consultar un permiso
@router.get(
    "/detalle/{id_permiso}",
    response_model=PermisoRespuesta,
    summary="Consultar un permiso",
)
async def detalle(
    id_permiso: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> PermisoRespuesta:
    return await obtener_permiso_servicio(sesion, id_permiso)


# ruta para editar permiso pendiente y recalcular reserva
@router.put(
    "/detalle/{id_permiso}",
    response_model=PermisoRespuesta,
    summary="Editar permiso pendiente y recalcular reserva",
)
async def editar(
    id_permiso: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: PermisoActualizar,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> PermisoRespuesta:
    return await actualizar_permiso_servicio(sesion, id_permiso, datos)


# ruta para cancelar permiso pendiente
@router.patch(
    "/detalle/{id_permiso}/cancelar",
    response_model=PermisoRespuesta,
    summary="Cancelar permiso pendiente",
)
async def cancelar(
    id_permiso: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> PermisoRespuesta:
    return await cancelar_permiso_servicio(sesion, id_permiso)


# ruta para aprobar por Talento Humano y convertir horas
@router.post(
    "/detalle/{id_permiso}/aprobacion",
    response_model=PermisoRespuesta,
    summary="Aprobar por Talento Humano y convertir horas",
)
async def aprobar(
    id_permiso: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: AprobacionCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> PermisoRespuesta:
    return await decidir_permiso_servicio(sesion, id_permiso, datos, aprobar=True)


# ruta para rechazar por Talento Humano y liberar reserva
@router.post(
    "/detalle/{id_permiso}/rechazo",
    response_model=PermisoRespuesta,
    summary="Rechazar por Talento Humano y liberar reserva",
)
async def rechazar(
    id_permiso: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: RechazoCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> PermisoRespuesta:
    return await decidir_permiso_servicio(sesion, id_permiso, datos, aprobar=False)


# ruta para incorporar un permiso pendiente antiguo revisado
@router.post(
    "/detalle/{id_permiso}/conciliacion",
    response_model=PermisoRespuesta,
    summary="Incorporar un permiso pendiente antiguo revisado",
)
async def conciliar(
    id_permiso: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: ConciliacionPermisoCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> PermisoRespuesta:
    return await conciliar_permiso_servicio(sesion, id_permiso, datos)


# ruta para consultar períodos descontados por esta aprobación
@router.get(
    "/detalle/{id_permiso}/descuentos",
    response_model=list[DescuentoHorasRespuesta],
    summary="Consultar períodos descontados por esta aprobación",
)
async def descuentos(
    id_permiso: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> list[DescuentoHorasRespuesta]:
    return await obtener_descuentos_servicio(sesion, id_permiso)
