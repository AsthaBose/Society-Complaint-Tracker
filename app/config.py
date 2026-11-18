"""Settings read from environment variables, with safe-for-development defaults."""
import os

DEFAULT_SECRET = "dev-only-secret-change-me-before-deploying"

SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET)
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "480"))

# Anyone who registers with this code becomes a committee member.
# Without it, every new account is a plain resident.
COMMITTEE_CODE = os.getenv("COMMITTEE_CODE", "committee-2026")


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./complaints.db")
    # Hosts like Render/Railway hand out postgres:// URLs; SQLAlchemy 2 wants an explicit driver.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _database_url()
