from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Gemini AI Setup
    GEMINI_API_KEY: SecretStr = Field(..., description='Gemini API key')

    # Telegram "Human-in-the-loop"
    TELEGRAM_BOT_TOKEN: SecretStr = Field(..., description="Bot token from @BotFather")
    TELEGRAM_CHAT_ID: int = Field(..., description="You Telegram user or group chat ID")

    # Optional / Future Social Tokens (Phase 2)
    THREADS_APP_ID: str
    THREADS_ACCESS_TOKEN: SecretStr  # <-- Add this line

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate config on module import
try:
    settings = Settings()
except Exception as e:
    print(f"❌ Configuration loading error: Check your .env file!\n{e}")
    raise e