"""Validaciones de datos de entrada y salida del modulo de Admisiones."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CrmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_crm: int
    id_persona: int | None
    id_responsable: int | None
    origen: str | None
    estado: str | None
    fecha_registro: datetime | None
    observacion: str | None



class CrmCreate(BaseModel):
    cedula: str
    nombres: str
    apellidos: str
    correo: str | None = None
    telefono: str | None = None
    origen: str
    observacion: str | None = None

class CrmUpdate(BaseModel):
    origen: str | None = None
    observacion: str | None = None

class CrmAsignar(BaseModel):
    id_responsable: int


class CrmEstado(BaseModel):
    estado: str
    motivo: str | None = None


class SeguimientoCreate(BaseModel):
    id_responsable: int
    tipo_contacto: str
    descripcion: str
    resultado: str | None = None
    proxima_accion: str | None = None
    fecha_proxima_accion: date | None = None


class SeguimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_seguimiento: int
    id_crm: int | None
    id_responsable: int | None
    tipo_contacto: str | None
    descripcion: str | None
    resultado: str | None
    proxima_accion: str | None
    fecha_proxima_accion: date | None
    fecha_registro: datetime | None


class ConversionCreate(BaseModel):
    carrera_interes: str
    periodo_interes: str


class AspiranteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_aspirante: int
    id_persona: int | None
    id_crm: int | None
    carrera_interes: str | None
    periodo_interes: str | None
    estado: str | None
    fecha_registro: datetime | None