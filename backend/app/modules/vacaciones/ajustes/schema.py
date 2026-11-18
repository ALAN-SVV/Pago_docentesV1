from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.vacaciones.permisos.schema import PermisoActualizar
from app.modules.vacaciones.solicitudes.schema import SolicitudActualizar


# definimos los datos que recibimos y validamos para esta operación
class ReversoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id_responsable: int = Field(strict=True, ge=1, le=9223372036854775807)
    motivo: str = Field(min_length=1)


# definimos los datos que recibimos y validamos para esta operación
class CorreccionSolicitudCrear(ReversoCrear):
    datos: SolicitudActualizar


# definimos los datos que recibimos y validamos para esta operación
class CorreccionPermisoCrear(ReversoCrear):
    datos: PermisoActualizar


# definimos los datos que devolvemos en la respuesta
class ReintegroRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_descuento: int
    id_aprobacion: int
    id_empleado: int
    id_saldo: int
    id_solicitud: int | None
    id_permiso: int | None
    id_descuento_origen: int
    tipo_movimiento: str
    dias_descontados: Decimal
    fecha_registro: datetime


# definimos los datos que devolvemos en la respuesta
class AjusteRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_aprobacion: int
    id_empleado: int
    id_aprobador: int
    tipo_intervencion: str
    decision: str
    observacion: str
    fecha: datetime
    id_solicitud: int | None
    id_permiso: int | None
    id_solicitud_nueva: int | None
    id_permiso_nuevo: int | None
    antes: dict
    despues: dict
    reintegros: list[ReintegroRespuesta] = Field(default_factory=list)
