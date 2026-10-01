from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "content-factory"
    database_url: str = "sqlite:///./content_factory.db"

    storage_endpoint: str = ""
    storage_bucket: str = "content-factory"
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_region: str = "auto"

    encryption_key: str = "CHANGE_ME"
    api_worker_token: str = "CHANGE_ME_WORKER_TOKEN"

    llm_provider: str = "gemini"
    llm_model: str = "gemini-1.5-flash"
    llm_api_key: str = ""

    tts_provider: str = "edge-tts"
    tts_model: str = "vi-VN-HoaiMyNeural"
    tts_api_key: str = ""

    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = "http://localhost:8000/api/v1/accounts/oauth/callback"
    tiktok_site_verification: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/accounts/oauth/callback"
    meta_app_id: str = ""
    meta_app_secret: str = ""

    max_render_jobs_per_day: int = 20
    max_jobs_per_source_per_hour: int = 30


settings = Settings()
