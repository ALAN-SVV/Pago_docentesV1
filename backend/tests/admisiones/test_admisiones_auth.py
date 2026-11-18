from fastapi.testclient import TestClient

from app.main import app
from app.modules.admisiones.models import Persona as AdmisionPersona
from app.modules.core.models.core import Empleado, Persona


def test_admisiones_routes_require_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/admision/crm")

    assert response.status_code == 401


def test_admisiones_routes_are_registered_in_openapi() -> None:
    with TestClient(app) as client:
        response = client.get("/api/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/admision/crm" in response.json()["paths"]
    assert "/api/v1/admision/crm/{id_crm}/seguimientos" in response.json()["paths"]


def test_admisiones_reuses_core_persona_and_empleado_models() -> None:
    from app.modules.admisiones.models import Empleado as AdmisionEmpleado

    assert AdmisionPersona is Persona
    assert AdmisionEmpleado is Empleado
