# file: src/settings.py
from pydantic_settings import BaseSettings
# os не потрібен, pydantic_settings робить це автоматично

class Settings(BaseSettings):
    secret_key: str
    db_user: str
    db_pass: str
    db_name: str
    db_host: str
    db_port: int
    
    class Config:
        env_file = ".env.docker"

# Create a single, reusable instance
settings = Settings()