
import os


def get_api_url() -> str:
    """
    Return the base URL of the running allocation API.
    """
    return os.environ.get(
        "API_URL",
        "http://localhost:5000",
    )


def get_postgres_uri() -> str:
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "postgres")
    database = os.environ.get("DB_NAME", "allocation")

    return (
        f"postgresql://{user}:{password}"
        f"@{host}:{port}/{database}"
    )


def get_database_uri() -> str:
    """
    Return the SQLite database connection URI.
    The database is stored in the project directory.
    """
    database_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "allocation.db",
    )

    return f"sqlite:///{database_path}"
