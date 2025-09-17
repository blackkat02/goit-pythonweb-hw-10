from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional


class TokenSchema(BaseModel):
    """
    Схема для повернення токенів доступу та оновлення.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ResetPasswordSchema(BaseModel):
    """
    Схема для скидання пароля за допомогою токена.
    """

    token: str
    new_password: str = Field(min_length=6)


class RequestEmailSchema(BaseModel):
    """
    Схема для запиту на повторну верифікацію пошти.
    """

    email: EmailStr
