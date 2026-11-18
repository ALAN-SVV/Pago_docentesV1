"""Logica de negocio del modulo de Admisiones."""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.audit_logging import registrar_auditoria
from app.modules.admisiones.models import Aspirante, Crm, CrmSeguimiento
from app.modules.core.models.core import Empleado, Persona
from app.modules.admisiones.schemas import (
    ConversionCreate,
    CrmAsignar,
    CrmCreate,
    CrmEstado,
    CrmUpdate,
    SeguimientoCreate,
)


async def listar_crm(db: AsyncSession) -> list[Crm]:
    resultado = await db.execute(select(Crm).order_by(Crm.id_crm))
    return list(resultado.scalars().all())


async def _auditar(
    db: AsyncSession, id_usuario: int, accion: str, tabla: str, id_registro: int
) -> None:
    await registrar_auditoria(
        db,
        id_usuario=id_usuario,
        modulo="ADMISION",
        accion=accion,
        tabla_afectada=tabla,
        id_registro=id_registro,
    )


async def registrar_crm(
    db: AsyncSession, datos: CrmCreate, id_usuario: int
) -> Crm:
    # Buscar si la persona ya existe por su cedula
    resultado = await db.execute(select(Persona).where(Persona.cedula == datos.cedula))
    persona = resultado.scalars().first()

    if persona is None:
        # Caso 1: la cedula es nueva, se crea la persona
        persona = Persona(
            cedula=datos.cedula,
            nombres=datos.nombres,
            apellidos=datos.apellidos,
            correo=datos.correo,
            telefono=datos.telefono,
            estado=True,
        )
        db.add(persona)
        await db.flush()
    else:
        # Caso 2 o 3: la persona existe, se revisa si ya tiene registro en el CRM
        resultado = await db.execute(select(Crm).where(Crm.id_persona == persona.id_persona))
        if resultado.scalars().first() is not None:
            # Caso 3: ya es prospecto, no se registra de nuevo
            raise HTTPException(status_code=409, detail="Esta cedula ya esta registrada como prospecto")

    # Caso 1 y 2: se crea el registro en el CRM
    crm = Crm(
        id_persona=persona.id_persona,
        origen=datos.origen,
        estado="Nuevo",
        fecha_registro=datetime.now(),
        observacion=datos.observacion,
    )
    db.add(crm)
    await db.flush()
    await _auditar(db, id_usuario, "REGISTRAR_PROSPECTO", "admision.crm", crm.id_crm)
    await db.refresh(crm)
    return crm


async def obtener_crm(db: AsyncSession, id_crm: int) -> Crm:
    crm = await db.get(Crm, id_crm)
    if crm is None:
        raise HTTPException(status_code=404, detail="Prospecto no encontrado")
    return crm


async def actualizar_crm(
    db: AsyncSession, id_crm: int, datos: CrmUpdate, id_usuario: int
) -> Crm:
    crm = await obtener_crm(db, id_crm)

    # RN-07: un prospecto en estado final no se puede editar
    if crm.estado in ("Convertido", "Perdido"):
        raise HTTPException(status_code=400, detail="No se puede editar un prospecto en estado final")

    if datos.origen is not None:
        crm.origen = datos.origen
    if datos.observacion is not None:
        crm.observacion = datos.observacion

    await _auditar(db, id_usuario, "EDITAR_PROSPECTO", "admision.crm", crm.id_crm)
    await db.refresh(crm)
    return crm


async def asignar_responsable(
    db: AsyncSession, id_crm: int, datos: CrmAsignar, id_usuario: int
) -> Crm:
    # 1. El prospecto debe existir (obtener_crm ya responde 404)
    crm = await obtener_crm(db, id_crm)

    # 2. RN-07: no se asigna asesor a un prospecto en estado final
    if crm.estado in ("Convertido", "Perdido"):
        raise HTTPException(status_code=400, detail="No se puede asignar asesor a un prospecto en estado final")

    # 3. El empleado debe existir
    empleado = await db.get(Empleado, datos.id_responsable)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Asesor no encontrado")

    # 4. El empleado debe estar activo
    if not empleado.estado:
        raise HTTPException(status_code=400, detail="El asesor no esta activo")

    crm.id_responsable = empleado.id_empleado
    await _auditar(db, id_usuario, "ASIGNAR_ASESOR", "admision.crm", crm.id_crm)
    await db.refresh(crm)
    return crm


# Estados a los que puede pasar un prospecto segun su estado actual
TRANSICIONES = {
    "Nuevo": ["Contactado", "Perdido"],
    "Contactado": ["Interesado", "Perdido"],
    "Interesado": ["Perdido"],
}


async def cambiar_estado(
    db: AsyncSession, id_crm: int, datos: CrmEstado, id_usuario: int
) -> Crm:
    crm = await obtener_crm(db, id_crm)

    # Revisar si el cambio esta permitido
    permitidos = TRANSICIONES.get(crm.estado, [])
    if datos.estado not in permitidos:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede pasar de {crm.estado} a {datos.estado}",
        )

    # Para marcar como Perdido se necesita un motivo
    if datos.estado == "Perdido":
        if not datos.motivo:
            raise HTTPException(status_code=400, detail="Debe indicar el motivo para marcar como Perdido")
        if crm.observacion:
            crm.observacion = crm.observacion + " | Motivo de perdida: " + datos.motivo
        else:
            crm.observacion = "Motivo de perdida: " + datos.motivo

    crm.estado = datos.estado
    await _auditar(db, id_usuario, "CAMBIAR_ESTADO", "admision.crm", crm.id_crm)
    await db.refresh(crm)
    return crm


TIPOS_CONTACTO = ["Llamada", "WhatsApp", "Correo", "Visita"]


async def registrar_seguimiento(
    db: AsyncSession, id_crm: int, datos: SeguimientoCreate, id_usuario: int
) -> CrmSeguimiento:
    crm = await obtener_crm(db, id_crm)

    # No se registran contactos en un prospecto en estado final
    if crm.estado in ("Convertido", "Perdido"):
        raise HTTPException(status_code=400, detail="No se puede registrar seguimiento en un prospecto en estado final")

    # El tipo de contacto debe ser uno de los permitidos
    if datos.tipo_contacto not in TIPOS_CONTACTO:
        raise HTTPException(status_code=400, detail="Tipo de contacto no valido. Use: Llamada, WhatsApp, Correo o Visita")

    # El asesor debe existir
    empleado = await db.get(Empleado, datos.id_responsable)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Asesor no encontrado")

    seguimiento = CrmSeguimiento(
        id_crm=crm.id_crm,
        id_responsable=datos.id_responsable,
        tipo_contacto=datos.tipo_contacto,
        descripcion=datos.descripcion,
        resultado=datos.resultado,
        proxima_accion=datos.proxima_accion,
        fecha_proxima_accion=datos.fecha_proxima_accion,
        fecha_registro=datetime.now(),
    )
    db.add(seguimiento)

    # RN-03: con el primer contacto, un prospecto Nuevo pasa a Contactado
    if crm.estado == "Nuevo":
        crm.estado = "Contactado"

    await db.flush()
    await _auditar(
        db,
        id_usuario,
        "REGISTRAR_SEGUIMIENTO",
        "admision.crm_seguimiento",
        seguimiento.id_seguimiento,
    )
    await db.refresh(seguimiento)
    return seguimiento


async def listar_seguimientos(db: AsyncSession, id_crm: int) -> list[CrmSeguimiento]:
    await obtener_crm(db, id_crm)
    resultado = await db.execute(
        select(CrmSeguimiento)
        .where(CrmSeguimiento.id_crm == id_crm)
        .order_by(CrmSeguimiento.fecha_registro)
    )
    return list(resultado.scalars().all())


async def convertir_aspirante(
    db: AsyncSession, id_crm: int, datos: ConversionCreate, id_usuario: int
) -> Aspirante:
    crm = await obtener_crm(db, id_crm)

    # RN-02: solo se convierte un prospecto Interesado
    if crm.estado != "Interesado":
        raise HTTPException(status_code=400, detail="Solo se puede convertir un prospecto en estado Interesado")

    # Seguridad extra: que no exista ya un aspirante creado desde este prospecto
    resultado = await db.execute(select(Aspirante).where(Aspirante.id_crm == crm.id_crm))
    if resultado.scalars().first() is not None:
        raise HTTPException(status_code=409, detail="Este prospecto ya fue convertido en aspirante")

    aspirante = Aspirante(
        id_persona=crm.id_persona,
        id_crm=crm.id_crm,
        carrera_interes=datos.carrera_interes,
        periodo_interes=datos.periodo_interes,
        estado="Registrado",
        fecha_registro=datetime.now(),
    )
    db.add(aspirante)

    # El prospecto termina su proceso en el CRM
    crm.estado = "Convertido"

    await db.flush()
    await _auditar(
        db,
        id_usuario,
        "CONVERTIR_PROSPECTO",
        "admision.aspirantes",
        aspirante.id_aspirante,
    )
    await db.refresh(aspirante)
    return aspirante