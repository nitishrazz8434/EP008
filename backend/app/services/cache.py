from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from app.settings import CACHE_DB


class SQLiteCache:
    def __init__(self, db_path: Path = CACHE_DB) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_observations (
                    dataset_id TEXT NOT NULL,
                    indicator TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    country_name TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    value REAL NOT NULL,
                    source TEXT NOT NULL,
                    PRIMARY KEY (dataset_id, indicator, country_code, year)
                )
                """
            )

    def get_json(self, key: str) -> Any | None:
        now = time.time()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload, expires_at FROM cache_entries WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if not row or row["expires_at"] < now:
            return None
        return json.loads(row["payload"])

    def set_json(self, key: str, payload: Any, ttl_seconds: int) -> None:
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO cache_entries(cache_key, payload, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    expires_at = excluded.expires_at
                """,
                (key, json.dumps(payload), now + ttl_seconds, now),
            )

    def save_custom_rows(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO custom_observations
                (dataset_id, indicator, unit, country_code, country_name, year, value, source)
                VALUES (:dataset_id, :indicator, :unit, :country_code, :country_name, :year, :value, :source)
                """,
                rows,
            )

    def list_custom_datasets(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT dataset_id, indicator, unit, source,
                       COUNT(*) AS rows_count,
                       COUNT(DISTINCT country_code) AS countries_count,
                       MIN(year) AS min_year,
                       MAX(year) AS max_year
                FROM custom_observations
                GROUP BY dataset_id, indicator, unit, source
                ORDER BY dataset_id, indicator
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_custom_series(
        self,
        dataset_id: str,
        indicator: str,
        countries: list[str],
        start_year: int | None,
        end_year: int | None,
    ) -> list[dict[str, Any]]:
        clauses = ["dataset_id = ?", "indicator = ?"]
        params: list[Any] = [dataset_id, indicator]
        if countries:
            placeholders = ",".join("?" for _ in countries)
            clauses.append(f"country_code IN ({placeholders})")
            params.extend(countries)
        if start_year is not None:
            clauses.append("year >= ?")
            params.append(start_year)
        if end_year is not None:
            clauses.append("year <= ?")
            params.append(end_year)

        query = f"""
            SELECT country_code, country_name, year, value
            FROM custom_observations
            WHERE {' AND '.join(clauses)}
            ORDER BY country_code, year
        """
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]
