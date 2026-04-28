# HealthPulse AI

HealthPulse AI is a full-stack public health data analyst chatbot. It answers natural-language questions, fetches live public-health indicators, creates chart-ready time series, scores risk, forecasts future values, and generates source-cited markdown reports.

## What Makes It More Than a Demo

- React + TypeScript analyst workspace instead of a simple console chatbot.
- FastAPI backend with structured APIs and validation.
- Live public data from WHO Global Health Observatory, World Bank Indicators, and Our World in Data.
- SQLite response cache to reduce repeated API calls.
- Local AI/NLP model using TF-IDF and logistic regression for trend, comparison, risk, forecast, ranking, and report questions.
- Character n-gram ML matching for health indicators, so natural wording like "TB", "doctors", or "baby deaths" maps to the right dataset.
- Forecasting with damped recent-trend modeling, confidence ranges, and R-squared.
- Risk scoring based on recent baseline, year-over-year change, and indicator polarity.
- Source citations and limitations in every answer.
- Custom CSV ingestion endpoint for regional or college-provided health datasets.

## Architecture

```text
React + TypeScript UI
        |
        v
FastAPI backend
        |
        +-- NLP query planner
        +-- Local ML intent and indicator model
        +-- Public data clients
        +-- SQLite cache
        +-- Analytics engine
        +-- Forecast and risk modules
        +-- Report generator
```

## Public Data Sources

- WHO Global Health Observatory OData API: https://www.who.int/data/gho/info/gho-odata-api
- World Bank Indicators API: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
- Our World in Data Grapher: https://ourworldindata.org/grapher

## Source Strategy

WHO is the primary source for public-health indicators such as mortality, immunization, health workforce, hospital beds, health expenditure, diabetes, malaria, and tuberculosis. Our World in Data is used for COVID time-series questions because it exposes simpler country-level COVID Grapher series for this chatbot flow. The World Bank client remains in the backend as a fallback integration, but the current chatbot indicator set is WHO-first except for COVID.

## Run Locally

Open two terminals from this folder.

Backend:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
backend\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Then open http://127.0.0.1:5173.

## Test

```powershell
backend\.venv\Scripts\python -m pytest backend\tests -q
backend\.venv\Scripts\python -m ruff check backend\app backend\tests
cd frontend
npm run build
npm audit --audit-level=moderate
```

## Example Questions

- Compare life expectancy in India and United States from 2010 to 2022.
- Forecast tuberculosis incidence in India for the next 3 years.
- Show risk alerts for malaria incidence in India since 2012.
- Compare hospital beds in India, China, and United States from 2010 to 2021.
- Compare COVID cases in India and Brazil from 2020 to 2023.

## Custom CSV Format

The upload endpoint accepts UTF-8 CSV files with these required columns:

```csv
indicator,country_code,country_name,year,value,unit,source
```

Use this for district, state, hospital, or college-provided datasets that are not available in global APIs.

## Important Note

This project is for data exploration and education. It does not provide medical advice and does not issue official public-health alerts.
