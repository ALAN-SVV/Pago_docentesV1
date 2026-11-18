from decimal import Decimal
import pytest
from fastapi import HTTPException
from test_calculos_periodos import db
from test_permisos_horas import crear, aprobar, resumen, vacaciones

BASE = {"id_responsable": 2, "motivo": "Corrección autorizada por TH"}


def vac_aprobada(c, inicio="2026-12-01", fin="2026-12-05"):
    r = vacaciones(c, inicio, fin)
    assert r.status_code == 201, r.text
    identificador = r.json()["id_solicitud"]
    r = c.post(f"/solicitudes/{identificador}/aprobacion", json={"id_aprobador": 2, "observacion": "Aprobado"})
    assert r.status_code == 201, r.text
    return identificador


def horas_aprobadas(c, fecha="2026-11-02", fin="11:00"):
    r = crear(c, fecha=fecha, fin=fin)
    assert r.status_code == 201, r.text
    identificador = r.json()["id_permiso"]
    r = aprobar(c, identificador)
    assert r.status_code == 200, r.text
    return identificador


def ajustar(c, identificador, horas=False, nuevos=None, responsable=2):
    clase = "permisos" if horas else "solicitudes"
    accion = "reverso" if nuevos is None else "correccion"
    datos = {**BASE, "id_responsable": responsable}
    if nuevos is not None:
        datos["datos"] = nuevos
    return c.post(f"/ajustes/{clase}/{identificador}/{accion}", json=datos)


def test_reverso_vacaciones_devuelve_periodos_exactos_y_conserva_historial(db):
    c, q, _ = db
    antes = q("SELECT * FROM vacaciones.saldos ORDER BY id_saldo")
    identificador = vac_aprobada(c)
    descuentos = q("SELECT * FROM vacaciones.descuentos_por_periodo WHERE tipo_movimiento='DESCUENTO'")
    decision = q("SELECT * FROM vacaciones.aprobaciones WHERE tipo_intervencion='DECISION'")
    r = ajustar(c, identificador)
    assert r.status_code == 201, r.text
    assert [(x["id_saldo"], Decimal(x["dias_descontados"])) for x in r.json()["reintegros"]] == [(20,3),(10,2)]
    assert q("SELECT * FROM vacaciones.saldos ORDER BY id_saldo") == antes
    assert q("SELECT * FROM vacaciones.descuentos_por_periodo WHERE tipo_movimiento='DESCUENTO'") == descuentos
    assert q("SELECT * FROM vacaciones.aprobaciones WHERE tipo_intervencion='DECISION'") == decision
    assert c.get(f"/solicitudes/detalle/{identificador}").json()["estado"] == "ANULADA"
    assert ajustar(c, identificador).status_code == 409
    h = c.get("/ajustes/empleados/1").json()
    assert len(h) == 1 and h[0]["antes"]["documento"]["estado"] == "APROBADA"
    assert h[0]["despues"]["documento"]["estado"] == "ANULADA"


def test_correccion_vacaciones_crea_reemplazo_aprobado_y_se_puede_revertir(db):
    c, q, _ = db
    original = vac_aprobada(c)
    r = ajustar(c, original, nuevos={"fecha_inicio":"2026-12-01", "fecha_fin":"2026-12-02", "motivo":"Fechas corregidas"})
    assert r.status_code == 201, r.text
    nuevo = r.json()["id_solicitud_nueva"]
    assert nuevo != original and r.json()["tipo_intervencion"] == "CORRECCION"
    assert r.json()["despues"]["reemplazo"]["estado"] == "APROBADA"
    assert q("SELECT dias_disponibles FROM vacaciones.saldos WHERE id_saldo=20") == [(1,)]
    assert ajustar(c, nuevo).status_code == 201
    assert q("SELECT dias_disponibles FROM vacaciones.saldos WHERE id_saldo=20") == [(3,)]
    assert len(c.get("/ajustes/empleados/1").json()) == 2


@pytest.mark.parametrize("fallo", ["saldo", "cruce"])
def test_correccion_fallida_revierte_documento_reintegro_y_reemplazo(db, fallo):
    c, q, _ = db
    original = vac_aprobada(c)
    if fallo == "cruce":
        vac_aprobada(c, "2027-01-01", "2027-01-02")
    tablas = ["saldos", "solicitudes", "aprobaciones", "descuentos_por_periodo", "reservas_por_periodo"]
    antes = {t:q(f"SELECT * FROM vacaciones.{t}") for t in tablas}
    fin = "2027-01-02" if fallo == "cruce" else "2027-03-01"
    r = ajustar(c, original, nuevos={"fecha_inicio":"2027-01-01", "fecha_fin":fin, "motivo":"Ampliación"})
    assert r.status_code == 409, r.text
    assert {t:q(f"SELECT * FROM vacaciones.{t}") for t in tablas} == antes


@pytest.mark.parametrize("horas", [False, True])
@pytest.mark.parametrize("responsable,codigo", [(1,403),(999,404)])
def test_ajuste_exige_th(db, horas, responsable, codigo):
    c, q, _ = db
    identificador = horas_aprobadas(c) if horas else vac_aprobada(c)
    assert ajustar(c, identificador, horas=horas, responsable=responsable).status_code == codigo
    assert q("SELECT count(*) FROM vacaciones.aprobaciones WHERE tipo_intervencion IN ('REVERSO','CORRECCION')") == [(0,)]


def test_pendientes_y_datos_invalidos_no_se_ajustan(db):
    c, q, _ = db
    assert crear(c).status_code == 201
    assert vacaciones(c).status_code == 201
    for horas in (True,False):
        assert ajustar(c, 1, horas=horas).status_code == 409
        assert ajustar(c, 999, horas=horas).status_code == 404
    for cambio in ({"motivo":"  "},{"id_responsable":True},{"dias_reintegrados":5}):
        r = c.post("/ajustes/solicitudes/1/reverso", json={**BASE, **cambio})
        assert r.status_code == 422
    assert q("SELECT count(*) FROM vacaciones.aprobaciones WHERE tipo_intervencion IN ('REVERSO','CORRECCION')") == [(0,)]


@pytest.mark.parametrize("anular", [1,2])
def test_reverso_horas_recalcula_acumulado_sin_depender_del_documento_que_desconto(db, anular):
    c, q, _ = db
    horas_aprobadas(c)
    horas_aprobadas(c, "2026-11-03", "13:00")
    assert resumen(c)["dias_descontados"] == 1
    descuentos = q("SELECT * FROM vacaciones.descuentos_por_periodo WHERE id_permiso IS NOT NULL AND tipo_movimiento='DESCUENTO'")
    r = ajustar(c, anular, horas=True)
    assert r.status_code == 201, r.text
    assert len(r.json()["reintegros"]) == 1
    assert resumen(c)["minutos_restantes"] == (300 if anular == 1 else 180)
    assert resumen(c)["dias_descontados"] == 0
    assert q("SELECT * FROM vacaciones.descuentos_por_periodo WHERE id_permiso IS NOT NULL AND tipo_movimiento='DESCUENTO'") == descuentos
    assert ajustar(c, anular, horas=True).status_code == 409
    assert ajustar(c, 3-anular, horas=True).status_code == 201
    assert resumen(c)["minutos_restantes"] == 0
    assert q("SELECT sum(dias_descontados) FROM vacaciones.descuentos_por_periodo WHERE tipo_movimiento='REINTEGRO'") == [(1,)]


def test_reverso_horas_sin_dia_convertido_no_crea_reintegro(db):
    c, q, _ = db
    horas_aprobadas(c)
    r = ajustar(c, 1, horas=True)
    assert r.status_code == 201 and r.json()["reintegros"] == []
    assert resumen(c)["minutos_restantes"] == 0
    assert q("SELECT dias_disponibles FROM vacaciones.saldos WHERE id_saldo=20") == [(3,)]


def test_reverso_horas_reasigna_reserva_de_otros_pendientes(db):
    c, q, _ = db
    horas_aprobadas(c, fin="16:00")
    horas_aprobadas(c, "2026-11-03", "09:00")
    assert crear(c, fecha="2026-11-04", fin="15:00").status_code == 201
    assert Decimal(resumen(c)["dias_reservados"]) == 1
    r = ajustar(c, 2, horas=True)
    assert r.status_code == 201, r.text
    assert Decimal(resumen(c)["dias_reservados"]) == 0
    assert resumen(c)["dias_descontados"] == 1
    assert aprobar(c, 3).status_code == 200
    assert resumen(c)["minutos_restantes"] == 420


def test_correccion_horas_conserva_original_y_cadena_sigue_funcionando(db):
    c, q, _ = db
    horas_aprobadas(c)
    horas_aprobadas(c, "2026-11-03", "13:00")
    r = ajustar(c, 1, horas=True, nuevos={"fecha":"2026-11-02", "hora_inicio":"08:00", "hora_fin":"12:00", "motivo":"Cuatro horas"})
    assert r.status_code == 201, r.text
    nuevo = r.json()["id_permiso_nuevo"]
    assert nuevo == 3 and resumen(c)["minutos_restantes"] == 60
    assert resumen(c)["dias_descontados"] == 1
    assert c.get("/permisos/detalle/1").json()["total_minutos"] == 180
    assert c.get("/permisos/detalle/1").json()["estado"] == "ANULADO"
    assert ajustar(c, 2, horas=True).status_code == 201
    assert resumen(c)["minutos_restantes"] == 240
    assert ajustar(c, nuevo, horas=True).status_code == 201
    assert resumen(c)["minutos_restantes"] == 0
    assert q("SELECT dias_disponibles FROM vacaciones.saldos WHERE id_saldo=20") == [(3,)]


def test_correccion_horas_sin_saldo_hace_rollback(db):
    c, q, e = db
    e("UPDATE vacaciones.saldos SET dias_utilizados=dias_asignados,dias_disponibles=0")
    horas_aprobadas(c)
    antes = q("SELECT * FROM vacaciones.permisos")
    r = ajustar(c, 1, horas=True, nuevos={"fecha":"2026-11-02", "hora_inicio":"08:00", "hora_fin":"16:00", "motivo":"Más tiempo"})
    assert r.status_code == 409
    assert q("SELECT * FROM vacaciones.permisos") == antes
    assert q("SELECT count(*) FROM vacaciones.aprobaciones WHERE tipo_intervencion IN ('REVERSO','CORRECCION')") == [(0,)]
    assert resumen(c)["minutos_restantes"] == 180


def test_reintegro_horas_recorre_descuentos_mas_recientes_y_fracciones(db):
    c, q, e = db
    e("UPDATE vacaciones.saldos SET dias_utilizados=14.5,dias_disponibles=0.5 WHERE id_saldo=20")
    horas_aprobadas(c, fin="16:00")
    r = ajustar(c, 1, horas=True)
    assert r.status_code == 201, r.text
    assert [(x["id_saldo"],Decimal(x["dias_descontados"])) for x in r.json()["reintegros"]] == [(10,Decimal('.5')),(20,Decimal('.5'))]
    assert resumen(c)["dias_descontados"] == 0


def test_reintegro_anticipo_reabre_capacidad(db):
    c, _, e = db
    e("UPDATE vacaciones.saldos SET dias_utilizados=dias_asignados,dias_disponibles=0 WHERE id_saldo IN (10,20)")
    identificador = vac_aprobada(c, "2026-12-01", "2026-12-15")
    assert Decimal(c.get('/saldos/1/resumen').json()['total_anticipable']) == 0
    assert ajustar(c, identificador).status_code == 201
    assert Decimal(c.get('/saldos/1/resumen').json()['total_anticipable']) == 15


def test_fallo_despues_de_reintegro_restaura_todo(db, monkeypatch):
    from app.modules.vacaciones.ajustes import service
    c, q, _ = db
    identificador = vac_aprobada(c)
    antes = q("SELECT * FROM vacaciones.saldos")
    async def fallar(*args):
        raise HTTPException(status_code=409, detail="Fallo simulado después del reintegro")
    monkeypatch.setattr(service, "reemplazar_solicitud", fallar)
    r = ajustar(c, identificador, nuevos={"fecha_inicio":"2026-12-01", "fecha_fin":"2026-12-02", "motivo":"Cambio"})
    assert r.status_code == 409
    assert q("SELECT * FROM vacaciones.saldos") == antes
    assert q("SELECT count(*) FROM vacaciones.descuentos_por_periodo WHERE tipo_movimiento='REINTEGRO'") == [(0,)]
    assert c.get(f"/solicitudes/detalle/{identificador}").json()["estado"] == "APROBADA"


def test_historicos_y_descuentos_incoherentes_no_se_revierten(db):
    c, q, e = db
    identificador = vac_aprobada(c)
    e("UPDATE vacaciones.descuentos_por_periodo SET dias_descontados=1 WHERE id_saldo=20")
    assert ajustar(c, identificador).status_code == 409
    e("INSERT INTO vacaciones.permisos(id_empleado,estado,total_horas) VALUES (1,'APROBADO',8)")
    assert ajustar(c, 1, horas=True).status_code == 409
    assert q("SELECT count(*) FROM vacaciones.aprobaciones WHERE tipo_intervencion IN ('REVERSO','CORRECCION')") == [(0,)]


def test_secuencia_de_reversos_y_nuevas_aprobaciones_conserva_minutos_y_saldo(db):
    c, q, _ = db
    vigentes = {}
    contador = 0
    def comprobar():
        total = sum(vigentes.values())
        r = resumen(c)
        assert r["minutos_aprobados"] == total
        assert (r["dias_descontados"], r["minutos_restantes"]) == divmod(total,480)
        assert q("SELECT sum(dias_utilizados) FROM vacaciones.saldos")[0][0] == 12 + total//480
    for minutos in [479,1,615,120,60,480]:
        contador += 1
        fin = 8*60 + minutos
        identificador = horas_aprobadas(c, f"2027-01-{contador:02}", f"{fin//60:02}:{fin%60:02}")
        vigentes[identificador] = minutos
        comprobar()
    for identificador in [1,4,2,6]:
        assert ajustar(c, identificador, horas=True).status_code == 201
        del vigentes[identificador]
        comprobar()
        contador += 1
        nuevo = horas_aprobadas(c, f"2027-01-{contador:02}", "09:13")
        vigentes[nuevo] = 73
        comprobar()
    for identificador in list(vigentes):
        assert ajustar(c, identificador, horas=True).status_code == 201
        del vigentes[identificador]
        comprobar()
