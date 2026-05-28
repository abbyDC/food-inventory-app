from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ai_provider: str = "groq"
    groq_api_key: str = ""
    gemini_api_key: str = ""
    huggingface_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
