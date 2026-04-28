from __future__ import annotations

from app.models import ChatResponse, ReportResponse


def make_markdown_report(response: ChatResponse) -> ReportResponse:
    metric = response.metric
    title = f"{metric.label} Public Health Brief"
    lines = [
        f"# {title}",
        "",
        f"**Question:** {response.plan.raw_query}",
        "",
        "## Executive Summary",
        response.answer,
        "",
        "## Key Findings",
    ]

    for insight in response.insights:
        latest = (
            f"{insight.latest_value:.2f} {metric.unit} in {insight.latest_year}"
            if insight.latest_value is not None
            else "No latest value available"
        )
        change = (
            f"{insight.percent_change:.1f}% year-over-year"
            if insight.percent_change is not None
            else "Year-over-year change unavailable"
        )
        lines.extend(
            [
                f"- **{insight.country_name}:** {latest}; trend: {insight.trend_label}; {change}; "
                f"risk: {insight.risk.level} ({insight.risk.score:.0f}/100).",
            ]
        )

    forecast_rows = [
        (insight.country_name, point)
        for insight in response.insights
        for point in insight.forecast
    ]
    if forecast_rows:
        lines.extend(["", "## Forecast"])
        for country, point in forecast_rows:
            lines.append(
                f"- {country} {point.year}: {point.value:.2f} "
                f"(range {point.lower:.2f}-{point.upper:.2f})"
            )

    lines.extend(["", "## Data Sources"])
    for citation in response.citations:
        lines.append(f"- {citation.name}: {citation.url}")
        if citation.note:
            lines.append(f"  - {citation.note}")

    if response.limitations:
        lines.extend(["", "## Limitations"])
        for limitation in response.limitations:
            lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            "## Public Health Note",
            "This report is for data exploration and education. It is not medical advice or an official outbreak declaration.",
        ]
    )
    return ReportResponse(title=title, markdown="\n".join(lines))
