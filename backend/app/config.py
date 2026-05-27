from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # WhatsApp Cloud API
    whatsapp_token: str = ""
    whatsapp_business_id: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_api_version: str = "v21.0"

    # Auth
    agent_username: str = "admin"
    agent_password: str = ""
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_hours: int = 24

    # DB
    database_url: str = "postgresql+asyncpg://avlok:avlok_pw@localhost:5432/avlok_wa"

    # Misc
    public_base_url: str = "http://localhost:8000"
    media_dir: str = "./media"
    cors_origins: str = ""  # optional extra explicit origins, comma-separated
    # Regex of allowed origins. Matches avlokai.com + common tunnel/host providers.
    cors_origin_regex: str = (
        r"^https?://("
        r"localhost(:\d+)?|127\.0\.0\.1(:\d+)?|"
        r"([a-z0-9-]+\.)*avlokai\.com|"
        r"([a-z0-9-]+\.)*devtunnels\.ms|"
        r"([a-z0-9-]+\.)*github\.io|"
        r"([a-z0-9-]+\.)*ngrok(-free)?\.app|"
        r"([a-z0-9-]+\.)*ngrok\.io|"
        r"([a-z0-9-]+\.)*vercel\.app"
        r")$"
    )

    @property
    def graph_url(self) -> str:
        return f"https://graph.facebook.com/{self.whatsapp_api_version}"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
