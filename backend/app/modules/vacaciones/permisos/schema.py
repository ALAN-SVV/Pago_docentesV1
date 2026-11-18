from datetime import date, datetime, time
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class PermisoDatos(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    fecha: date
    hora_inicio: time
    hora_fin: time
    motivo: str = Field(min_length=1)

    @field_validator("hora_inicio", "hora_fin")
    @classmethod
    def validar_hora_local(cls, valor: time) -> time:
        if valor.tzinfo is not None or valor.second or valor.microsecond:
            raise ValueError("Usa horas locales HH:MM, sin zona horaria ni segundos distintos de cero.")
        return valor

    @model_validator(mode="after")
    def validar_intervalo(self):
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("hora_fin debe ser posterior a hora_inicio dentro de la misma fecha.")
        return self


class PermisoCrear(PermisoDatos):
    id_empleado: int = Field(strict=True, ge=1, le=9223372036854775807)


class PermisoActualizar(PermisoDatos):
    pass


class ConciliacionPermisoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_responsable: int = Field(strict=True, ge=1, le=9223372036854775807)

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# definimos los datos que recibimos y validamos para esta operación
class PermisoDatos(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    fecha: date
    hora_inicio: time
    hora_fin: time
    motivo: str = Field(min_length=1)

    # función para validar hora local
    @field_validator("hora_inicio", "hora_fin")
    @classmethod
    def validar_hora_local(cls, valor: time) -> time:
        if valor.tzinfo is not None or valor.second or valor.microsecond:
            raise ValueError(
                "Usa horas locales HH:MM, sin zona horaria ni segundos distintos de cero."
            )
        return valor

    # función para validar intervalo
    @model_validator(mode="after")
    def validar_intervalo(self):
        if self.hora_fin <= self.hora_inicio:
            raise ValueError(
                "hora_fin debe ser posterior a hora_inicio dentro de la misma fecha."
            )
        return self


# definimos los datos que recibimos y validamos para esta operación
class PermisoCrear(PermisoDatos):
    id_empleado: int = Field(strict=True, ge=1, le=9223372036854775807)


# definimos los datos que recibimos y validamos para esta operación
class PermisoActualizar(PermisoDatos):
    pass


# definimos los datos que recibimos y validamos para esta operación
class ConciliacionPermisoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_responsable: int = Field(strict=True, ge=1, le=9223372036854775807)


# definimos los datos que devolvemos en la respuesta
class PermisoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_permiso: int
    id_empleado: int | None
    fecha: date | None
    hora_inicio: time | None
    hora_fin: time | None
    total_horas: Decimal | None
    motivo: str | None
    estado: str | None
    total_minutos: int | None
    gestionado: bool
    observacion: str | None
    fecha_registro: datetime | None
    fecha_cierre: datetime | None
    id_aprobador: int | None
    observacion_decision: str | None
    minutos_restantes_antes: int | None
    minutos_restantes_despues: int | None
    dias_convertidos: int | None


# definimos los datos que devolvemos en la respuesta
class ReservaHorasRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_reserva: int
    id_empleado: int
    id_saldo: int
    id_permiso_cambio: int
    id_permiso_cierre: int | None
    dias_reservados: Decimal
    es_anticipo: bool
    estado: str
    fecha_registro: datetime
    fecha_cierre: datetime | None


# definimos los datos que devolvemos en la respuesta
class DescuentoHorasRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_descuento: int
    id_empleado: int
    id_permiso: int
    id_saldo: int
    dias_descontados: Decimal
    es_anticipo: bool
    fecha_registro: datetime


# definimos los datos que devolvemos en la respuesta
class ResumenHorasRespuesta(BaseModel):
    minutos_apertura: int = 0
    id_empleado: int
    minutos_aprobados: int
    minutos_pendientes: int
    dias_descontados: int
    minutos_restantes: int
    horas_restantes: int
    minutos_adicionales: int
    dias_reservados: Decimal
    reservas_activas: list[ReservaHorasRespuesta]
    permisos_historicos_sin_conciliar: list[int]
    observacion: str = "Horas de permiso a cargo a vacaciones"
