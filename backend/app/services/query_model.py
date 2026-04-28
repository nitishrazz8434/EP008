from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline

from app.data_sources.registry import INDICATORS, IndicatorDef

INTENT_TRAINING: dict[str, list[str]] = {
    "trend": [
        "show trend of malaria in india",
        "how has life expectancy changed over time",
        "trend for hospital beds since 2010",
        "show tuberculosis data over the years",
        "what is the pattern for diabetes prevalence",
        "plot infant mortality over time",
    ],
    "compare": [
        "compare india and united states life expectancy",
        "india vs brazil covid cases",
        "compare hospital beds between india china and usa",
        "which is higher between india and pakistan",
        "compare vaccination coverage for two countries",
        "show difference between countries",
    ],
    "forecast": [
        "forecast malaria next 3 years",
        "predict tuberculosis incidence",
        "future covid cases",
        "what will happen next year",
        "estimate life expectancy in next five years",
        "forecast trend for india",
    ],
    "risk": [
        "risk alert for dengue",
        "detect outbreak risk",
        "show spike in malaria cases",
        "is there danger of outbreak",
        "public health alert",
        "find unusual increase in cases",
    ],
    "ranking": [
        "top countries by infant mortality",
        "highest covid deaths",
        "lowest life expectancy",
        "rank countries by health expenditure",
        "which country has maximum malaria",
        "show top five countries",
    ],
    "report": [
        "generate report for malaria",
        "create public health brief",
        "make summary report",
        "write analysis report",
        "download report for india",
        "prepare health data report",
    ],
}


@dataclass
class IntentPrediction:
    intent: str
    confidence: float


@dataclass
class IndicatorPrediction:
    indicator: IndicatorDef
    confidence: float


class LocalHealthQueryModel:
    def __init__(self) -> None:
        self.intent_pipeline = self._train_intent_model()
        self.indicator_vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            lowercase=True,
        )
        self.indicator_documents = [
            " ".join((indicator.id.replace("_", " "), indicator.label, *indicator.aliases))
            for indicator in INDICATORS.values()
        ]
        self.indicator_ids = list(INDICATORS.keys())
        self.indicator_matrix = self.indicator_vectorizer.fit_transform(self.indicator_documents)

    def _train_intent_model(self) -> Pipeline:
        samples: list[str] = []
        labels: list[str] = []
        for intent, examples in INTENT_TRAINING.items():
            samples.extend(examples)
            labels.extend([intent] * len(examples))
        return Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
                (
                    "classifier",
                    LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
                ),
            ]
        ).fit(samples, labels)

    def predict_intent(self, text: str) -> IntentPrediction:
        probabilities = self.intent_pipeline.predict_proba([text])[0]
        classes = list(self.intent_pipeline.classes_)
        best_index = max(range(len(probabilities)), key=lambda index: probabilities[index])
        return IntentPrediction(intent=classes[best_index], confidence=float(probabilities[best_index]))

    def predict_indicator(self, text: str) -> IndicatorPrediction:
        query_vector = self.indicator_vectorizer.transform([text])
        similarities = cosine_similarity(query_vector, self.indicator_matrix)[0]
        best_index = max(range(len(similarities)), key=lambda index: similarities[index])
        indicator_id = self.indicator_ids[best_index]
        return IndicatorPrediction(
            indicator=INDICATORS[indicator_id],
            confidence=float(similarities[best_index]),
        )


@lru_cache(maxsize=1)
def get_query_model() -> LocalHealthQueryModel:
    return LocalHealthQueryModel()
