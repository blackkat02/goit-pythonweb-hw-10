from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime


# --- Базові схеми ---


class UserBaseSchema(BaseModel):
    """
    Базова схема для користувача, що містить загальні поля.
    Використовується для створення інших, специфічних схем.
    """

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr


# --- Схеми для реєстрації та входу ---


class UserCreateSchema(UserBaseSchema):
    """
    Схема для реєстрації нового користувача.
    Включає поле password та avatar, які необхідні під час реєстрації.
    """

    password: str = Field(min_length=6)
    avatar: Optional[str] = None
    confirmed: bool = False


class UserLoginSchema(BaseModel):
    """
    Схема для входу в систему.
    """

    email: EmailStr
    password: str


# --- Схеми для відповіді API ---


class UserResponseSchema(UserBaseSchema):
    """
    Схема для повернення даних користувача.
    Не містить пароля, але включає ID та інші службові поля.
    """

    id: int
    # Використовуємо datetime замість str для коректної типізації.
    created_at: datetime
    avatar: Optional[str] = None
    confirmed: bool = False

    model_config = ConfigDict(from_attributes=True)


# --- Схема для оновлення даних користувача ---


class UserUpdateSchema(BaseModel):
    """
    Схема для часткового оновлення даних користувача.
    Всі поля є опціональними. Пароль оновлюється окремим запитом.
    """

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    # Виправлено: avatar тепер має коректну довжину.
    avatar: Optional[str] = Field(None, min_length=3, max_length=255)


class TokenSchema(BaseModel):
    """
    Схема для JWT-токенів.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
