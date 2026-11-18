from fastapi.testclient import TestClient

from app.main import app


def test_vacation_routes_require_authentication() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/vacaciones/calculos/dias",
            params={"fecha_inicio": "2026-11-06", "fecha_fin": "2026-11-06"},
        )

    assert response.status_code == 401


def test_vacation_route_is_registered_in_openapi() -> None:
    with TestClient(app) as client:
        response = client.get("/api/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/vacaciones/calculos/dias" in response.json()["paths"]
