from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "portfolio-base-bucket"
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    KAGGLE_USERNAME: str = ""
    KAGGLE_KEY: str = ""

    model_config = {"env_file": (".env", "../.env"), "extra": "ignore"}

settings = Settings()
