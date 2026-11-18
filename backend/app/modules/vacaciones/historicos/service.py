# Apertura única, revisión optimista y conciliación sin inventar documentos pasados.
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vacaciones.historicos import repository as repo
from app.modules.vacaciones.historicos.schema import AperturaCrear, PeriodoHistorico
from app.modules.vacaciones.permisos.contabilidad import consultar_acumulacion
from app.modules.vacaciones.permisos.service import validar_responsable
from app.modules.vacaciones.saldos import service as saldos
from app.modules.vacaciones.saldos.model import Saldo
from app.modules.vacaciones.saldos.repository import (
    consultar_datos_empleado,
    consultar_saldos_por_empleado,
)
from app.modules.vacaciones.solicitudes.repository import bloquear_empleado

CAMPOS = tuple(PeriodoHistorico.model_fields)


# guardamos una copia de los valores para poder revisar los cambios después
def capturar_saldos(filas):
    fotografias = []
    for saldo in filas:
        valores = {"id_saldo": saldo.id_saldo}
        for campo in CAMPOS:
            valor = getattr(saldo, campo)
            if valor is None:
                valores[campo] = None
            elif campo.startswith("dias_"):
                valores[campo] = format(valor, ".2f")
            else:
                valores[campo] = str(valor)
        fotografias.append(valores)
    return fotografias


# calculamos una huella para detectar si los datos cambiaron desde la revisión
def calcular_huella(valor):
    return hashlib.sha256(
        json.dumps(valor, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


# ordenamos los períodos y dejamos los días con dos decimales para comparar las cargas
def preparar_datos_apertura(datos):
    datos_apertura = AperturaCrear.model_validate(
        datos.model_dump(exclude={"huella_revision"})
    ).model_dump(mode="json")
    for periodo in datos_apertura["periodos"]:
        for campo in ("dias_asignados", "dias_utilizados", "dias_disponibles"):

            periodo[campo] = format(Decimal(periodo[campo]), ".2f")
    datos_apertura["periodos"].sort(key=lambda periodo: periodo["fecha_inicio_periodo"])
    return datos_apertura


# comparamos los períodos recibidos con los saldos y verificamos si se puede cargar la apertura
async def revisar(sesion: AsyncSession, id_empleado: int, datos):
    await bloquear_empleado(sesion, id_empleado)
    await validar_responsable(sesion, datos.id_responsable)
    empleado = await consultar_datos_empleado(sesion, id_empleado)
    ingreso = empleado["fecha_ingreso"]
    if ingreso is None or not ingreso <= datos.fecha_corte <= saldos.fecha_actual():
        raise HTTPException(
            422, "El corte debe estar entre el ingreso del empleado y hoy."
        )
    for periodo in datos.periodos:
        anios = periodo.fecha_inicio_periodo.year - ingreso.year
        if (
            anios < 0
            or periodo.fecha_inicio_periodo.year >= 9999
            or periodo.fecha_inicio_periodo != saldos.fecha_aniversario(ingreso, anios)
            or periodo.fecha_acreditacion
            != saldos.fecha_aniversario(ingreso, anios + 1)
            or periodo.fecha_fin_periodo
            != periodo.fecha_acreditacion - timedelta(days=1)
        ):
            raise HTTPException(
                422,
                "Las fechas históricas deben coincidir con los aniversarios de ingreso.",
            )
        if (
            periodo.fecha_acreditacion > datos.fecha_corte
            and periodo.dias_utilizados > 15
        ):
            raise HTTPException(
                422, "El período no acreditado supera los 15 días de anticipo."
            )
    filas = await consultar_saldos_por_empleado(sesion, id_empleado)
    apertura = await repo.consultar_apertura(sesion, id_empleado)
    actividad = await repo.contar_actividad(sesion, id_empleado)
    datos_json = preparar_datos_apertura(datos)
    # Igual petición devuelve el comprobante original incluso después de nuevas operaciones.
    repetida = apertura is not None and apertura["huella_datos"] == calcular_huella(
        datos_json
    )
    impedimentos = []
    if apertura and not repetida:
        impedimentos.append("El empleado ya tiene una apertura certificada.")
    if any(actividad.values()) and not repetida:
        impedimentos.append(
            "Hay documentos o movimientos; la apertura no puede sobrescribirlos."
        )
    existentes = {saldo.fecha_inicio_periodo: saldo for saldo in filas}
    recibidos = {periodo.fecha_inicio_periodo: periodo for periodo in datos.periodos}
    if any(inicio not in recibidos for inicio in existentes) and not repetida:
        impedimentos.append(
            "Incluye todos los períodos existentes; no se eliminan saldos ni se deducen fechas faltantes."
        )
    diferencias = []
    for inicio, periodo in recibidos.items():
        saldo = existentes.get(inicio)
        cambios = {
            campo: {
                "actual": str(getattr(saldo, campo)) if saldo else None,
                "propuesto": str(getattr(periodo, campo)),
            }
            for campo in CAMPOS
            if saldo is None or getattr(saldo, campo) != getattr(periodo, campo)
        }
        if cambios:
            diferencias.append(
                {
                    "inicio": inicio.isoformat(),
                    "id_saldo": saldo.id_saldo if saldo else None,
                    "campos": cambios,
                }
            )
    revision = calcular_huella(
        {
            "datos": datos_json,
            "saldos": capturar_saldos(filas),
            "actividad": actividad,
            "apertura": apertura,
            "ingreso": str(ingreso),
        }
    )
    return (
        {
            "puede_confirmar": not impedimentos,
            "repetida": repetida,
            "impedimentos": impedimentos,
            "diferencias": diferencias,
            "actividad": actividad,
            "huella_revision": revision,
            "apertura": apertura,
        },
        filas,
        datos_json,
    )


# devolvemos las diferencias encontradas para que se revisen antes de confirmar
async def previsualizar(sesion: AsyncSession, id_empleado: int, datos):
    async with sesion.begin():
        resultado, _, _ = await revisar(sesion, id_empleado, datos)
        return resultado


# revisamos nuevamente los datos y guardamos la apertura completa en una transacción
async def confirmar(sesion: AsyncSession, id_empleado: int, datos):
    try:
        async with sesion.begin():
            revision, filas, datos_json = await revisar(sesion, id_empleado, datos)
            if revision["repetida"]:
                return {"repetida": True, "apertura": revision["apertura"]}
            if not revision["puede_confirmar"]:
                raise HTTPException(409, revision["impedimentos"])
            if datos.huella_revision != revision["huella_revision"]:
                raise HTTPException(
                    409, "Los datos cambiaron desde la vista previa; vuelve a revisar."
                )
            antes = capturar_saldos(filas)
            por_inicio = {saldo.fecha_inicio_periodo: saldo for saldo in filas}
            guardados = []
            for periodo in sorted(
                datos.periodos, key=lambda periodo: periodo.fecha_inicio_periodo
            ):
                saldo = por_inicio.get(periodo.fecha_inicio_periodo)
                if saldo is None:
                    saldo = Saldo(id_empleado=id_empleado)
                    sesion.add(saldo)
                for campo in CAMPOS:
                    setattr(saldo, campo, getattr(periodo, campo))
                guardados.append(saldo)
            await sesion.flush()
            await saldos.obtener_resumen_saldo(sesion, id_empleado)
            apertura = {
                "version": 1,
                "id_empleado": id_empleado,
                "datos": datos_json,
                "huella_datos": calcular_huella(datos_json),
                "registrada_en": datetime.now(timezone.utc).isoformat(),
                "antes": antes,
                "despues": capturar_saldos(guardados),
            }
            # Una sola fila conserva el comprobante de apertura completo del empleado.
            guardados[0].apertura_historica = apertura
            await sesion.flush()
            return {"repetida": False, "apertura": apertura}
    except IntegrityError:
        raise HTTPException(
            409, "Conflicto al guardar la apertura; no se guardó ningún cambio."
        ) from None


# función para consultar
async def consultar(sesion: AsyncSession, id_empleado: int):
    async with sesion.begin():
        await bloquear_empleado(sesion, id_empleado)
        apertura = await repo.consultar_apertura(sesion, id_empleado)
        return {"id_empleado": id_empleado, "apertura": apertura}


# comparamos los saldos actuales con la apertura y los movimientos posteriores
async def conciliar(sesion: AsyncSession, id_empleado: int):

    async with sesion.begin():
        await bloquear_empleado(sesion, id_empleado)
        apertura = await repo.consultar_apertura(sesion, id_empleado)
        if not apertura:
            raise HTTPException(
                409, "No hay apertura certificada para establecer la base histórica."
            )
        iniciales = {periodo["id_saldo"]: periodo for periodo in apertura["despues"]}
        movimientos = await repo.consultar_movimientos_por_empleado(sesion, id_empleado)
        filas = await consultar_saldos_por_empleado(sesion, id_empleado)
        diferencias = []
        for saldo in filas:
            base = iniciales.get(saldo.id_saldo)
            inicial = Decimal(base["dias_utilizados"]) if base else Decimal(0)
            neto = sum(
                (
                    movimiento.dias_descontados
                    * (1 if movimiento.tipo_movimiento == "DESCUENTO" else -1)
                    for movimiento in movimientos
                    if movimiento.id_saldo == saldo.id_saldo
                ),
                Decimal(0),
            )
            esperado = inicial + neto
            if saldo.dias_utilizados != esperado:
                diferencias.append(
                    {
                        "id_saldo": saldo.id_saldo,
                        "campo": "dias_utilizados",
                        "actual": str(saldo.dias_utilizados),
                        "esperado": str(esperado),
                    }
                )
            if base:
                for campo in (
                    "dias_asignados",
                    "fecha_inicio_periodo",
                    "fecha_fin_periodo",
                    "fecha_acreditacion",
                ):
                    if str(getattr(saldo, campo)) != base[campo]:
                        diferencias.append(
                            {
                                "id_saldo": saldo.id_saldo,
                                "campo": campo,
                                "actual": str(getattr(saldo, campo)),
                                "esperado": base[campo],
                            }
                        )
        faltantes = sorted(set(iniciales) - {saldo.id_saldo for saldo in filas})
        errores = []
        try:
            await saldos.obtener_resumen_saldo(sesion, id_empleado)
        except HTTPException as error:
            errores.append(error.detail)
        try:
            await consultar_acumulacion(sesion, id_empleado)
        except HTTPException as error:
            errores.append(error.detail)
        return {
            "id_empleado": id_empleado,
            "coincide": not diferencias and not faltantes and not errores,
            "diferencias": diferencias,
            "saldos_faltantes": faltantes,
            "errores": errores,
        }
