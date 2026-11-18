from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session as obtener_sesion
from app.modules.vacaciones.aprobaciones.schema import (
    AprobacionCrear,
    AprobacionRespuesta,
    RechazoCrear,
)
from app.modules.vacaciones.aprobaciones.service import (
    aprobar_solicitud,
    obtener_aprobaciones_por_solicitud,
    rechazar_solicitud,
)

# ruta para conectar con el main y uso de prefix para saber la ruta de este controlador
router = APIRouter(
    prefix="/solicitudes",
    tags=["Aprobaciones"],
)


# el router get se usara para indicar que esta peticion solo podra realizar lecturas, consultas y traer datos.
@router.get(
    # se solicita el id del empleado
    "/{id_solicitud}/aprobaciones",
    # respose se usa para indicar que la list ue resiva tiene que seguir el modelo definido en aprobacionrespuesta
    response_model=list[AprobacionRespuesta],
    # documentacion de fast api
    summary="Consultar decisiones de una solicitud",
    description=(
        "Consulta desiciones registradas. de la mas reciente"
        "Operacion que no aprueba o rechaza una solicitud."
    ),
)

# se va a realizar la validacion de las id con annotated.
# ge es usado para indicar que el dato tiene que ser mayor o igual a 1
# le es para indicar que el dato tiene que ser mnor o igual al digito colocado
# obtenemos la secion que configuramos en el databes y list es solo para que respete el formato
async def consultar_aprobaciones(
    id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> list[AprobacionRespuesta]:
    # funcion asyn para obtener una sesion temporal y list para indicar que se va a retornar una lista con el siguiente formato
    aprobaciones = await obtener_aprobaciones_por_solicitud(sesion, id_solicitud)
    return aprobaciones


# creamos un registro de decisión y actualizamos la solicitud
@router.post(
    "/{id_solicitud}/rechazo",
    response_model=AprobacionRespuesta,
    status_code=201,
    summary="Rechazar una solicitud de vacaciones pendiente",
    description=(
        "Registra el aprobador, la fecha y el motivo obligatorio del rechazo. "
        "Cambia la solicitud a RECHAZADA y libera su reserva en la misma transacción. "
        "Solo admite solicitudes PENDIENTES sin decisiones anteriores. "
        "Uso local de desarrollo: el id_aprobador se ingresa manualmente; "
        "la identidad y la autorización por rol se integrarán con Core."
    ),
    responses={
        404: {"description": "La solicitud o el empleado aprobador no existe."},
        409: {
            "description": "La solicitud no admite rechazo o existe un conflicto de referencias."
        },
    },
)
# funcion para registrar el rechazo, con validaciones de tamaño del id
async def registrar_rechazo(
    id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: RechazoCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> AprobacionRespuesta:
    return await rechazar_solicitud(sesion, id_solicitud, datos)


# ruta para registrar la aprobacion final y descontar los dias reservados
@router.post(
    "/{id_solicitud}/aprobacion",
    response_model=AprobacionRespuesta,
    status_code=201,
    summary="Registrar aprobación final de Talento Humano y descontar la reserva",
    description="Operación local con aprobador habilitado en la base. Identidad autenticada pendiente de Core. Las firmas previas se verifican fuera de esta API.",
    responses={
        403: {"description": "Responsable no habilitado."},
        409: {"description": "Estado o reserva incompatible."},
    },
)

# funcion async para recibir la peticion de aprobacion
# recibimos el aprobador y la observacion usando el esquema de validacion
async def registrar_aprobacion(
    id_solicitud: Annotated[int, Path(ge=1, le=9223372036854775807)],
    datos: AprobacionCrear,
    sesion: Annotated[AsyncSession, Depends(obtener_sesion)],
) -> AprobacionRespuesta:
    # llamamos al servicio que valida, aprueba y descuenta la reserva
    # esperamos el resultado y devolvemos la respuesta
    return await aprobar_solicitud(sesion, id_solicitud, datos)
