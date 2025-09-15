from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional

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
    Включає поле password, яке необхідне лише під час реєстрації.
    """
    password: str = Field(min_length=6)

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
    created_at: Optional[str] = None
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
    avatar: Optional[str] = Field(None, min_length=3, max_length=50)
