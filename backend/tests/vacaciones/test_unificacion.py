from decimal import Decimal
from test_calculos_periodos import db
from test_ajustes import horas_aprobadas, vac_aprobada, ajustar
from test_permisos_horas import resumen, crear


def test_mezclar_consumos_y_reintegros_no_cruza_vacaciones_con_horas(db):
    c, q, _ = db
    permiso = horas_aprobadas(c, fin="16:00")
    solicitud = vac_aprobada(c, "2026-12-01", "2026-12-02")
    assert resumen(c)["dias_descontados"] == 1
    assert ajustar(c, solicitud).status_code == 201
    assert resumen(c)["dias_descontados"] == 1
    assert q("SELECT sum(dias_utilizados) FROM vacaciones.saldos") == [(13,)]
    assert ajustar(c, permiso, horas=True).status_code == 201
    assert resumen(c)["dias_descontados"] == 0
    assert q("SELECT sum(dias_utilizados) FROM vacaciones.saldos") == [(12,)]
    assert q("SELECT count(*) FROM vacaciones.descuentos_por_periodo WHERE tipo_movimiento='DESCUENTO'") == [(2,)]
    assert q("SELECT count(*) FROM vacaciones.descuentos_por_periodo WHERE tipo_movimiento='REINTEGRO'") == [(2,)]
    assert q("SELECT count(*) FROM vacaciones.aprobaciones WHERE tipo_intervencion='DECISION'") == [(2,)]
    assert q("SELECT count(*) FROM vacaciones.aprobaciones WHERE tipo_intervencion='REVERSO'") == [(2,)]


def test_rechazo_permiso_se_registra_en_aprobaciones_existente(db):
    c, q, _ = db
    assert crear(c, fin="16:00").status_code == 201
    assert c.post('/permisos/detalle/1/rechazo',json={'id_aprobador':2,'observacion':'Revisión TH'}).status_code == 200
    assert q("SELECT id_permiso,id_solicitud,id_aprobador,decision,tipo_intervencion FROM vacaciones.aprobaciones") == [(1,None,2,'RECHAZADA','DECISION')]
    assert Decimal(resumen(c)['dias_reservados']) == 0


def test_modelos_y_base_no_crean_tablas_separadas(db):
    from app.core.database import Base
    _, q, _ = db
    esperadas = {'saldos','solicitudes','feriados','aprobaciones','permisos',
                 'reservas_por_periodo','descuentos_por_periodo','responsables_talento_humano'}
    assert {r[0] for r in q("SELECT name FROM vacaciones.sqlite_master WHERE type='table' AND name<>'sqlite_sequence'")} == esperadas
    assert not {'ajustes','reintegros','reservas_por_horas','descuentos_por_horas'} & {t.name for t in Base.metadata.tables.values()}
