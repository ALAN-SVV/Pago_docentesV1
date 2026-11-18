from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.pagos_docentes.enums import PaymentModel, PaymentStatus, ThresholdUnit
from app.modules.pagos_docentes.schemas import (
    PaymentCreate,
    PaymentReady,
    PaymentSettingsUpdate,
)


def payment_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id_docente": 1,
        "id_periodo": 2,
        "id_carrera": 3,
        "nombre_modulo": "Matemática",
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-01-31",
    }
    payload.update(overrides)
    return payload


def test_payment_create_uses_safe_initial_defaults() -> None:
    payment = PaymentCreate.model_validate(payment_payload())

    assert payment.estado is PaymentStatus.EN_CURSO
    assert payment.modelo is PaymentModel.CARRERA
    assert payment.fecha_inicio == date(2026, 1, 1)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id_docente", 0),
        ("id_periodo", -1),
        ("id_carrera", 0),
    ],
)
def test_payment_create_rejects_non_positive_reference_ids(
    field: str, value: int
) -> None:
    with pytest.raises(ValidationError):
        PaymentCreate.model_validate(payment_payload(**{field: value}))


def test_payment_create_rejects_reversed_dates() -> None:
    with pytest.raises(ValidationError, match="posterior"):
        PaymentCreate.model_validate(
            payment_payload(fecha_inicio="2026-02-01", fecha_fin="2026-01-31")
        )


@pytest.mark.parametrize("estado", ["LISTO_PAGO", "APROBADO", "PAGADO", "ANULADO"])
def test_payment_create_only_allows_initial_status(estado: str) -> None:
    with pytest.raises(ValidationError):
        PaymentCreate.model_validate(payment_payload(estado=estado))


def test_payment_create_accepts_case_insensitive_model_alias() -> None:
    payment = PaymentCreate.model_validate(payment_payload(modelo="validacion"))

    assert payment.modelo is PaymentModel.VALIDACION


@pytest.mark.parametrize("amount", ["0", "-1", "1.001", "10000000000.00"])
def test_ready_payment_rejects_invalid_amounts(amount: str) -> None:
    with pytest.raises(ValidationError):
        PaymentReady.model_validate({"monto": amount})


def test_ready_payment_accepts_positive_amount_with_two_decimal_places() -> None:
    payment = PaymentReady.model_validate({"monto": "1250.50"})

    assert payment.monto == Decimal("1250.50")


def test_settings_update_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError, match="al menos un valor"):
        PaymentSettingsUpdate.model_validate({})


@pytest.mark.parametrize("value", [0, 366])
def test_settings_update_rejects_out_of_range_threshold(value: int) -> None:
    with pytest.raises(ValidationError):
        PaymentSettingsUpdate.model_validate({"valor": value})


def test_settings_update_accepts_valid_partial_update() -> None:
    update = PaymentSettingsUpdate.model_validate(
        {"valor": 14, "unidad": ThresholdUnit.DIAS, "correo_notificacion": "pagos@itq.edu"}
    )

    assert update.valor == 14
    assert update.unidad is ThresholdUnit.DIAS
    assert update.correo_notificacion == "pagos@itq.edu"


def test_settings_update_rejects_invalid_notification_email() -> None:
    with pytest.raises(ValidationError):
        PaymentSettingsUpdate.model_validate(
            {"correo_notificacion": "not-an-email"}
        )
