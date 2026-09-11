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

    # Canonical public origin (single source of truth for every absolute URL
    # the app emits: OAuth redirects, compliance callbacks, templates, scripts).
    # Domain swap = change this env var in BOTH Vercel scopes + app dashboards.
    APP_BASE_URL: str = Field(
        default="https://hudhud-radar.vercel.app",
        description="Canonical public origin without trailing slash",
    )

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
    META_WEBHOOK_VERIFY_TOKEN: Optional[str] = Field(default=None, description="Webhook verify token (must be set in production — fail-closed without it)")
    WEBHOOK_VERIFY_TOKEN: Optional[str] = Field(default=None, description="Legacy/Vercel alias for Webhook verify token")
    CRON_SECRET: Optional[str] = Field(default=None, description="Shared secret for cron endpoints (Authorization: Bearer <secret>)")

    @property
    def EFFECTIVE_WEBHOOK_VERIFY_TOKEN(self) -> str:
        return self.WEBHOOK_VERIFY_TOKEN or self.META_WEBHOOK_VERIFY_TOKEN

    LLM_PROVIDER: str = Field(default="gemini", description="LLM provider: gemini (OpenAI reserved for future SaaS phase)")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key (unused — reserved for future)")
    LLM_MODEL: str = Field(default="gemini-flash-latest", description="LLM model name")

    # Google Sign-In (direct OAuth from our backend — consent screen shows
    # APP_BASE_URL, never Supabase). Owner creates the client in Google Cloud.
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, description="Google OAuth 2.0 Client ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, description="Google OAuth 2.0 Client Secret")

    # Payments (Polar.sh first — gateway registry allows more later)
    POLAR_ACCESS_TOKEN: Optional[str] = Field(default=None, description="Polar API access token (sandbox or live)")
    POLAR_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Polar webhook signing secret (whsec_...)")
    POLAR_ORGANIZATION_ID: Optional[str] = Field(default=None, description="Polar organization id")

    # Threads App (separate from the main Meta app — Threads uses its own OAuth)
    THREADS_APP_ID: Optional[str] = Field(default=None, description="Threads App ID")
    THREADS_APP_SECRET: Optional[str] = Field(default=None, description="Threads App Secret")
    THREADS_REDIRECT_URI: Optional[str] = Field(
        default=None,
        description="Threads OAuth redirect URI (defaults to APP_BASE_URL/api/threads/oauth/callback)",
    )
    THREADS_ACCESS_TOKEN: Optional[str] = Field(default=None, description="Legacy env Threads token (fallback when no OAuth connection exists)")
    THREADS_USER_ID: Optional[str] = Field(default=None, description="Legacy env Threads user id")
    THREADS_BASE_URL: str = Field(default="https://graph.threads.net/v1.0", description="Threads Graph API base URL")

    # Instagram child app (Meta's "Instagram API with Instagram Login" product
    # creates a SEPARATE app id/secret — using the main Meta app id fails with
    # "Invalid platform app" on www.instagram.com/oauth/authorize)
    IG_APP_ID: Optional[str] = Field(default=None, description="Instagram child App ID")
    IG_APP_SECRET: Optional[str] = Field(default=None, description="Instagram child App Secret")

    @property
    def EFFECTIVE_THREADS_REDIRECT_URI(self) -> str:
        return self.THREADS_REDIRECT_URI or f"{self.APP_BASE_URL.rstrip('/')}/api/threads/oauth/callback"

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
