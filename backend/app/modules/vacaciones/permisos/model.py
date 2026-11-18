from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

# relacionamos la clase con los campos de la tabla en la base de datos
class Permiso(Base):
    # Un intervalo de ausencia del mismo día, a cargo de vacaciones.
    __tablename__ = "permisos"
    __table_args__ = {"schema": "vacaciones"}
    id_permiso: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Conservamos los nulos antiguos para no reinterpretar el historial.
    id_empleado: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    hora_inicio: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_fin: Mapped[time | None] = mapped_column(Time, nullable=True)
    total_horas: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Minutos enteros = cantidad exacta. total_horas solo muestra dos decimales.
    total_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gestionado: Mapped[bool] = mapped_column(Boolean, default=False)
    observacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_registro: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_cierre: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    id_aprobador: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    observacion_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Solo al aprobar: dejan constancia de cada conversión de 480 minutos.
    minutos_restantes_antes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutos_restantes_despues: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    dias_convertidos: Mapped[int | None] = mapped_column(Integer, nullable=True)
