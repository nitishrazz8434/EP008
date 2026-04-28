from __future__ import annotations

from fastapi.testclient import TestClient

from app import main
from app.models import DataPoint, Series, SourceCitation


def _fake_who_series(countries: list[str]) -> list[Series]:
    names = {"IND": "India", "BRA": "Brazil", "USA": "United States"}
    values = {
        "IND": [10.0, 8.0, 6.0],
        "BRA": [18.0, 16.0, 14.0],
        "USA": [70.0, 72.0, 74.0],
    }
    series: list[Series] = []
    for code in countries:
        country_values = values.get(code, [5.0, 4.0, 3.0])
        series.append(
            Series(
                country_code=code,
                country_name=names.get(code, code),
                points=[
                    DataPoint(year=2020, value=country_values[0]),
                    DataPoint(year=2021, value=country_values[1]),
                    DataPoint(year=2022, value=country_values[2]),
                ],
            )
        )
    return series


async def _mock_fetch_series(indicator, countries, start_year, end_year):
    return (
        _fake_who_series(countries),
        [
            SourceCitation(
                name="WHO Global Health Observatory OData API",
                url="https://www.who.int/data/gho/info/gho-odata-api",
                accessed_via=f"https://ghoapi.azureedge.net/api/{indicator.source_id}",
                note=f"Indicator {indicator.source_id}: {indicator.label}.",
            )
        ],
    )


def test_chat_api_uses_who_for_malaria_comparison(monkeypatch) -> None:
    monkeypatch.setattr(main.who, "fetch_series", _mock_fetch_series)
    client = TestClient(main.app)

    response = client.post("/api/chat", json={"message": "Compare malaria in India and Brazil"})
    body = response.json()

    assert response.status_code == 200
    assert body["plan"]["intent"] == "compare"
    assert body["plan"]["indicator_id"] == "malaria_incidence"
    assert body["plan"]["countries"] == ["IND", "BRA"]
    assert body["metric"]["source"] == "WHO"
    assert body["citations"][0]["name"] == "WHO Global Health Observatory OData API"


def test_chat_api_explains_improving_maternal_mortality(monkeypatch) -> None:
    monkeypatch.setattr(main.who, "fetch_series", _mock_fetch_series)
    client = TestClient(main.app)

    response = client.post("/api/chat", json={"message": "Is maternal mortality improving in India?"})
    body = response.json()

    assert response.status_code == 200
    assert body["plan"]["indicator_id"] == "maternal_mortality"
    assert body["metric"]["source"] == "WHO"
    assert "improving" in body["answer"].lower()
    assert "Risk level" not in body["answer"]


def test_chat_api_asks_for_clarification_before_fetching_vague_request(monkeypatch) -> None:
    async def fail_fetch(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("The API should not fetch source data for vague questions.")

    monkeypatch.setattr(main.who, "fetch_series", fail_fetch)
    client = TestClient(main.app)

    response = client.post("/api/chat", json={"message": "show me public health data"})
    body = response.json()

    assert response.status_code == 200
    assert body["needs_clarification"] is True
    assert body["series"] == []
    assert body["citations"] == []
    assert any("indicator" in question.lower() for question in body["clarification_questions"])
    assert any("country" in question.lower() for question in body["clarification_questions"])


def test_chat_api_asks_for_second_country_in_incomplete_comparison(monkeypatch) -> None:
    async def fail_fetch(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("The API should not fetch source data for incomplete comparisons.")

    monkeypatch.setattr(main.who, "fetch_series", fail_fetch)
    client = TestClient(main.app)

    response = client.post("/api/chat", json={"message": "compare malaria in India"})
    body = response.json()

    assert response.status_code == 200
    assert body["needs_clarification"] is True
    assert body["plan"]["intent"] == "compare"
    assert any("countries" in question.lower() for question in body["clarification_questions"])
