# HealthPulse AI Model Card

## Model Purpose

The project uses a local AI/NLP layer to convert a public-health question into a structured analysis plan:

- intent: trend, compare, forecast, risk, ranking, or report
- indicator: life expectancy, malaria incidence, tuberculosis incidence, vaccination coverage, hospital beds, and other supported indicators
- countries and time range
- forecast horizon

## Model Type

- Intent model: TF-IDF vectorizer + Logistic Regression classifier
- Indicator model: TF-IDF character n-gram similarity over indicator names and aliases
- Forecast model: damped recent-trend time-series forecast with confidence ranges
- Risk model: anomaly-style scoring using recent baseline, year-over-year change, and health-indicator polarity

## Why This Is Better Than Rule Matching

The original version used mostly keyword rules. That was brittle and made the project feel like a dashboard pretending to be AI. The current version trains a lightweight local classifier for query intent and uses ML similarity for indicator matching. This keeps the project explainable while still using actual machine-learning methods.

## Supported Data Sources

- WHO Global Health Observatory OData API
- World Bank Indicators API
- Our World in Data Grapher CSV API
- Uploaded custom CSV datasets

WHO is used first for the core public-health indicators. Other sources are intentionally limited to cases where WHO is not the best fit for the current chatbot flow, especially COVID time-series data.

## Limitations

- The intent model is trained on compact synthetic examples, so it should be expanded with real user questions for production use.
- Forecasts are educational statistical estimates, not official public-health predictions.
- Global public datasets may lag behind local government surveillance reports.
- The system is not a medical diagnosis tool.

## Suggested Future Upgrade

Add an optional LLM/RAG layer for richer natural-language explanations while keeping the local ML model as the fallback. This requires an API key or a local language model runtime.
