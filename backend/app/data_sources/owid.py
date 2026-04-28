from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime

import httpx

from app.data_sources.registry import COUNTRIES, IndicatorDef
from app.data_sources.world_bank import DataSourceError
from app.models import DataPoint, Series, SourceCitation
from app.services.cache import SQLiteCache
from app.settings import CACHE_TTL_SECONDS, HTTP_TIMEOUT_SECONDS


class OwidClient:
    base_url = "https://ourworldindata.org/grapher"

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
            "owid:"
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

        url = f"{self.base_url}/{indicator.source_id}.csv?country={'~'.join(country_codes)}"
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "HealthPulseAI/1.0 education project"},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DataSourceError(f"Our World in Data request failed: {exc}") from exc

        reader = csv.DictReader(io.StringIO(response.text))
        if not reader.fieldnames:
            raise DataSourceError("Our World in Data returned an empty CSV.")

        value_column = next(
            (
                column
                for column in reversed(reader.fieldnames)
                if column not in {"Entity", "Code", "Year", "Day"}
            ),
            None,
        )
        if not value_column:
            raise DataSourceError("Could not find a value column in Our World in Data CSV.")

        yearly_values: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        names: dict[str, str] = {}

        for row in reader:
            code = (row.get("Code") or "").upper()
            if code not in country_codes:
                continue
            raw_value = row.get(value_column)
            if raw_value in (None, ""):
                continue
            try:
                value = float(raw_value)
            except ValueError:
                continue

            year = self._extract_year(row)
            if year is None:
                continue
            if start_year is not None and year < start_year:
                continue
            if end_year is not None and year > end_year:
                continue

            names[code] = row.get("Entity") or _country_name(code)
            yearly_values[code][year].append(value)

        series: list[Series] = []
        for code in country_codes:
            if code not in yearly_values:
                continue
            points = [
                DataPoint(year=year, value=sum(values) / len(values))
                for year, values in sorted(yearly_values[code].items())
                if values
            ]
            series.append(
                Series(
                    country_code=code,
                    country_name=names.get(code) or _country_name(code),
                    points=points,
                )
            )

        citations = [
            SourceCitation(
                name="Our World in Data Grapher",
                url=f"https://ourworldindata.org/grapher/{indicator.source_id}",
                accessed_via=url,
                note=f"Annual averages computed from Grapher series: {indicator.source_id}.",
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

    def _extract_year(self, row: dict[str, str]) -> int | None:
        if row.get("Year"):
            try:
                return int(row["Year"])
            except ValueError:
                return None
        if row.get("Day"):
            try:
                return datetime.fromisoformat(row["Day"]).year
            except ValueError:
                return None
        return None


def _country_name(code: str) -> str:
    return COUNTRIES[code].name if code in COUNTRIES else code
