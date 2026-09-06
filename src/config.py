"""
Configuration and Environment Settings for HudhudRadar.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Application Info
    APP_ENV: str = Field(default="development", description="Application Environment: development, staging, production")
    APP_DEBUG: bool = Field(default=True, description="Debug mode")
    PORT: int = Field(default=8000, description="Server port")
    HOST: str = Field(default="0.0.0.0", description="Server host")
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production-32-chars-min", description="App secret key")

    # Supabase Settings
    SUPABASE_URL: Optional[str] = Field(default=None, description="Supabase project URL")
    SUPABASE_KEY: Optional[str] = Field(default=None, description="Supabase public/anon key")
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(default=None, description="Supabase service role key")

    # Meta Graph API Settings
    META_GRAPH_API_BASE_URL: str = Field(default="https://graph.facebook.com/v26.0", description="Base URL for Meta Graph API")
    META_APP_ID: Optional[str] = Field(default=None, description="Meta App ID")
    META_APP_SECRET: Optional[str] = Field(default=None, description="Meta App Secret for webhook HMAC verification")
    META_PAGE_ID: Optional[str] = Field(default=None, description="Facebook Page ID")
    META_PAGE_ACCESS_TOKEN: Optional[str] = Field(default=None, description="Meta Page Access Token")
    META_INSTAGRAM_ACCOUNT_ID: Optional[str] = Field(default=None, description="Instagram Business Account ID")
    META_WEBHOOK_VERIFY_TOKEN: str = Field(default="hudhud-radar-verify-token-secret", description="Webhook verify token")
    WEBHOOK_VERIFY_TOKEN: Optional[str] = Field(default=None, description="Legacy/Vercel alias for Webhook verify token")
    CRON_SECRET: Optional[str] = Field(default=None, description="Shared secret for cron endpoints (Authorization: Bearer <secret>)")

    @property
    def EFFECTIVE_WEBHOOK_VERIFY_TOKEN(self) -> str:
        return self.WEBHOOK_VERIFY_TOKEN or self.META_WEBHOOK_VERIFY_TOKEN

    LLM_PROVIDER: str = Field(default="gemini", description="LLM provider: gemini (OpenAI reserved for future SaaS phase)")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key (unused — reserved for future)")
    LLM_MODEL: str = Field(default="gemini-flash-latest", description="LLM model name")

    # Threads App (separate from the main Meta app — Threads uses its own OAuth)
    THREADS_APP_ID: Optional[str] = Field(default=None, description="Threads App ID")
    THREADS_APP_SECRET: Optional[str] = Field(default=None, description="Threads App Secret")
    THREADS_REDIRECT_URI: str = Field(
        default="https://hudhud-radar-steel.vercel.app/api/threads/oauth/callback",
        description="Threads OAuth redirect URI",
    )
    THREADS_BASE_URL: str = Field(default="https://graph.threads.net/v1.0", description="Threads Graph API base URL")

    # Rate Limiting & Safety Governance
    MAX_MESSAGES_PER_MINUTE: int = Field(default=20, description="Maximum outbound messages per minute")
    ENFORCE_24H_WINDOW: bool = Field(default=True, description="Enforce Meta 24-hour standard messaging window")
    REQUIRE_MANUAL_IDENTITY_CONFIRMATION: bool = Field(default=True, description="Require human confirmation for ambiguous identities")
    CONFIDENCE_THRESHOLD_AUTO_LINK: float = Field(default=0.95, description="Score threshold for auto linking (only deterministic)")
    CONFIDENCE_THRESHOLD_QUEUE_REVIEW: float = Field(default=0.50, description="Score threshold to queue for manual review")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_security(self):
        """Validates critical security settings for production deployments."""
        if self.APP_ENV.lower() == "production":
            if "dev-secret-key" in self.SECRET_KEY:
                print("WARNING: Running in production with default SECRET_KEY. Please configure SECRET_KEY in environment variables.")
            if not self.META_APP_SECRET:
                print("WARNING: META_APP_SECRET is not configured in environment variables.")


settings = Settings()
settings.validate_security()
