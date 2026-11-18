from copy import deepcopy
import pytest
from test_calculos_periodos import db

def datos():
    return {"id_responsable":2,"referencia":"Acta TH 2026-10-26","motivo":"Apertura validada por TH",
            "fecha_corte":"2026-10-26","minutos_sobrantes":300,"periodos":[
                {"periodo":"2023-2024","fecha_inicio_periodo":"2023-11-15","fecha_fin_periodo":"2024-11-14","fecha_acreditacion":"2024-11-15","dias_asignados":"15.00","dias_utilizados":"12.00","dias_disponibles":"3.00"},
                {"periodo":"2024-2025","fecha_inicio_periodo":"2024-11-15","fecha_fin_periodo":"2025-11-14","fecha_acreditacion":"2025-11-15","dias_asignados":"15.00","dias_utilizados":"1.00","dias_disponibles":"14.00"},
                {"periodo":"2025-2026","fecha_inicio_periodo":"2025-11-15","fecha_fin_periodo":"2026-11-14","fecha_acreditacion":"2026-11-15","dias_asignados":"15.00","dias_utilizados":"0.00","dias_disponibles":"15.00"}]}

def abrir(c,d=None):
    d=deepcopy(d or datos())
    r=c.post('/historicos/1/revision',json=d)
    assert r.status_code==200,r.text
    d['huella_revision']=r.json()['huella_revision']
    r=c.post('/historicos/1/apertura',json=d)
    assert r.status_code==200,r.text
    return d,r.json()

def test_revision_no_escribe_y_reintento_no_duplica(db):
    c,q,e=db; antes=q('SELECT * FROM vacaciones.saldos')
    r=c.post('/historicos/1/revision',json=datos())
    assert r.status_code==200 and r.json()['puede_confirmar']
    assert q('SELECT * FROM vacaciones.saldos')==antes
    d,r=abrir(c)
    assert not r['repetida']
    assert c.post('/historicos/1/apertura',json=d).json()['repetida']
    assert q('SELECT count(*) FROM vacaciones.saldos')==[(3,)]
    assert c.get('/historicos/1/conciliacion').json()['coincide']
    assert c.get('/historicos/1/apertura').json()['apertura']['datos']['referencia']==datos()['referencia']

def test_sobrante_convierte_y_reverso_lo_restaura(db):
    c,q,e=db;abrir(c)
    assert c.get('/permisos/1/resumen').json()['minutos_restantes']==300
    r=c.post('/permisos',json={'id_empleado':1,'fecha':'2026-11-02','hora_inicio':'09:00','hora_fin':'12:00','motivo':'Trámite'})
    assert r.status_code==201,r.text
    ident=r.json()['id_permiso']
    r=c.post(f'/permisos/detalle/{ident}/aprobacion',json={'id_aprobador':2,'observacion':'TH'})
    assert r.status_code==200,r.text
    assert c.get('/permisos/1/resumen').json()['minutos_restantes']==0
    assert c.get('/historicos/1/conciliacion').json()['coincide']
    r=c.post(f'/ajustes/permisos/{ident}/reverso',json={'id_responsable':2,'motivo':'Anulación'})
    assert r.status_code==201,r.text
    assert c.get('/permisos/1/resumen').json()['minutos_restantes']==300
    assert c.get('/historicos/1/conciliacion').json()['coincide']

@pytest.mark.parametrize('cambio',[{'minutos_sobrantes':480},{'minutos_sobrantes':1.5},{'referencia':' '},{'fecha_corte':'2099-01-01'},{'id_responsable':1}])
def test_rechaza_datos_invalidos(db,cambio):
    c,q,e=db;d=datos();d.update(cambio)
    assert c.post('/historicos/1/revision',json=d).status_code in (422,403)
    assert q('SELECT count(*) FROM vacaciones.saldos WHERE apertura_historica IS NOT NULL')==[(0,)]

def test_revision_obsoleta_y_no_sobrescribir_actividad(db):
    c,q,e=db;d=datos();r=c.post('/historicos/1/revision',json=d)
    d['huella_revision']=r.json()['huella_revision']
    e("UPDATE vacaciones.saldos SET dias_utilizados=2,dias_disponibles=13 WHERE id_saldo=10")
    assert c.post('/historicos/1/apertura',json=d).status_code==409
    c.post('/permisos',json={'id_empleado':1,'fecha':'2026-11-02','hora_inicio':'09:00','hora_fin':'10:00','motivo':'Prueba'})
    r=c.post('/historicos/1/revision',json=datos())
    assert not r.json()['puede_confirmar']

def test_conciliacion_detecta_cambios_y_corte_bloquea(db):
    c,q,e=db;abrir(c)
    assert c.post('/permisos',json={'id_empleado':1,'fecha':'2026-10-26','hora_inicio':'09:00','hora_fin':'10:00','motivo':'Duplicado'}).status_code==409
    assert c.post('/solicitudes',json={'id_empleado':1,'fecha_inicio':'2026-10-26','fecha_fin':'2026-10-27','motivo':'Duplicado'}).status_code==409
    e('UPDATE vacaciones.saldos SET dias_utilizados=5,dias_disponibles=10 WHERE id_saldo=10')
    r=c.get('/historicos/1/conciliacion').json()
    assert not r['coincide'] and r['diferencias'][0]['id_saldo']==10

def test_creacion_saldos_y_rollback(db,monkeypatch):
    c,q,e=db;e('DELETE FROM vacaciones.saldos')
    from app.modules.vacaciones.historicos import service
    async def fallar(*a):
        from fastapi import HTTPException
        raise HTTPException(409,'Fallo simulado')
    original=service.saldos.obtener_resumen_saldo
    monkeypatch.setattr(service.saldos,'obtener_resumen_saldo',fallar)
    d=datos();d['huella_revision']=c.post('/historicos/1/revision',json=d).json()['huella_revision']
    assert c.post('/historicos/1/apertura',json=d).status_code==409
    assert q('SELECT count(*) FROM vacaciones.saldos')==[(0,)]
    monkeypatch.setattr(service.saldos,'obtener_resumen_saldo',original)
    abrir(c)
    assert q('SELECT count(*) FROM vacaciones.saldos')==[(3,)]
