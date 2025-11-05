from pydantic import BaseSettings

class Settings(BaseSettings):
    ESPN_API_KEY: str
    CACHE_EXPIRATION: int = 300  # Default cache expiration time in seconds

    class Config:
        env_file = ".env"

settings = Settings()