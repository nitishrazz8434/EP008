from __future__ import annotations

import csv
import io
import re
import uuid
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.data_sources.owid import OwidClient
from app.data_sources.registry import (
    IndicatorDef,
    search_countries,
    search_indicators,
)
from app.data_sources.who import WHOClient
from app.data_sources.world_bank import DataSourceError, WorldBankClient
from app.models import (
    ChatRequest,
    ChatResponse,
    CustomAnalyzeRequest,
    DataPoint,
    QueryPlan,
    ReportRequest,
    ReportResponse,
    Series,
    SourceCitation,
    UploadResult,
)
from app.services.analytics import build_insights
from app.services.cache import SQLiteCache
from app.services.nlp import build_answer, build_clarification_answer, clarification_questions, make_plan
from app.services.reports import make_markdown_report
from app.settings import APP_NAME, APP_VERSION

app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cache = SQLiteCache()
world_bank = WorldBankClient(cache)
owid = OwidClient(cache)
who = WHOClient(cache)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


@app.get("/api/indicators")
async def indicators(q: str | None = None):
    return search_indicators(q)


@app.get("/api/countries")
async def countries(q: str | None = None):
    return search_countries(q)


@app.get("/api/datasets")
async def datasets():
    return cache.list_custom_datasets()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    plan, indicator = make_plan(request)
    questions = clarification_questions(request, plan)
    if questions:
        answer, follow_ups, limitations = build_clarification_answer(plan, indicator, questions)
        return ChatResponse(
            answer=answer,
            plan=plan,
            metric=indicator.to_metric(),
            series=[],
            insights=[],
            citations=[],
            follow_up_questions=follow_ups,
            limitations=limitations,
            needs_clarification=True,
            clarification_questions=questions,
        )

    try:
        if indicator.source == "WHO":
            series, citations = await who.fetch_series(
                indicator,
                plan.countries,
                plan.start_year,
                plan.end_year,
            )
        elif indicator.source == "Our World in Data":
            series, citations = await owid.fetch_series(
                indicator,
                plan.countries,
                plan.start_year,
                plan.end_year,
            )
        else:
            series, citations = await world_bank.fetch_series(
                indicator,
                plan.countries,
                plan.start_year,
                plan.end_year,
            )
    except DataSourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    insights = build_insights(series, indicator, plan.forecast_years)
    answer, follow_ups, limitations = build_answer(plan, indicator, series, insights)
    return ChatResponse(
        answer=answer,
        plan=plan,
        metric=indicator.to_metric(),
        series=series,
        insights=insights,
        citations=citations,
        follow_up_questions=follow_ups,
        limitations=limitations,
    )


@app.post("/api/report", response_model=ReportResponse)
async def report(request: ReportRequest) -> ReportResponse:
    return make_markdown_report(request.response)


@app.post("/api/datasets/upload", response_model=UploadResult)
async def upload_dataset(file: Annotated[UploadFile, File(...)]) -> UploadResult:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file.")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text))
    required = {"indicator", "country_code", "country_name", "year", "value"}
    if not reader.fieldnames or not required.issubset({name.lower() for name in reader.fieldnames}):
        raise HTTPException(
            status_code=400,
            detail="CSV must include indicator, country_code, country_name, year, and value columns.",
        )

    normalized_fields = {name.lower(): name for name in reader.fieldnames}
    dataset_id = _slug(file.filename) + "-" + uuid.uuid4().hex[:8]
    rows = []
    warnings: list[str] = []
    for line_number, row in enumerate(reader, start=2):
        try:
            indicator = row[normalized_fields["indicator"]].strip()
            country_code = row[normalized_fields["country_code"]].strip().upper()
            country_name = row[normalized_fields["country_name"]].strip()
            year = int(row[normalized_fields["year"]])
            value = float(row[normalized_fields["value"]])
        except (KeyError, TypeError, ValueError) as exc:
            warnings.append(f"Skipped line {line_number}: {exc}")
            continue
        if not indicator or not country_code or not country_name:
            warnings.append(f"Skipped line {line_number}: missing required text value.")
            continue
        rows.append(
            {
                "dataset_id": dataset_id,
                "indicator": indicator,
                "unit": row.get(normalized_fields.get("unit", ""), "").strip() or "value",
                "country_code": country_code,
                "country_name": country_name,
                "year": year,
                "value": value,
                "source": row.get(normalized_fields.get("source", ""), "").strip() or file.filename,
            }
        )

    cache.save_custom_rows(rows)
    return UploadResult(
        dataset_id=dataset_id,
        rows_ingested=len(rows),
        indicators=sorted({row["indicator"] for row in rows}),
        countries=sorted({row["country_code"] for row in rows}),
        warnings=warnings[:25],
    )


@app.post("/api/datasets/analyze", response_model=ChatResponse)
async def analyze_custom_dataset(request: CustomAnalyzeRequest) -> ChatResponse:
    metadata = [
        row
        for row in cache.list_custom_datasets()
        if row["dataset_id"] == request.dataset_id and row["indicator"] == request.indicator
    ]
    if not metadata:
        raise HTTPException(status_code=404, detail="Dataset or indicator was not found.")

    rows = cache.get_custom_series(
        request.dataset_id,
        request.indicator,
        [code.upper() for code in request.countries or []],
        request.start_year,
        request.end_year,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No rows matched the selected custom dataset filters.")

    grouped: dict[str, dict[str, object]] = {}
    for row in rows:
        code = str(row["country_code"])
        grouped.setdefault(code, {"name": row["country_name"], "points": []})
        grouped[code]["points"].append(DataPoint(year=int(row["year"]), value=float(row["value"])))

    series = [
        Series(
            country_code=code,
            country_name=str(data["name"]),
            points=sorted(data["points"], key=lambda point: point.year),  # type: ignore[arg-type]
        )
        for code, data in grouped.items()
    ]
    metric = IndicatorDef(
        id=f"custom_{request.indicator}",
        label=request.indicator.replace("_", " ").title(),
        unit=str(metadata[0]["unit"]),
        source="Custom CSV",
        source_id=request.dataset_id,
        aliases=(request.indicator,),
        polarity=_infer_polarity(request.indicator),
    )
    plan = QueryPlan(
        raw_query=f"Analyze uploaded dataset {request.dataset_id}: {request.indicator}",
        intent="report",
        indicator_id=metric.id,
        countries=[item.country_code for item in series],
        start_year=request.start_year,
        end_year=request.end_year,
        forecast_years=request.forecast_years,
        chart="line",
    )
    insights = build_insights(series, metric, request.forecast_years)
    answer, follow_ups, limitations = build_answer(
        plan=plan,
        indicator=metric,
        series=series,
        insights=insights,
    )

    return ChatResponse(
        answer=answer,
        plan=plan,
        metric=metric.to_metric(),
        series=series,
        insights=insights,
        citations=[
            SourceCitation(
                name="Uploaded CSV dataset",
                url="local-upload",
                accessed_via=request.dataset_id,
                note=f"Custom indicator {request.indicator}.",
            )
        ],
        follow_up_questions=follow_ups,
        limitations=limitations,
    )


def _slug(value: str) -> str:
    stem = value.rsplit(".", 1)[0].lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return stem or "dataset"


def _infer_polarity(indicator: str) -> str:
    lower = indicator.lower()
    if any(token in lower for token in ("coverage", "vaccination", "immunization", "beds", "doctors", "nurses")):
        return "higher_is_good"
    if any(token in lower for token in ("cases", "mortality", "death", "incidence", "prevalence", "risk")):
        return "higher_is_bad"
    return "mixed"
