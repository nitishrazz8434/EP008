import type {
  ChatRequest,
  ChatResponse,
  CountryOption,
  CustomAnalyzeRequest,
  IndicatorOption,
  ReportResponse,
  UploadResult
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message = payload?.detail ?? `Request failed with ${response.status}`;
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function fetchIndicators(): Promise<IndicatorOption[]> {
  return request<IndicatorOption[]>("/api/indicators");
}

export function fetchCountries(): Promise<CountryOption[]> {
  return request<CountryOption[]>("/api/countries");
}

export function askQuestion(body: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
}

export function createReport(response: ChatResponse): Promise<ReportResponse> {
  return request<ReportResponse>("/api/report", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ response })
  });
}

export function uploadDataset(file: File): Promise<UploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  return request<UploadResult>("/api/datasets/upload", {
    method: "POST",
    body: formData
  });
}

export function analyzeDataset(body: CustomAnalyzeRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/api/datasets/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
}
