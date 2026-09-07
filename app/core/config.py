from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://inventory:inventory@postgres:5432/inventory_db"
    reservation_ttl_minutes: int = 15
    echo_sql: bool = False


settings = Settings()
