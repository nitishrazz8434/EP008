import { FormEvent, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bot,
  Database,
  Download,
  Globe2,
  LineChart as LineChartIcon,
  Loader2,
  Send
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { askQuestion, createReport } from "./api";
import type { ChatResponse } from "./types";

type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  text: string;
  response?: ChatResponse;
};

const STARTERS = [
  "Forecast malaria in India next 3 years",
  "Compare life expectancy in India and USA since 2010",
  "Is tuberculosis risk increasing in India?",
  "Show COVID cases in India and Brazil from 2020 to 2023"
];

const COLORS = ["#19766f", "#d95f43", "#2f6fd6", "#be8a12", "#7754c8", "#27313a"];

export default function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendQuestion(question: string) {
    const cleanQuestion = question.trim();
    if (!cleanQuestion || loading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: cleanQuestion
    };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await askQuestion({ message: cleanQuestion });
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: response.answer,
          response
        }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The chatbot could not answer that question.");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendQuestion(input);
  }

  async function downloadReport(response: ChatResponse) {
    const report = await createReport(response);
    const blob = new Blob([report.markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${report.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="chat-shell">
      <header className="chat-header">
        <div className="brand-row">
          <div className="brand-left">
            <div className="brand-icon">
              <Activity size={22} aria-hidden="true" />
            </div>
            <div>
              <h1>HealthPulse AI</h1>
              <p>Public health chatbot</p>
            </div>
          </div>
        </div>
      </header>

      <section className={messages.length ? "conversation" : "conversation empty"} aria-live="polite">
        {!messages.length && !loading ? (
          <StartPanel
            input={input}
            loading={loading}
            onInput={setInput}
            onSelect={(starter) => void sendQuestion(starter)}
            onSubmit={handleSubmit}
          />
        ) : null}

        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onAsk={(question) => void sendQuestion(question)}
            onReport={downloadReport}
          />
        ))}

        {loading ? (
          <div className="message-row assistant">
            <div className="avatar">
              <Bot size={18} aria-hidden="true" />
            </div>
            <div className="bubble loading-bubble">
              <Loader2 className="spin" size={18} aria-hidden="true" />
              Checking public health data...
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="error-message" role="alert">
            <AlertTriangle size={18} aria-hidden="true" />
            {error}
          </div>
        ) : null}
      </section>

      {messages.length ? (
        <section className="composer-panel" aria-label="Ask the chatbot">
          <Composer input={input} loading={loading} onInput={setInput} onSubmit={handleSubmit} />
        </section>
      ) : null}
    </main>
  );
}

function StartPanel({
  input,
  loading,
  onInput,
  onSelect,
  onSubmit
}: {
  input: string;
  loading: boolean;
  onInput: (value: string) => void;
  onSelect: (starter: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <section className="start-panel" aria-label="Example public health questions">
      <div className="start-mark">
        <Globe2 size={28} aria-hidden="true" />
      </div>
      <h2>Track public health with AI</h2>
      <p>Ask in plain English and get WHO-first trends, forecasts, compact charts, and sources.</p>
      <Composer input={input} loading={loading} onInput={onInput} onSubmit={onSubmit} variant="hero" />
      <div className="starter-chips">
        {STARTERS.map((starter, index) => (
          <button key={starter} type="button" onClick={() => onSelect(starter)}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            {starter}
          </button>
        ))}
      </div>
    </section>
  );
}

function Composer({
  input,
  loading,
  onInput,
  onSubmit,
  variant = "default"
}: {
  input: string;
  loading: boolean;
  onInput: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  variant?: "default" | "hero";
}) {
  return (
    <form className={`composer ${variant === "hero" ? "hero-composer" : ""}`} onSubmit={onSubmit}>
      <input
        value={input}
        onChange={(event) => onInput(event.target.value)}
        placeholder="Ask about malaria, COVID, life expectancy, hospital beds..."
        aria-label="Ask a public health question"
      />
      <button type="submit" disabled={loading || !input.trim()} aria-label="Send question">
        {loading ? <Loader2 className="spin" size={19} aria-hidden="true" /> : <Send size={19} aria-hidden="true" />}
      </button>
    </form>
  );
}

function MessageBubble({
  message,
  onAsk,
  onReport
}: {
  message: ChatMessage;
  onAsk: (question: string) => void;
  onReport: (response: ChatResponse) => Promise<void>;
}) {
  const isAssistant = message.role === "assistant";
  const response = message.response;
  const showResult = response && !response.needs_clarification && response.series.length > 0;
  const showFollowUps = response && response.follow_up_questions.length > 0;

  return (
    <div className={`message-row ${message.role}`}>
      {isAssistant ? (
        <div className="avatar">
          <Bot size={18} aria-hidden="true" />
        </div>
      ) : null}
      <article className="bubble">
        {isAssistant && response ? <ResultMeta response={response} /> : null}
        <p>{message.text}</p>
        {response?.needs_clarification ? <ClarificationBlock response={response} /> : null}
        {showResult ? <CompactResult response={response} onReport={onReport} /> : null}
        {showFollowUps ? <FollowUpQuestions questions={response.follow_up_questions} onAsk={onAsk} /> : null}
      </article>
    </div>
  );
}

function ResultMeta({ response }: { response: ChatResponse }) {
  return (
    <div className="result-meta">
      <span>{response.metric.source}</span>
      <span>{response.metric.label}</span>
      <span>{response.plan.intent}</span>
    </div>
  );
}

function ClarificationBlock({ response }: { response: ChatResponse }) {
  return (
    <div className="clarification-block">
      <strong>To answer this properly:</strong>
      <ul>
        {response.clarification_questions.map((question) => (
          <li key={question}>{question}</li>
        ))}
      </ul>
    </div>
  );
}

function FollowUpQuestions({
  questions,
  onAsk
}: {
  questions: string[];
  onAsk: (question: string) => void;
}) {
  return (
    <div className="follow-up-strip" aria-label="Follow-up questions">
      {questions.slice(0, 4).map((question) => (
        <button key={question} type="button" onClick={() => onAsk(question)}>
          {question}
        </button>
      ))}
    </div>
  );
}

function CompactResult({
  response,
  onReport
}: {
  response: ChatResponse;
  onReport: (response: ChatResponse) => Promise<void>;
}) {
  const primary = response.insights[0];

  return (
    <div className="result-card">
      <div className="result-topline">
        <div>
          <strong>{response.plan.countries.join(" vs ")}</strong>
          <span>{response.metric.unit}</span>
        </div>
        <button type="button" onClick={() => void onReport(response)}>
          <Download size={16} aria-hidden="true" />
        </button>
      </div>

      {primary ? (
        <div className="fact-strip">
          <div>
            <span>Latest</span>
            <strong>
              {formatValue(primary.latest_value)}
              {primary.latest_year ? <small>{primary.latest_year}</small> : null}
            </strong>
          </div>
          <div>
            <span>Trend</span>
            <strong>{primary.trend_label}</strong>
          </div>
          <div>
            <span>Risk</span>
            <strong>{primary.risk.level.replace("_", " ")}</strong>
          </div>
        </div>
      ) : null}

      <MiniChart response={response} />

      <details className="source-details">
        <summary>Source and limits</summary>
        <div>
          {response.citations.map((citation) => (
            <p key={citation.accessed_via}>
              <Database size={14} aria-hidden="true" />
              {citation.url.startsWith("http") ? (
                <a href={citation.url} target="_blank" rel="noreferrer">
                  {citation.name}
                </a>
              ) : (
                citation.name
              )}
            </p>
          ))}
          {response.limitations.slice(0, 2).map((limitation) => (
            <p key={limitation}>{limitation}</p>
          ))}
        </div>
      </details>
    </div>
  );
}

function MiniChart({ response }: { response: ChatResponse }) {
  const lineData = useMemo(() => {
    const rows = new Map<number, Record<string, number | string>>();
    response.series.forEach((series) => {
      series.points.forEach((point) => {
        const row = rows.get(point.year) ?? { year: point.year };
        row[series.country_name] = Number(point.value.toFixed(2));
        rows.set(point.year, row);
      });
    });
    return [...rows.values()].sort((a, b) => Number(a.year) - Number(b.year));
  }, [response.series]);

  const barData = response.insights.map((insight) => ({
    country: insight.country_name,
    value: insight.latest_value ? Number(insight.latest_value.toFixed(2)) : 0
  }));

  const useBar = response.plan.chart === "bar";
  if (!response.series.length) return null;

  return (
    <div className="mini-chart">
      <div className="mini-chart-title">
        {useBar ? <BarChart3 size={16} aria-hidden="true" /> : <LineChartIcon size={16} aria-hidden="true" />}
        {useBar ? "Comparison" : "Trend"}
      </div>
      <ResponsiveContainer width="100%" height={230}>
        {useBar ? (
          <BarChart data={barData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e1e6ed" />
            <XAxis dataKey="country" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="value" fill="#19766f" radius={[5, 5, 0, 0]} />
          </BarChart>
        ) : (
          <LineChart data={lineData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e1e6ed" />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {response.series.map((series, index) => (
              <Line
                key={series.country_code}
                type="monotone"
                dataKey={series.country_name}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2.4}
                dot={false}
                activeDot={{ r: 4 }}
                connectNulls
              />
            ))}
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

function formatValue(value: number | null) {
  if (value === null) return "NA";
  if (Math.abs(value) >= 100) return value.toFixed(0);
  return value.toFixed(2);
}
