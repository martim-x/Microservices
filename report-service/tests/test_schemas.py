from decimal import Decimal

import pytest
from database.schemas import ReportCreate, ReportOut
from pydantic import ValidationError


def test_report_create_valid() -> None:
    report = ReportCreate(
        order_id=1,
        user_id=2,
        total=Decimal("10.50"),
    )

    assert report.order_id == 1
    assert report.user_id == 2
    assert report.total == Decimal("10.50")


@pytest.mark.parametrize(
    "payload",
    [
        {"order_id": 0, "user_id": 2, "total": Decimal("10.50")},
        {"order_id": 1, "user_id": 0, "total": Decimal("10.50")},
        {"order_id": 1, "user_id": 2, "total": Decimal("0")},
    ],
)
def test_report_create_invalid_values(payload: dict) -> None:
    with pytest.raises(ValidationError):
        ReportCreate(**payload)


def test_report_out_from_attributes() -> None:
    class DummyReport:
        order_id = 1
        user_id = 2
        total = Decimal("99.99")

    result = ReportOut.model_validate(DummyReport())

    assert result.order_id == 1
    assert result.user_id == 2
    assert result.total == Decimal("99.99")
