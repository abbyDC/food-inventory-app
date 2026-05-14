from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./food_inventory.db"
    ai_provider: str = "groq"
    groq_api_key: str = ""
    gemini_api_key: str = ""
    huggingface_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
