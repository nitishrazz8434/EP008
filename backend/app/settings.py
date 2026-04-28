from pathlib import Path

APP_NAME = "Public Health Intelligence Assistant"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / ".cache"
CACHE_DB = CACHE_DIR / "health_cache.sqlite3"

HTTP_TIMEOUT_SECONDS = 30.0
DEFAULT_COUNTRIES = ["IND"]
DEFAULT_START_YEAR = 2010
DEFAULT_FORECAST_YEARS = 3
CACHE_TTL_SECONDS = 60 * 60 * 24
