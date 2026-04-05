from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "AI-News-Bot/1.0"
    database_url: str = "sqlite+aiosqlite:///./ai_news.db"
    scrape_interval_hours: int = 6
    max_articles_per_source: int = 20
    log_level: str = "INFO"


settings = Settings()
