from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import quote

import httpx

from app.data_sources.registry import COUNTRIES, IndicatorDef
from app.data_sources.world_bank import DataSourceError
from app.models import DataPoint, Series, SourceCitation
from app.services.cache import SQLiteCache
from app.settings import CACHE_TTL_SECONDS, HTTP_TIMEOUT_SECONDS


class WHOClient:
    base_url = "https://ghoapi.azureedge.net/api"

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
            "who:"
            + indicator.source_id
            + ":"
            + ";".join(country_codes)
            + f":{start_year}:{end_year}:"
            + "|".join(indicator.source_filter)
        )
        cached = self.cache.get_json(cache_key)
        if cached:
            return (
                [Series.model_validate(item) for item in cached["series"]],
                [SourceCitation.model_validate(item) for item in cached["citations"]],
            )

        series: list[Series] = []
        accessed_urls: list[str] = []
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            for code in country_codes:
                rows, url = await self._fetch_country_rows(client, indicator, code, start_year, end_year)
                accessed_urls.append(url)
                points_by_year: dict[int, list[float]] = defaultdict(list)
                for row in rows:
                    year = _safe_int(row.get("TimeDim"))
                    value = _safe_float(row.get("NumericValue"))
                    if year is None or value is None:
                        continue
                    points_by_year[year].append(value)

                points = [
                    DataPoint(year=year, value=sum(values) / len(values))
                    for year, values in sorted(points_by_year.items())
                    if values
                ]
                if points:
                    series.append(
                        Series(
                            country_code=code,
                            country_name=_country_name(code),
                            points=points,
                        )
                    )

        citations = [
            SourceCitation(
                name="WHO Global Health Observatory OData API",
                url="https://www.who.int/data/gho/info/gho-odata-api",
                accessed_via="; ".join(accessed_urls),
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

    async def _fetch_country_rows(
        self,
        client: httpx.AsyncClient,
        indicator: IndicatorDef,
        country_code: str,
        start_year: int | None,
        end_year: int | None,
    ) -> tuple[list[dict[str, Any]], str]:
        clauses = [f"SpatialDim eq '{country_code}'", *indicator.source_filter]
        if start_year is not None:
            clauses.append(f"TimeDim ge {start_year}")
        if end_year is not None:
            clauses.append(f"TimeDim le {end_year}")

        filter_text = " and ".join(clauses)
        url = f"{self.base_url}/{indicator.source_id}?$filter={quote(filter_text)}"
        first_url = url
        rows: list[dict[str, Any]] = []
        page_count = 0

        while url and page_count < 20:
            try:
                response = await client.get(
                    url,
                    headers={"User-Agent": "HealthPulseAI/1.0 education project"},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise DataSourceError(f"WHO API request failed: {exc}") from exc

            payload: Any = response.json()
            rows.extend(payload.get("value", []))
            url = payload.get("@odata.nextLink")
            page_count += 1

        return rows, first_url


def _country_name(code: str) -> str:
    return COUNTRIES[code].name if code in COUNTRIES else code


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
