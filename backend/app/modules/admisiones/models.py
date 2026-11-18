"""Modelos propios del módulo de Admisiones."""
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.core.models.core import Empleado, Persona


class Crm(Base):
    __tablename__ = "crm"
    __table_args__ = {"schema": "admision"}

    id_crm: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_persona: Mapped[int | None] = mapped_column(BigInteger)
    id_responsable: Mapped[int | None] = mapped_column(BigInteger)
    origen: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str | None] = mapped_column(String(50))
    fecha_registro: Mapped[datetime | None] = mapped_column(DateTime)
    observacion: Mapped[str | None] = mapped_column(Text)



class CrmSeguimiento(Base):
    __tablename__ = "crm_seguimiento"
    __table_args__ = {"schema": "admision"}

    id_seguimiento: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_crm: Mapped[int | None] = mapped_column(BigInteger)
    id_responsable: Mapped[int | None] = mapped_column(BigInteger)
    tipo_contacto: Mapped[str | None] = mapped_column(String(50))
    descripcion: Mapped[str | None] = mapped_column(Text)
    resultado: Mapped[str | None] = mapped_column(String(100))
    proxima_accion: Mapped[str | None] = mapped_column(Text)
    fecha_proxima_accion: Mapped[date | None] = mapped_column(Date)
    fecha_registro: Mapped[datetime | None] = mapped_column(DateTime)


class Aspirante(Base):
    __tablename__ = "aspirantes"
    __table_args__ = {"schema": "admision"}

    id_aspirante: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_persona: Mapped[int | None] = mapped_column(BigInteger)
    id_crm: Mapped[int | None] = mapped_column(BigInteger)
    carrera_interes: Mapped[str | None] = mapped_column(String(150))
    periodo_interes: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str | None] = mapped_column(String(50))
    fecha_registro: Mapped[datetime | None] = mapped_column(DateTime)