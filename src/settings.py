# file: src/settings.py
# from pydantic_settings import BaseSettings
# # os не потрібен, pydantic_settings робить це автоматично

# class Settings(BaseSettings):
#     secret_key: str
#     db_user: str
#     db_pass: str
#     db_name: str
#     db_host: str
#     db_port: int
    
#     class Config:
#         env_file = ".env.docker"

# # Create a single, reusable instance
# settings = Settings()


from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    db_user: str
    db_pass: str
    db_name: str
    db_host: str
    db_port: int
    
    # Налаштування для FastAPI-Mail
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int
    mail_server: str
    mail_from_name: str
    mail_starttls: bool
    mail_ssl_tls: bool
    mail_use_credentials: bool
    mail_validate_certs: bool
    
    class Config:
        env_file = ".env.docker"

# Create a single, reusable instance
settings = Settings()