export type IndicatorOption = {
  id: string;
  label: string;
  unit: string;
  source: string;
  aliases: string[];
};

export type CountryOption = {
  code: string;
  name: string;
  aliases: string[];
};

export type SourceCitation = {
  name: string;
  url: string;
  accessed_via: string;
  note?: string | null;
};

export type DataPoint = {
  year: number;
  value: number;
};

export type Series = {
  country_code: string;
  country_name: string;
  points: DataPoint[];
};

export type ForecastPoint = {
  year: number;
  value: number;
  lower: number;
  upper: number;
};

export type RiskAssessment = {
  level: "low" | "moderate" | "high" | "insufficient_data";
  score: number;
  reason: string;
};

export type SeriesInsight = {
  country_code: string;
  country_name: string;
  latest_year: number | null;
  latest_value: number | null;
  previous_value: number | null;
  percent_change: number | null;
  trend_label: string;
  annual_slope: number | null;
  r_squared: number | null;
  min_value: number | null;
  max_value: number | null;
  risk: RiskAssessment;
  forecast: ForecastPoint[];
  data_quality: string[];
};

export type MetricInfo = {
  id: string;
  label: string;
  unit: string;
  source: string;
  source_id: string;
  polarity: "higher_is_good" | "higher_is_bad" | "mixed";
  bounded_100: boolean;
};

export type QueryPlan = {
  raw_query: string;
  intent: "trend" | "compare" | "forecast" | "risk" | "ranking" | "report";
  indicator_id: string;
  countries: string[];
  start_year: number | null;
  end_year: number | null;
  forecast_years: number;
  chart: "line" | "bar" | "ranking";
};

export type ChatResponse = {
  answer: string;
  plan: QueryPlan;
  metric: MetricInfo;
  series: Series[];
  insights: SeriesInsight[];
  citations: SourceCitation[];
  follow_up_questions: string[];
  limitations: string[];
  needs_clarification: boolean;
  clarification_questions: string[];
};

export type ChatRequest = {
  message: string;
  indicator_id?: string;
  countries?: string[];
  start_year?: number;
  end_year?: number;
  forecast_years?: number;
};

export type ReportResponse = {
  title: string;
  markdown: string;
};

export type UploadResult = {
  dataset_id: string;
  rows_ingested: number;
  indicators: string[];
  countries: string[];
  warnings: string[];
};

export type CustomAnalyzeRequest = {
  dataset_id: string;
  indicator: string;
  countries?: string[];
  start_year?: number;
  end_year?: number;
  forecast_years?: number;
};
