from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.ajustes import repository as repo
from app.modules.vacaciones.ajustes.schema import AjusteRespuesta, ReintegroRespuesta
from app.modules.vacaciones.aprobaciones.model import Aprobacion
from app.modules.vacaciones.aprobaciones.repository import (
    consultar_aprobaciones_por_solicitud,
)
from app.modules.vacaciones.aprobaciones.schema import AprobacionCrear
from app.modules.vacaciones.calculos.service import calcular_dias_solicitud
from app.modules.vacaciones.permisos.contabilidad import (
    consultar_acumulacion,
    convertir_horas_aprobadas,
    recalcular_reserva_comun,
)
from app.modules.vacaciones.permisos.model import Permiso
from app.modules.vacaciones.permisos.repository import bloquear_permiso_y_empleado
from app.modules.vacaciones.permisos.schema import PermisoRespuesta
from app.modules.vacaciones.permisos.service import (
    OBSERVACION,
    asignar_intervalo,
    validar_cruces,
    validar_historial,
    validar_responsable,
)
from app.modules.vacaciones.reservas.model import Descuento
from app.modules.vacaciones.reservas.repository import (
    bloquear_saldos,
    consultar_reservas,
)
from app.modules.vacaciones.reservas.service import descontar_reservas, reservar_dias
from app.modules.vacaciones.saldos.service import obtener_resumen_saldo
from app.modules.vacaciones.solicitudes.model import Solicitud
from app.modules.vacaciones.solicitudes.repository import (
    bloquear_solicitud_y_empleado,
    existe_empleado,
)
from app.modules.vacaciones.solicitudes.schema import SolicitudRespuesta


# función para respuesta ajuste
async def respuesta_ajuste(sesion: AsyncSession, ajuste):
    r = AjusteRespuesta.model_validate(ajuste)
    r.reintegros = [
        ReintegroRespuesta.model_validate(x)
        for x in await repo.consultar_reintegros(sesion, ajuste.id_aprobacion)
    ]
    return r


# función para obtener historial
async def obtener_historial(sesion: AsyncSession, id_empleado: int):
    if not await existe_empleado(sesion, id_empleado):
        raise HTTPException(status_code=404, detail="El empleado no existe.")
    return [
        await respuesta_ajuste(sesion, a)
        for a in await repo.consultar_historial(sesion, id_empleado)
    ]


# guardamos el documento y sus saldos antes o después del ajuste
async def fotografia(sesion: AsyncSession, documento, horas):
    esquema = PermisoRespuesta if horas else SolicitudRespuesta
    resultado = {
        "documento": esquema.model_validate(documento).model_dump(mode="json"),
        "saldos": (
            await obtener_resumen_saldo(sesion, documento.id_empleado)
        ).model_dump(mode="json"),
    }
    if horas:
        aprobados, pendientes, dias, resto, _ = await consultar_acumulacion(
            sesion, documento.id_empleado
        )
        resultado["acumulacion"] = {
            "minutos_aprobados": aprobados,
            "minutos_pendientes": pendientes,
            "dias_descontados_netos": dias,
            "minutos_restantes": resto,
        }
    return resultado


# devolvemos los días al período del descuento original y registramos la devolución
async def reintegrar(sesion: AsyncSession, ajuste, saldos, descuentos, cantidad, horas):
    faltan = Decimal(cantidad)
    for descuento, reintegrable in descuentos:
        if reintegrable < 0 or reintegrable > descuento.dias_descontados:
            raise HTTPException(
                status_code=409, detail="El historial de reintegros es inconsistente."
            )
        if faltan <= 0:
            break
        tomar = min(faltan, reintegrable)
        if tomar <= 0:
            continue
        saldo = saldos.get(descuento.id_saldo)
        if saldo is None or saldo.dias_utilizados < tomar:
            raise HTTPException(
                status_code=409,
                detail="El saldo no respalda el reintegro. Revisa ajustes externos o datos históricos.",
            )
        saldo.dias_utilizados -= tomar
        saldo.dias_disponibles += tomar
        sesion.add(
            Descuento(
                id_aprobacion=ajuste.id_aprobacion,
                id_empleado=ajuste.id_empleado,
                id_saldo=saldo.id_saldo,
                id_solicitud=descuento.id_solicitud,
                id_permiso=descuento.id_permiso,
                id_descuento_origen=descuento.id_descuento,
                tipo_movimiento="REINTEGRO",
                dias_descontados=tomar,
                es_anticipo=descuento.es_anticipo,
                fecha_registro=datetime.now(timezone.utc),
            )
        )
        faltan -= tomar
    if faltan:
        raise HTTPException(
            status_code=409,
            detail="Faltan descuentos trazables para devolver los días.",
        )


# función para reemplazar solicitud
async def reemplazar_solicitud(sesion: AsyncSession, original, datos):
    dias = await calcular_dias_solicitud(sesion, datos.datos)
    nueva = Solicitud(
        id_empleado=original.id_empleado,
        tipo="VACACIONES",
        **datos.datos.model_dump(exclude={"dias_solicitados"}),
        dias_solicitados=dias,
        horas_solicitadas=Decimal("0.00"),
        estado="PENDIENTE",
        reserva_gestionada=False,
        fecha_solicitud=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    sesion.add(nueva)
    await sesion.flush()
    await reservar_dias(sesion, nueva)
    await descontar_reservas(sesion, nueva)
    nueva.estado = "APROBADA"
    sesion.add(
        Aprobacion(
            id_empleado=nueva.id_empleado,
            id_solicitud=nueva.id_solicitud,
            id_aprobador=datos.id_responsable,
            fecha=datetime.now(timezone.utc).replace(tzinfo=None),
            decision="APROBADA",
            observacion=datos.motivo,
        )
    )
    await sesion.flush()
    return nueva


# función para reemplazar permiso
async def reemplazar_permiso(sesion: AsyncSession, original, datos):
    nuevo = Permiso(
        id_empleado=original.id_empleado,
        estado="PENDIENTE",
        gestionado=True,
        observacion=OBSERVACION,
        fecha_registro=datetime.now(timezone.utc),
    )
    asignar_intervalo(nuevo, datos.datos)
    await validar_cruces(sesion, nuevo)
    sesion.add(nuevo)
    await sesion.flush()
    await recalcular_reserva_comun(sesion, nuevo)
    await convertir_horas_aprobadas(
        sesion,
        nuevo,
        AprobacionCrear(id_aprobador=datos.id_responsable, observacion=datos.motivo),
    )
    return nuevo


# validamos el responsable y guardamos la anulación o corrección en una sola transacción
async def ajustar_documento(
    sesion: AsyncSession, identificador, datos, horas=False, corregir=False
):
    # Revierte y, opcionalmente, aprueba un reemplazo en UNA transacción.
    try:
        async with sesion.begin():
            documento = (
                await bloquear_permiso_y_empleado(sesion, identificador)
                if horas
                else await bloquear_solicitud_y_empleado(sesion, identificador)
            )
            if documento is None:
                raise HTTPException(status_code=404, detail="La solicitud no existe.")
            await validar_responsable(sesion, datos.id_responsable)
            esperado = "APROBADO" if horas else "APROBADA"
            if documento.estado != esperado or await repo.consultar_ajuste_documento(
                sesion, identificador, horas
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Solo se ajustan documentos aprobados que no hayan sido anulados o sustituidos.",
                )
            if horas:
                if not documento.gestionado:
                    raise HTTPException(
                        status_code=409,
                        detail="El permiso histórico requiere conciliación antes de ajustar.",
                    )
                await validar_historial(sesion, documento.id_empleado)
            else:
                if documento.tipo != "VACACIONES" or not documento.reserva_gestionada:
                    raise HTTPException(
                        status_code=409,
                        detail="Se requieren vacaciones aprobadas con descuentos gestionados.",
                    )
                decisiones = await consultar_aprobaciones_por_solicitud(
                    sesion, identificador
                )
                if len(decisiones) != 1 or decisiones[0].decision != "APROBADA":
                    raise HTTPException(
                        status_code=409,
                        detail="Revisa la decisión de aprobación original.",
                    )
                if any(
                    r.estado == "ACTIVA"
                    for r in await consultar_reservas(sesion, identificador)
                ):
                    raise HTTPException(
                        status_code=409,
                        detail="La solicitud aprobada conserva reservas activas inconsistentes.",
                    )
            saldos = {
                s.id_saldo: s
                for s in await bloquear_saldos(sesion, documento.id_empleado)
            }
            antes = await fotografia(sesion, documento, horas)
            # Se completa como CORRECCION al enlazar el reemplazo; nada se confirma a mitad del flujo.
            ajuste = Aprobacion(
                id_empleado=documento.id_empleado,
                id_aprobador=datos.id_responsable,
                tipo_intervencion="REVERSO",
                decision="ANULADA",
                observacion=datos.motivo,
                fecha=datetime.now(timezone.utc).replace(tzinfo=None),
                id_solicitud=None if horas else identificador,
                id_permiso=identificador if horas else None,
                antes=antes,
                despues={},
            )
            sesion.add(ajuste)
            await sesion.flush()
            descuentos = await repo.consultar_descuentos_reintegrables(
                sesion, documento.id_empleado, None if horas else identificador
            )
            if horas:
                aprobados, _, dias, _, _ = await consultar_acumulacion(
                    sesion, documento.id_empleado
                )
                cantidad = dias - (aprobados - documento.total_minutos) // 480
            else:
                cantidad = documento.dias_solicitados
                if (
                    cantidad is None
                    or cantidad <= 0
                    or not descuentos
                    or any(
                        disponible != d.dias_descontados for d, disponible in descuentos
                    )
                    or sum((d.dias_descontados for d, _ in descuentos), Decimal("0.00"))
                    != cantidad
                ):
                    raise HTTPException(
                        status_code=409,
                        detail="Los descuentos no coinciden con el documento original.",
                    )
            await reintegrar(sesion, ajuste, saldos, descuentos, cantidad, horas)
            documento.estado = "ANULADO" if horas else "ANULADA"
            await sesion.flush()
            if horas:
                await recalcular_reserva_comun(sesion, documento)
            nuevo = None
            if corregir:
                nuevo = (
                    await reemplazar_permiso(sesion, documento, datos)
                    if horas
                    else await reemplazar_solicitud(sesion, documento, datos)
                )
                ajuste.tipo_intervencion = "CORRECCION"
                ajuste.decision = "CORREGIDA"
                if horas:
                    ajuste.id_permiso_nuevo = nuevo.id_permiso
                else:
                    ajuste.id_solicitud_nueva = nuevo.id_solicitud
            despues = await fotografia(sesion, documento, horas)
            if nuevo is not None:
                esquema = PermisoRespuesta if horas else SolicitudRespuesta
                despues["reemplazo"] = esquema.model_validate(nuevo).model_dump(
                    mode="json"
                )
            ajuste.despues = despues
            await sesion.flush()
            respuesta = await respuesta_ajuste(sesion, ajuste)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="El ajuste entra en conflicto con el historial o las referencias. No se guardó ningún cambio.",
        ) from None
    return respuesta
