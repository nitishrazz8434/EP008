from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import CountryOption, IndicatorOption, MetricInfo


@dataclass(frozen=True)
class IndicatorDef:
    id: str
    label: str
    unit: str
    source: str
    source_id: str
    aliases: tuple[str, ...]
    polarity: str
    bounded_100: bool = False
    source_filter: tuple[str, ...] = ()

    def to_metric(self) -> MetricInfo:
        return MetricInfo(
            id=self.id,
            label=self.label,
            unit=self.unit,
            source=self.source,
            source_id=self.source_id,
            polarity=self.polarity,  # type: ignore[arg-type]
            bounded_100=self.bounded_100,
        )

    def to_option(self) -> IndicatorOption:
        return IndicatorOption(
            id=self.id,
            label=self.label,
            unit=self.unit,
            source=self.source,
            aliases=list(self.aliases),
        )


INDICATORS: dict[str, IndicatorDef] = {
    "life_expectancy": IndicatorDef(
        id="life_expectancy",
        label="Life expectancy at birth",
        unit="years",
        source="WHO",
        source_id="WHOSIS_000001",
        aliases=("life expectancy", "lifespan", "average age", "longevity"),
        polarity="higher_is_good",
        source_filter=("Dim1 eq 'SEX_BTSX'",),
    ),
    "infant_mortality": IndicatorDef(
        id="infant_mortality",
        label="Infant mortality rate",
        unit="deaths per 1,000 live births",
        source="WHO",
        source_id="MDG_0000000001",
        aliases=("infant mortality", "baby deaths", "child mortality infant"),
        polarity="higher_is_bad",
        source_filter=("Dim1 eq 'SEX_BTSX'", "Dim2 eq 'AGEGROUP_MONTHS0-11'"),
    ),
    "under5_mortality": IndicatorDef(
        id="under5_mortality",
        label="Under-5 mortality rate",
        unit="deaths per 1,000 live births",
        source="WHO",
        source_id="MDG_0000000007",
        aliases=("under 5 mortality", "under-five mortality", "child mortality", "children deaths"),
        polarity="higher_is_bad",
        source_filter=("Dim1 eq 'SEX_BTSX'", "Dim2 eq 'AGEGROUP_YEARSUNDER5'"),
    ),
    "maternal_mortality": IndicatorDef(
        id="maternal_mortality",
        label="Maternal mortality ratio",
        unit="deaths per 100,000 live births",
        source="WHO",
        source_id="MDG_0000000026",
        aliases=("maternal mortality", "mother deaths", "pregnancy deaths"),
        polarity="higher_is_bad",
    ),
    "health_expenditure_gdp": IndicatorDef(
        id="health_expenditure_gdp",
        label="Current health expenditure",
        unit="% of GDP",
        source="WHO",
        source_id="GHED_CHEGDP_SHA2011",
        aliases=("health expenditure", "health spending", "medical spending", "health budget"),
        polarity="mixed",
        bounded_100=True,
    ),
    "hospital_beds": IndicatorDef(
        id="hospital_beds",
        label="Hospital beds",
        unit="beds per 10,000 people",
        source="WHO",
        source_id="WHS6_102",
        aliases=("hospital beds", "beds", "hospital capacity"),
        polarity="higher_is_good",
    ),
    "physicians": IndicatorDef(
        id="physicians",
        label="Medical doctors",
        unit="doctors per 10,000 people",
        source="WHO",
        source_id="HWF_0001",
        aliases=("physicians", "doctors", "doctor density", "medical doctors"),
        polarity="higher_is_good",
    ),
    "nurses_midwives": IndicatorDef(
        id="nurses_midwives",
        label="Nurses and midwives",
        unit="nurses and midwives per 10,000 people",
        source="WHO",
        source_id="HWF_0006",
        aliases=("nurses", "midwives", "nursing staff"),
        polarity="higher_is_good",
    ),
    "measles_immunization": IndicatorDef(
        id="measles_immunization",
        label="Measles immunization coverage",
        unit="% among 1-year-olds",
        source="WHO",
        source_id="WHS8_110",
        aliases=("measles", "measles vaccine", "measles vaccination", "immunization"),
        polarity="higher_is_good",
        bounded_100=True,
    ),
    "dpt_immunization": IndicatorDef(
        id="dpt_immunization",
        label="DPT immunization coverage",
        unit="% among 1-year-olds",
        source="WHO",
        source_id="WHS4_100",
        aliases=("dpt", "dpt vaccine", "dpt vaccination", "vaccination coverage"),
        polarity="higher_is_good",
        bounded_100=True,
    ),
    "tb_incidence": IndicatorDef(
        id="tb_incidence",
        label="Tuberculosis incidence",
        unit="cases per 100,000 people",
        source="WHO",
        source_id="MDG_0000000020",
        aliases=("tuberculosis", "tb", "tb incidence"),
        polarity="higher_is_bad",
    ),
    "malaria_incidence": IndicatorDef(
        id="malaria_incidence",
        label="Malaria incidence",
        unit="cases per 1,000 population at risk",
        source="WHO",
        source_id="MALARIA_EST_INCIDENCE",
        aliases=("malaria", "malaria cases", "malaria incidence"),
        polarity="higher_is_bad",
    ),
    "diabetes_prevalence": IndicatorDef(
        id="diabetes_prevalence",
        label="Diabetes prevalence",
        unit="% of adults ages 18+",
        source="WHO",
        source_id="NCD_DIABETES_PREVALENCE_CRUDE",
        aliases=("diabetes", "diabetes prevalence", "blood sugar"),
        polarity="higher_is_bad",
        bounded_100=True,
        source_filter=("Dim1 eq 'SEX_BTSX'", "Dim2 eq 'AGEGROUP_YEARS18-PLUS'"),
    ),
    "covid_cases": IndicatorDef(
        id="covid_cases",
        label="COVID-19 weekly cases",
        unit="weekly cases per million, annual average",
        source="Our World in Data",
        source_id="weekly-covid-cases-per-million-people",
        aliases=("covid", "coronavirus", "covid cases", "new covid cases"),
        polarity="higher_is_bad",
    ),
    "covid_deaths": IndicatorDef(
        id="covid_deaths",
        label="COVID-19 weekly deaths",
        unit="weekly deaths per million, annual average",
        source="Our World in Data",
        source_id="weekly-covid-deaths-per-million-people",
        aliases=("covid deaths", "coronavirus deaths", "pandemic deaths"),
        polarity="higher_is_bad",
    ),
}


COUNTRIES: dict[str, CountryOption] = {
    "IND": CountryOption(code="IND", name="India", aliases=["india", "bharat"]),
    "USA": CountryOption(code="USA", name="United States", aliases=["usa", "us", "america", "united states"]),
    "GBR": CountryOption(code="GBR", name="United Kingdom", aliases=["uk", "britain", "united kingdom", "england"]),
    "CHN": CountryOption(code="CHN", name="China", aliases=["china"]),
    "BRA": CountryOption(code="BRA", name="Brazil", aliases=["brazil"]),
    "ZAF": CountryOption(code="ZAF", name="South Africa", aliases=["south africa"]),
    "NGA": CountryOption(code="NGA", name="Nigeria", aliases=["nigeria"]),
    "PAK": CountryOption(code="PAK", name="Pakistan", aliases=["pakistan"]),
    "BGD": CountryOption(code="BGD", name="Bangladesh", aliases=["bangladesh"]),
    "IDN": CountryOption(code="IDN", name="Indonesia", aliases=["indonesia"]),
    "JPN": CountryOption(code="JPN", name="Japan", aliases=["japan"]),
    "DEU": CountryOption(code="DEU", name="Germany", aliases=["germany", "deutschland"]),
    "FRA": CountryOption(code="FRA", name="France", aliases=["france"]),
    "CAN": CountryOption(code="CAN", name="Canada", aliases=["canada"]),
    "AUS": CountryOption(code="AUS", name="Australia", aliases=["australia"]),
    "RUS": CountryOption(code="RUS", name="Russian Federation", aliases=["russia", "russian federation"]),
    "MEX": CountryOption(code="MEX", name="Mexico", aliases=["mexico"]),
    "ITA": CountryOption(code="ITA", name="Italy", aliases=["italy"]),
    "ESP": CountryOption(code="ESP", name="Spain", aliases=["spain"]),
    "LKA": CountryOption(code="LKA", name="Sri Lanka", aliases=["sri lanka"]),
    "NPL": CountryOption(code="NPL", name="Nepal", aliases=["nepal"]),
    "WLD": CountryOption(code="WLD", name="World", aliases=["world", "global", "worldwide"]),
}


def get_indicator(indicator_id: str) -> IndicatorDef:
    if indicator_id not in INDICATORS:
        raise KeyError(f"Unknown indicator: {indicator_id}")
    return INDICATORS[indicator_id]


def search_indicators(query: str | None = None) -> list[IndicatorOption]:
    if not query:
        return [indicator.to_option() for indicator in INDICATORS.values()]
    q = query.lower().strip()
    matches: list[IndicatorOption] = []
    for indicator in INDICATORS.values():
        haystack = " ".join((indicator.id, indicator.label, *indicator.aliases)).lower()
        if q in haystack:
            matches.append(indicator.to_option())
    return matches


def match_indicator(text: str, explicit_id: str | None = None) -> IndicatorDef:
    if explicit_id:
        return get_indicator(explicit_id)

    query = text.lower()
    best: tuple[int, IndicatorDef] | None = None
    for indicator in INDICATORS.values():
        score = 0
        if indicator.id.replace("_", " ") in query:
            score += 5
        if indicator.label.lower() in query:
            score += 5
        for alias in indicator.aliases:
            if alias in query:
                score += 3 + len(alias.split())
        if score and (best is None or score > best[0]):
            best = (score, indicator)

    return best[1] if best else INDICATORS["life_expectancy"]


def match_countries(text: str, explicit_codes: list[str] | None = None) -> list[str]:
    if explicit_codes:
        valid = [code.upper() for code in explicit_codes if code.upper() in COUNTRIES]
        if valid:
            return valid[:6]

    query = text.lower()
    matches: list[str] = []
    for code, country in COUNTRIES.items():
        tokens = {country.name.lower(), code.lower(), *country.aliases}
        if any(_contains_token(query, token) for token in tokens):
            matches.append(code)
    return matches[:6] or ["IND"]


def _contains_token(query: str, token: str) -> bool:
    escaped = re.escape(token.lower())
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", query) is not None


def search_countries(query: str | None = None) -> list[CountryOption]:
    if not query:
        return list(COUNTRIES.values())
    q = query.lower().strip()
    return [
        country
        for country in COUNTRIES.values()
        if q in country.code.lower()
        or q in country.name.lower()
        or any(q in alias for alias in country.aliases)
    ]
