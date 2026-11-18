"""Endpoints de la API del modulo de Admisiones."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.admisiones import service
from app.modules.admisiones.schemas import (
    AspiranteOut,
    ConversionCreate,
    CrmAsignar,
    CrmCreate,
    CrmEstado,
    CrmOut,
    CrmUpdate,
    SeguimientoCreate,
    SeguimientoOut,
)
from app.modules.core.models.core import Usuario

router = APIRouter(
    prefix="/admision",
    tags=["Admisiones"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/crm", response_model=list[CrmOut])
async def listar_crm(db: AsyncSession = Depends(get_db)):
    return await service.listar_crm(db)



@router.post("/crm", response_model=CrmOut, status_code=201)
async def registrar_crm(
    datos: CrmCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    return await service.registrar_crm(db, datos, usuario.id_usuario)



@router.get("/crm/{id_crm}", response_model=CrmOut)
async def obtener_crm(id_crm: int, db: AsyncSession = Depends(get_db)):
    return await service.obtener_crm(db, id_crm)


@router.put("/crm/{id_crm}", response_model=CrmOut)
async def actualizar_crm(
    id_crm: int,
    datos: CrmUpdate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    return await service.actualizar_crm(db, id_crm, datos, usuario.id_usuario)


@router.put("/crm/{id_crm}/asignar", response_model=CrmOut)
async def asignar_responsable(
    id_crm: int,
    datos: CrmAsignar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    return await service.asignar_responsable(db, id_crm, datos, usuario.id_usuario)


@router.put("/crm/{id_crm}/estado", response_model=CrmOut)
async def cambiar_estado(
    id_crm: int,
    datos: CrmEstado,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    return await service.cambiar_estado(db, id_crm, datos, usuario.id_usuario)


@router.post("/crm/{id_crm}/seguimientos", response_model=SeguimientoOut, status_code=201)
async def registrar_seguimiento(
    id_crm: int,
    datos: SeguimientoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    return await service.registrar_seguimiento(
        db, id_crm, datos, usuario.id_usuario
    )


@router.get("/crm/{id_crm}/seguimientos", response_model=list[SeguimientoOut])
async def listar_seguimientos(id_crm: int, db: AsyncSession = Depends(get_db)):
    return await service.listar_seguimientos(db, id_crm)



@router.post("/crm/{id_crm}/convertir", response_model=AspiranteOut, status_code=201)
async def convertir_aspirante(
    id_crm: int,
    datos: ConversionCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    return await service.convertir_aspirante(db, id_crm, datos, usuario.id_usuario)