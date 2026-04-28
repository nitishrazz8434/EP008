from __future__ import annotations

from collections import defaultdict
from typing import Any

import httpx

from app.data_sources.registry import COUNTRIES, IndicatorDef
from app.models import DataPoint, Series, SourceCitation
from app.services.cache import SQLiteCache
from app.settings import CACHE_TTL_SECONDS, HTTP_TIMEOUT_SECONDS


class DataSourceError(RuntimeError):
    pass


class WorldBankClient:
    base_url = "https://api.worldbank.org/v2"

    def __init__(self, cache: SQLiteCache) -> None:
        self.cache = cache

    async def fetch_series(
        self,
        indicator: IndicatorDef,
        countries: list[str],
        start_year: int | None,
        end_year: int | None,
    ) -> tuple[list[Series], list[SourceCitation]]:
        country_codes = [code.upper() for code in countries]
        cache_key = (
            "worldbank:"
            + indicator.source_id
            + ":"
            + ";".join(country_codes)
            + f":{start_year}:{end_year}"
        )
        cached = self.cache.get_json(cache_key)
        if cached:
            return (
                [Series.model_validate(item) for item in cached["series"]],
                [SourceCitation.model_validate(item) for item in cached["citations"]],
            )

        url = (
            f"{self.base_url}/country/{';'.join(country_codes)}/indicator/"
            f"{indicator.source_id}?format=json&per_page=20000"
        )

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DataSourceError(f"World Bank API request failed: {exc}") from exc

        payload: Any = response.json()
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            raise DataSourceError("World Bank API returned an unexpected response.")

        grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"name": "", "points": []})
        for row in payload[1]:
            value = row.get("value")
            year_text = row.get("date")
            code = row.get("countryiso3code") or row.get("country", {}).get("id")
            if value is None or not year_text or not code:
                continue
            try:
                year = int(year_text)
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue
            if start_year is not None and year < start_year:
                continue
            if end_year is not None and year > end_year:
                continue
            grouped[code]["name"] = row.get("country", {}).get("value") or _country_name(code)
            grouped[code]["points"].append(DataPoint(year=year, value=numeric_value))

        series = [
            Series(
                country_code=code,
                country_name=data["name"] or _country_name(code),
                points=sorted(data["points"], key=lambda point: point.year),
            )
            for code, data in grouped.items()
        ]
        series.sort(key=lambda item: country_codes.index(item.country_code) if item.country_code in country_codes else 999)

        citations = [
            SourceCitation(
                name="World Bank Indicators API",
                url="https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation",
                accessed_via=url,
                note=f"Indicator {indicator.source_id}: {indicator.label}.",
            )
        ]
        self.cache.set_json(
            cache_key,
            {
                "series": [item.model_dump() for item in series],
                "citations": [item.model_dump() for item in citations],
            },
            CACHE_TTL_SECONDS,
        )
        return series, citations


def _country_name(code: str) -> str:
    return COUNTRIES[code].name if code in COUNTRIES else code
