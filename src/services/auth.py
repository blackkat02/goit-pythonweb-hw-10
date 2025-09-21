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
        except ConnectionErrors as conn_err:
            raise
        except Exception as err:
            raise


# ---------------- DEPENDENCIES ----------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
auth_service = AuthService()


def get_auth_service() -> AuthService:
    """Dependency that returns an instance of AuthService."""
    return auth_service

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_session),
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    email = auth_service.decode_jwt_token(token, scope="access_token")

    if email is None:
        raise credentials_exception

    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_email(email)

    if user is None:
        raise credentials_exception

    return user
