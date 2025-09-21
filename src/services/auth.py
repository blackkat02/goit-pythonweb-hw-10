import logging
from logging.handlers import RotatingFileHandler
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

import redis
import pickle
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_async_session
from src.settings import settings
from src.repository.users import UserRepository
from src.database.models import UserModel


# ---------------- LOGGING ----------------
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stdout)

file_handler = RotatingFileHandler("app.log", maxBytes=10_000_000, backupCount=5)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)

logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger("fastapi_mail").setLevel(logging.DEBUG)

logger = logging.getLogger("app.auth.email")


# ---------------- FASTMAIL CONFIG ----------------
templates_dir = Path(__file__).parent / "templates"

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.MAIL_USE_CREDENTIALS,
    VALIDATE_CERTS=settings.MAIL_VALIDATE_CERTS,
    TEMPLATE_FOLDER=templates_dir,
)

fm = FastMail(conf)
env = Environment(loader=FileSystemLoader(str(templates_dir)))


# ---------------- AUTH SERVICE ----------------
class AuthService:
    """Handles user authentication, password hashing, and token management."""

    pwd_context = CryptContext(schemes=["bcrypt"])
    redis_client = redis.Redis(host="redis", port=6379, db=0)
    ALGORITHM = "HS256"

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def create_jwt_token(
        self, payload: dict, scope: str = "access_token", expires_delta: float = 15
    ) -> str:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)
        payload["scope"] = scope
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=self.ALGORITHM)

    def decode_jwt_token(self, token: str, scope: str = "access_token") -> str:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload.get("scope") != scope:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token scope",
                )
            return payload.get("email")
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

    async def decode_verification_token(self, token: str) -> str:
        await asyncio.sleep(0)  # async-safe placeholder
        return self.decode_jwt_token(token, scope="verification_token")

    async def send_confirmation_email(self, email: str, username: str, host: str):
        """Асинхронна відправка листа підтвердження."""
        logger.info("Preparing and sending confirmation email for %s", email)

        # 1) Токен
        token = self.create_jwt_token({"email": email}, scope="verification_token")

        # 2) HTML шаблон
        template = env.get_template("email_verification.html")
        html_body = template.render(username=username, host=host, token=token)

        # 3) Лист
        message = MessageSchema(
            subject="Confirm your account",
            recipients=[email],
            body=html_body,
            subtype=MessageType.html,
        )

        # 4) Відправка
        try:
            await fm.send_message(message)
            logger.info("Confirmation email successfully sent to %s", email)
        except ConnectionErrors as conn_err:
            logger.exception(
                "SMTP connection error while sending email to %s: %s", email, conn_err
            )
            raise
        except Exception as err:
            logger.exception("Failed to send confirmation email to %s: %s", email, err)
            raise


# ---------------- DEPENDENCIES ----------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
auth_service = AuthService()


def get_auth_service() -> AuthService:
    """Dependency that returns an instance of AuthService."""
    return auth_service


logger = logging.getLogger("app.auth")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_session),
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    logger.info("Attempting to decode token...") # <-- Додайте це
    email = auth_service.decode_jwt_token(token, scope="access_token")

    if email is None:
        logger.error("Token decoding failed or email not found in payload.") # <-- Додайте це
        raise credentials_exception

    logger.info("Token decoded successfully for user: %s", email) # <-- Додайте це

    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_email(email)

    if user is None:
        logger.error("User with email %s not found in database.", email) # <-- Додайте це
        raise credentials_exception

    logger.info("User %s successfully authenticated.", user.username) # <-- Додайте це
    return user




# import logging
# from logging.handlers import RotatingFileHandler
# import sys

# LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
# logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stdout)

# # Додатковий file handler (щоб логи зберігалися в контейнері)
# file_handler = RotatingFileHandler("app.log", maxBytes=10_000_000, backupCount=5)
# file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
# root_logger = logging.getLogger()
# root_logger.addHandler(file_handler)

# # На рівні модулів можна детальніше:
# logging.getLogger("uvicorn").setLevel(logging.INFO)
# logging.getLogger("uvicorn.error").setLevel(logging.INFO)
# logging.getLogger("uvicorn.access").setLevel(logging.INFO)
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)  # або DEBUG для SQL
# logging.getLogger("fastapi_mail").setLevel(logging.DEBUG)     # fastapi-mail debug

# logger = logging.getLogger("app.auth.email")


# import asyncio
# from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
# from fastapi_mail.errors import ConnectionErrors
# from passlib.context import CryptContext
# from pathlib import Path
# import redis
# import pickle
# from jose import jwt, JWTError
# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from datetime import datetime, timezone, timedelta
# from typing import Optional
# from src.database.db import get_async_session
# from src.settings import settings
# from src.repository.users import UserRepository
# from src.database.models import UserModel
# from sqlalchemy.ext.asyncio import AsyncSession
# from jinja2 import Environment, FileSystemLoader

# from src.settings import settings



# class AuthService:
#     """Handles user authentication, password hashing, and token management."""

#     pwd_context = CryptContext(schemes=["bcrypt"])
#     redis_client = redis.Redis(host="redis", port=6379, db=0)
#     ALGORITHM = "HS256"

#     async def decode_verification_token(self, token: str) -> str:
#     # Тут async логіка, наприклад:
#         await asyncio.sleep(0)  # placeholder, щоб прибрати попередження
#         return self.decode_jwt_token(token, scope="verification_token")



#     def verify_password(self, plain_password: str, hashed_password: str) -> bool:
#         return self.pwd_context.verify(plain_password, hashed_password)

#     def hash_password(self, password: str) -> str:
#         return self.pwd_context.hash(password)

#     def create_jwt_token(self, payload: dict, scope: str = "access_token", expires_delta: float = 15) -> str:
#         payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)
#         payload["scope"] = scope
#         return jwt.encode(payload, settings.secret_key, algorithm=self.ALGORITHM)

#     def decode_jwt_token(self, token: str, scope: str = "access_token") -> str:
#         try:
#             payload = jwt.decode(token, settings.secret_key, algorithms=[self.ALGORITHM])
#             if payload.get("scope") != scope:
#                 raise HTTPException(
#                     status_code=status.HTTP_401_UNAUTHORIZED,
#                     detail="Invalid token scope",
#                 )
#             return payload.get("email")
#         except JWTError:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Could not validate credentials",
#             )

#     # async def send_confirmation_email(self, email: str, username: str, host: str):
#     #     """
#     #     Асинхронна відправка листа підтвердження — з докладними логами.
#     #     """
#     #     logger.info("Preparing confirmation email for %s", email)

#     #     # 1) Згенерувати токен підтвердження
#     #     token = self.create_jwt_token({"email": email}, scope="verification_token")
#     #     logger.debug("Generated verification token for %s (len=%d)", email, len(token))

#     #     # 2) Підготувати HTML (рендеримо локально, щоб мати контроль)
#     #     templates_dir = Path(__file__).parent / "templates"
#     #     template_name = "email_verification.html"
#     #     try:
#     #         env = Environment(loader=FileSystemLoader(str(templates_dir)))
#     #         template = env.get_template(template_name)
#     #         html_body = template.render(username=username, host=host, token=token)
#     #         logger.debug("Rendered email template (%s). Length=%d", template_name, len(html_body))
#     #     except Exception as render_err:
#     #         logger.exception(
#     #             "Failed to render email template '%s' from %s. Available files: %s",
#     #             template_name,
#     #             templates_dir,
#     #             list(templates_dir.glob("*.html")),
#     #         )
#     #         raise

#     #     # 3) Підготувати ConnectionConfig (не логуй паролі!)
#     #     conf = ConnectionConfig(
#     #         MAIL_USERNAME=settings.mail_username,
#     #         MAIL_PASSWORD=settings.mail_password,
#     #         MAIL_FROM=settings.mail_from,
#     #         MAIL_PORT=settings.mail_port,
#     #         MAIL_SERVER=settings.mail_server,
#     #         MAIL_FROM_NAME=settings.mail_from_name,
#     #         MAIL_STARTTLS=settings.mail_starttls,
#     #         MAIL_SSL_TLS=settings.mail_ssl_tls,
#     #         USE_CREDENTIALS=settings.mail_use_credentials,
#     #         VALIDATE_CERTS=settings.mail_validate_certs,
#     #         TEMPLATE_FOLDER=templates_dir,
#     #     )

#     #     logger.info("Attempting to send email to %s via %s:%s", email, settings.mail_server, settings.mail_port)

#     #     # 4) Відправка
#     #     try:
#     #         message = MessageSchema(
#     #             subject="Confirm your account",
#     #             recipients=[email],
#     #             body=html_body,
#     #             subtype=MessageType.html,
#     #         )

#     #         fm = FastMail(conf)
#     #         await fm.send_message(message)  # Використовуємо наш html_body напряму
#     #         logger.info("Confirmation email successfully sent to %s", email)

#     #     except ConnectionErrors as conn_err:
#     #         logger.exception("SMTP connection error while sending email to %s: %s", email, conn_err)
#     #         raise
#     #     except Exception as err:
#     #         logger.exception("Unexpected error when sending email to %s: %s", email, err)
#     #         raise


#     async def send_confirmation_email(self, email: str, username: str, host: str):
#         """Асинхронна відправка листа підтвердження."""
#         logger.info("Preparing and sending confirmation email for %s", email)
        
#         token = self.create_jwt_token({"email": email}, scope="verification_token")
        
#         templates_dir = Path(__file__).parent / "templates"
#         env = Environment(loader=FileSystemLoader(str(templates_dir)))
#         template = env.get_template("email_verification.html")
#         html_body = template.render(username=username, host=host, token=token)

#         message = MessageSchema(
#             subject="Confirm your account",
#             recipients=[email],
#             body=html_body,
#             subtype=MessageType.html,
#         )
        
#         try:
#             await self.fm.send_message(message)
#             logger.info("Confirmation email successfully sent to %s", email)
#         except Exception as err:
#             logger.exception("Failed to send confirmation email to %s: %s", email, err)
#             raise
        

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# auth_service = AuthService()

# # Ось та функція-залежність, яку ти забуваєш
# def get_auth_service() -> AuthService:
#     """ Dependency that returns an instance of AuthService. """
#     return auth_service


# async def get_current_user(
#     token: str = Depends(oauth2_scheme),
#     db: AsyncSession = Depends(get_async_session),
# ) -> UserModel:
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#     )
    
#     email = auth_service.decode_jwt_token(token, scope="access_token")
#     if email is None:
#         raise credentials_exception

#     user_repo = UserRepository(db)
#     user = await user_repo.get_user_by_email(email)

#     if user is None:
#         raise credentials_exception

#     return user