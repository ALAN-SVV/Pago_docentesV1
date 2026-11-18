from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from test_calculos_periodos import db
from app.modules.vacaciones.saldos import service as saldos_service


def crear(c, fecha="2026-11-02", inicio="08:00", fin="11:00", empleado=1):
    return c.post("/permisos", json={"id_empleado": empleado, "fecha": fecha,
        "hora_inicio": inicio, "hora_fin": fin, "motivo": "Trámite personal"})


def aprobar(c, identificador, aprobador=2):
    return c.post(f"/permisos/detalle/{identificador}/aprobacion",
                  json={"id_aprobador": aprobador, "observacion": "Revisado por TH"})


def resumen(c, empleado=1):
    r = c.get(f"/permisos/{empleado}/resumen")
    assert r.status_code == 200, r.text
    return r.json()


def vacaciones(c, inicio="2026-12-01", fin="2026-12-01"):
    return c.post("/solicitudes", json={"id_empleado": 1, "fecha_inicio": inicio,
                  "fecha_fin": fin, "motivo": "Vacaciones de prueba"})


@pytest.mark.parametrize("orden", [(1, 2), (2, 1)])
def test_tres_mas_cinco_reserva_comun_y_aprobacion_en_cualquier_orden(db, orden):
    c, q, _ = db
    antes = q("SELECT * FROM vacaciones.saldos")
    a = crear(c)
    b = crear(c, fecha="2026-11-03", fin="13:00")
    assert a.status_code == b.status_code == 201
    assert a.json()["total_minutos"] == 180
    assert a.json()["observacion"] == "Horas de permiso a cargo a vacaciones"
    r = resumen(c)
    assert r["minutos_aprobados"] == 0 and r["minutos_pendientes"] == 480
    assert Decimal(r["dias_reservados"]) == 1
    saldo = c.get("/saldos/1/resumen").json()
    assert Decimal(saldo["total_disponible"]) == 17
    assert Decimal(saldo["total_reservado_por_horas"]) == 1
    assert q("SELECT * FROM vacaciones.saldos") == antes
    assert aprobar(c, orden[0]).status_code == 200
    assert resumen(c)["dias_descontados"] == 0
    assert aprobar(c, orden[1]).status_code == 200
    r = resumen(c)
    assert r["dias_descontados"] == 1 and r["minutos_restantes"] == 0
    assert Decimal(r["dias_reservados"]) == 0
    assert q("SELECT id_saldo,dias_descontados FROM vacaciones.descuentos_por_periodo WHERE id_permiso IS NOT NULL AND tipo_movimiento='DESCUENTO'") == [(20, 1)]
    assert q("SELECT dias_utilizados,dias_disponibles FROM vacaciones.saldos WHERE id_saldo=20") == [(13, 2)]
    conversion = c.get(f"/permisos/detalle/{orden[1]}").json()
    assert conversion["dias_convertidos"] == 1
    assert conversion["minutos_restantes_despues"] == 0
    assert len(c.get(f"/permisos/detalle/{orden[1]}/descuentos").json()) == 1


def test_diez_horas_descuenta_un_dia_y_conserva_dos(db):
    c, _, _ = db
    assert crear(c, fin="18:00").status_code == 201
    r = aprobar(c, 1)
    assert r.status_code == 200, r.text
    assert r.json()["minutos_restantes_antes"] == 0
    assert r.json()["minutos_restantes_despues"] == 120
    r = resumen(c)
    assert r["dias_descontados"] == 1 and r["horas_restantes"] == 2
    assert r["minutos_adicionales"] == 0


def test_sobrante_pasa_por_aniversario_y_generacion(db, monkeypatch):
    c, _, _ = db
    assert crear(c, fin="15:00").status_code == 201
    assert aprobar(c, 1).status_code == 200
    monkeypatch.setattr(saldos_service, "fecha_actual", lambda: date(2026, 11, 15))
    assert c.post("/saldos/1/periodos", json={"id_responsable": 2}).status_code == 200
    assert resumen(c)["minutos_restantes"] == 420
    assert crear(c, fecha="2026-11-16", fin="09:00").status_code == 201
    assert aprobar(c, 2).status_code == 200
    assert resumen(c)["dias_descontados"] == 1
    assert resumen(c)["minutos_restantes"] == 0


def test_minutos_sin_redondear_la_contabilidad(db):
    c, _, _ = db
    # 48 intervalos de 10 minutos. Sumar total_horas redondeadas daría 8.16 h.
    for n in range(48):
        desde = 8 * 60 + n * 10
        hasta = desde + 10
        r = crear(c, inicio=f"{desde//60:02}:{desde%60:02}", fin=f"{hasta//60:02}:{hasta%60:02}")
        assert r.status_code == 201, r.text
        assert Decimal(r.json()["total_horas"]) == Decimal("0.17")
        assert aprobar(c, r.json()["id_permiso"]).status_code == 200
    r = resumen(c)
    assert r["minutos_aprobados"] == 480
    assert r["dias_descontados"] == 1 and r["minutos_restantes"] == 0


def test_un_minuto_completa_el_dia(db):
    c, _, _ = db
    assert crear(c, fin="15:59").status_code == 201
    assert aprobar(c, 1).status_code == 200
    assert resumen(c)["minutos_restantes"] == 479
    assert crear(c, inicio="15:59", fin="16:00").status_code == 201
    assert aprobar(c, 2).status_code == 200
    assert resumen(c)["minutos_restantes"] == 0
    assert resumen(c)["dias_descontados"] == 1


@pytest.mark.parametrize("accion", ["cancelar", "rechazo"])
def test_cancelar_o_rechazar_libera_sin_borrar_sobrante(db, accion):
    c, q, _ = db
    assert crear(c).status_code == 201
    assert aprobar(c, 1).status_code == 200
    assert crear(c, fecha="2026-11-03", fin="13:00").status_code == 201
    assert Decimal(resumen(c)["dias_reservados"]) == 1
    if accion == "cancelar":
        r = c.patch("/permisos/detalle/2/cancelar")
    else:
        r = c.post("/permisos/detalle/2/rechazo", json={"id_aprobador": 2, "observacion": "No procede"})
    assert r.status_code == 200, r.text
    assert resumen(c)["minutos_restantes"] == 180
    assert Decimal(resumen(c)["dias_reservados"]) == 0
    assert q("SELECT count(*) FROM vacaciones.descuentos_por_periodo WHERE id_permiso IS NOT NULL AND tipo_movimiento='DESCUENTO'") == [(0,)]
    assert aprobar(c, 2).status_code == 409
    assert crear(c, fecha="2026-11-03", fin="13:00").status_code == 201
    assert aprobar(c, 3).status_code == 200
    assert resumen(c)["dias_descontados"] == 1


def test_editar_recalcula_y_saldo_insuficiente_revierte_todo(db):
    c, q, e = db
    e("UPDATE vacaciones.saldos SET dias_utilizados=dias_asignados,dias_disponibles=0")
    e("UPDATE vacaciones.saldos SET dias_utilizados=14,dias_disponibles=1 WHERE id_saldo=20")
    assert crear(c, fin="12:00").status_code == 201
    assert crear(c, fecha="2026-11-03", fin="12:00").status_code == 201
    antes = q("SELECT * FROM vacaciones.reservas_por_periodo WHERE ambito='HORAS'")
    datos = {"fecha": "2026-11-02", "hora_inicio": "08:00", "hora_fin": "20:00", "motivo": "Ampliación"}
    assert c.put("/permisos/detalle/1", json=datos).status_code == 409
    assert c.get("/permisos/detalle/1").json()["total_minutos"] == 240
    assert q("SELECT * FROM vacaciones.reservas_por_periodo WHERE ambito='HORAS'") == antes
    assert c.put("/permisos/detalle/1", json={**datos, "hora_fin": "09:00"}).status_code == 200
    assert Decimal(resumen(c)["dias_reservados"]) == 0


def test_una_aprobacion_no_puede_descontar_dos_veces_ni_reeditarse(db):
    c, q, _ = db
    assert crear(c, fin="16:00").status_code == 201
    assert aprobar(c, 1).status_code == 200
    assert aprobar(c, 1).status_code == 409
    assert c.patch("/permisos/detalle/1/cancelar").status_code == 409
    assert c.put("/permisos/detalle/1", json={"fecha": "2026-11-03", "hora_inicio": "08:00", "hora_fin": "10:00", "motivo": "Cambio"}).status_code == 409
    assert q("SELECT count(*) FROM vacaciones.descuentos_por_periodo WHERE id_permiso IS NOT NULL AND tipo_movimiento='DESCUENTO'") == [(1,)]


@pytest.mark.parametrize("aprobador,codigo", [(1, 403), (999, 404)])
def test_responsable_habilitado_y_rollback(db, aprobador, codigo):
    c, q, _ = db
    assert crear(c, fin="16:00").status_code == 201
    assert aprobar(c, 1, aprobador).status_code == codigo
    assert q("SELECT estado,id_aprobador FROM vacaciones.permisos") == [("PENDIENTE", None)]
    assert Decimal(resumen(c)["dias_reservados"]) == 1


@pytest.mark.parametrize("cambio", [
    {"hora_fin": "07:59"}, {"hora_fin": "08:00"}, {"hora_inicio": "08:00:01"},
    {"hora_inicio": "08:00:00.000001"}, {"hora_fin": "11:00+00:00"},
    {"hora_fin": "24:00"}, {"fecha": "2026-02-30"}, {"motivo": "  "},
    {"total_horas": 3}, {"total_minutos": 180}, {"estado": "APROBADO"},
    {"gestionado": True}, {"id_empleado": True}, {"id_empleado": 0},
])
def test_validacion_no_acepta_totales_o_estados_del_cliente(db, cambio):
    c, q, _ = db
    datos = {"id_empleado": 1, "fecha": "2026-11-02", "hora_inicio": "08:00", "hora_fin": "11:00", "motivo": "Prueba"}
    assert c.post("/permisos", json={**datos, **cambio}).status_code == 422
    assert q("SELECT count(*) FROM vacaciones.permisos") == [(0,)]


def test_intervalos_superpuestos_y_contiguos(db):
    c, _, _ = db
    assert crear(c).status_code == 201
    assert crear(c, inicio="10:59", fin="12:00").status_code == 409
    assert crear(c, inicio="11:00", fin="12:00").status_code == 201
    assert crear(c, fecha="2026-11-03").status_code == 201


@pytest.mark.parametrize("primero", ["permiso", "vacaciones"])
def test_cruce_entre_permisos_y_vacaciones_en_ambas_direcciones(db, primero):
    c, _, _ = db
    if primero == "permiso":
        assert crear(c).status_code == 201
        assert vacaciones(c, "2026-11-01", "2026-11-03").status_code == 409
        assert aprobar(c, 1).status_code == 200
        assert vacaciones(c, "2026-11-02", "2026-11-02").status_code == 409
    else:
        assert vacaciones(c, "2026-11-01", "2026-11-03").status_code == 201
        assert crear(c).status_code == 409


def test_reserva_horas_impide_gastar_el_mismo_dia_en_vacaciones(db):
    c, _, e = db
    e("UPDATE vacaciones.saldos SET dias_utilizados=dias_asignados,dias_disponibles=0")
    e("UPDATE vacaciones.saldos SET dias_utilizados=14,dias_disponibles=1 WHERE id_saldo=20")
    assert crear(c, fin="16:00").status_code == 201
    assert vacaciones(c).status_code == 409
    assert c.patch("/permisos/detalle/1/cancelar").status_code == 200
    r = vacaciones(c)
    assert r.status_code == 201, r.text
    assert crear(c, fecha="2026-11-03", fin="16:00").status_code == 409


def test_fifo_admite_fracciones_historicas_sin_redondear_el_dia(db):
    c, q, e = db
    e("UPDATE vacaciones.saldos SET dias_utilizados=14.5,dias_disponibles=0.5 WHERE id_saldo=20")
    assert crear(c, fin="16:00").status_code == 201
    assert aprobar(c, 1).status_code == 200
    assert q("SELECT id_saldo,dias_descontados FROM vacaciones.descuentos_por_periodo WHERE id_permiso IS NOT NULL AND tipo_movimiento='DESCUENTO' ORDER BY id_descuento") == [(20, .5), (10, .5)]
    assert resumen(c)["dias_descontados"] == 1


def test_anticipo_comparte_limite_de_15_con_vacaciones(db):
    c, q, e = db
    e("UPDATE vacaciones.saldos SET dias_utilizados=15,dias_disponibles=0 WHERE id_saldo IN (10,20)")
    e("UPDATE vacaciones.saldos SET dias_asignados=16,dias_utilizados=14,dias_disponibles=2 WHERE id_saldo=30")
    assert crear(c, fin="16:00").status_code == 201
    assert resumen(c)["reservas_activas"][0]["es_anticipo"] is True
    assert vacaciones(c).status_code == 409
    assert aprobar(c, 1).status_code == 200
    assert q("SELECT dias_utilizados FROM vacaciones.saldos WHERE id_saldo=30") == [(15,)]
    assert crear(c, fecha="2026-11-03", fin="16:00").status_code == 409


def test_menos_de_ocho_horas_no_reserva_un_dia_incompleto(db):
    c, q, e = db
    e("UPDATE vacaciones.saldos SET dias_utilizados=dias_asignados,dias_disponibles=0")
    assert crear(c, fin="15:00").status_code == 201
    assert aprobar(c, 1).status_code == 200
    assert resumen(c)["minutos_restantes"] == 420
    assert crear(c, fecha="2026-11-03", fin="09:00").status_code == 409
    assert q("SELECT count(*) FROM vacaciones.permisos") == [(1,)]
    assert resumen(c)["minutos_restantes"] == 420


def test_rollback_si_falla_despues_del_descuento(db, monkeypatch):
    from app.modules.vacaciones.permisos import contabilidad
    c, q, _ = db
    assert crear(c, fin="16:00").status_code == 201
    antes = q("SELECT * FROM vacaciones.saldos")
    async def fallar(*args):
        raise HTTPException(status_code=409, detail="Fallo simulado al reponer reservas")
    monkeypatch.setattr(contabilidad, "recalcular_reserva_comun", fallar)
    assert aprobar(c, 1).status_code == 409
    assert q("SELECT * FROM vacaciones.saldos") == antes
    assert q("SELECT estado,dias_convertidos FROM vacaciones.permisos") == [("PENDIENTE", None)]
    assert q("SELECT count(*) FROM vacaciones.descuentos_por_periodo WHERE id_permiso IS NOT NULL AND tipo_movimiento='DESCUENTO'") == [(0,)]
    assert Decimal(resumen(c)["dias_reservados"]) == 1


def test_historico_pendiente_se_concilia_expresamente(db):
    c, _, e = db
    e("INSERT INTO vacaciones.permisos(id_permiso,id_empleado,fecha,hora_inicio,hora_fin,total_horas,motivo,estado) VALUES (7,1,'2026-11-02','08:00','11:00',3,'Histórico','PENDIENTE')")
    assert resumen(c)["permisos_historicos_sin_conciliar"] == [7]
    assert crear(c, fecha="2026-11-03").status_code == 409
    assert aprobar(c, 7).status_code == 409
    assert c.post("/permisos/detalle/7/conciliacion", json={"id_responsable": 1}).status_code == 403
    r = c.post("/permisos/detalle/7/conciliacion", json={"id_responsable": 2})
    assert r.status_code == 200, r.text
    assert r.json()["total_minutos"] == 180 and r.json()["gestionado"]
    assert aprobar(c, 7).status_code == 200
    assert resumen(c)["minutos_restantes"] == 180


def test_historico_aprobado_no_se_cobra_automaticamente(db):
    c, q, e = db
    e("INSERT INTO vacaciones.permisos(id_empleado,fecha,hora_inicio,hora_fin,total_horas,motivo,estado) VALUES (1,'2026-01-01','08:00','16:00',8,'Histórico','APROBADO')")
    antes = q("SELECT * FROM vacaciones.saldos")
    assert c.get("/permisos/1").json()[0]["gestionado"] is False
    assert resumen(c)["permisos_historicos_sin_conciliar"] == [1]
    assert crear(c).status_code == 409
    assert c.post("/permisos/detalle/1/conciliacion", json={"id_responsable": 2}).status_code == 409
    assert q("SELECT * FROM vacaciones.saldos") == antes


def test_empleado_documento_y_parametros_invalidos(db):
    c, _, _ = db
    assert crear(c, empleado=999).status_code == 404
    assert c.get("/permisos/999/resumen").status_code == 404
    assert c.get("/permisos/detalle/999").status_code == 404
    assert c.get("/permisos/detalle/999/descuentos").status_code == 404
    assert c.patch("/permisos/detalle/999/cancelar").status_code == 404
    assert c.get("/permisos/0/resumen").status_code == 422
