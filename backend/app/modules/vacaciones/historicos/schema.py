# Datos certificados de apertura; no se deducen consumos de años anteriores.
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Cantidad = Annotated[Decimal, Field(ge=0, max_digits=6, decimal_places=2)]


# definimos los datos que recibimos y validamos para esta operación
class PeriodoHistorico(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    periodo: str = Field(min_length=1, max_length=20)
    fecha_inicio_periodo: date
    fecha_fin_periodo: date
    fecha_acreditacion: date
    dias_asignados: Cantidad
    dias_utilizados: Cantidad
    dias_disponibles: Cantidad

    # función para comprobar
    @model_validator(mode="after")
    def comprobar(self):
        if self.dias_asignados - self.dias_utilizados != self.dias_disponibles:
            raise ValueError(
                "Asignados menos utilizados debe coincidir con disponibles."
            )
        if (
            not self.fecha_inicio_periodo
            <= self.fecha_fin_periodo
            < self.fecha_acreditacion
        ):
            raise ValueError("Revisa el orden de las fechas del período.")
        return self


# definimos los datos que recibimos y validamos para esta operación
class AperturaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id_responsable: int = Field(ge=1, le=9223372036854775807)
    referencia: str = Field(min_length=1, max_length=150)
    motivo: str = Field(min_length=1, max_length=2000)
    fecha_corte: date
    minutos_sobrantes: int = Field(default=0, ge=0, lt=480, strict=True)
    periodos: list[PeriodoHistorico] = Field(min_length=1, max_length=100)

    # función para comprobar periodos
    @model_validator(mode="after")
    def comprobar_periodos(self):
        ordenados = sorted(self.periodos, key=lambda p: p.fecha_inicio_periodo)
        for a, b in zip(ordenados, ordenados[1:]):
            if b.fecha_inicio_periodo <= a.fecha_fin_periodo:
                raise ValueError("Hay períodos duplicados o superpuestos.")
        if any(p.fecha_inicio_periodo > self.fecha_corte for p in ordenados):
            raise ValueError("No se cargan períodos que no han comenzado al corte.")
        return self


# definimos los datos que recibimos y validamos para esta operación
class AperturaConfirmar(AperturaCrear):
    huella_revision: str = Field(pattern=r"^[0-9a-f]{64}$")


# datos que devolvemos al comparar la fuente con los saldos actuales
class RevisionHistoricaRespuesta(BaseModel):
    puede_confirmar: bool
    repetida: bool
    impedimentos: list[str]
    diferencias: list[dict]
    actividad: dict[str, int]
    huella_revision: str
    apertura: dict | None


# comprobante que devolvemos después de confirmar la apertura
class ConfirmacionHistoricaRespuesta(BaseModel):
    repetida: bool
    apertura: dict


# datos que devolvemos al consultar la apertura de un empleado
class AperturaHistoricaRespuesta(BaseModel):
    id_empleado: int
    apertura: dict | None


# diferencias encontradas entre la apertura, los movimientos y el saldo actual
class ConciliacionHistoricaRespuesta(BaseModel):
    id_empleado: int
    coincide: bool
    diferencias: list[dict]
    saldos_faltantes: list[int]
    errores: list[str]
