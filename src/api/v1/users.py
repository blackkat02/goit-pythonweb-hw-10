from fastapi import (
    Depends,
    APIRouter,
    HTTPException,
    status,
    BackgroundTasks,
    Request,
    Query,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from src.database.db import get_async_session
from src.schemas.users import (
    UserBaseSchema,
    UserCreateSchema,
    UserLoginSchema,
    UserResponseSchema,
    UserUpdateSchema,
)
from src.repository.users import UserRepository
from src.services.auth import AuthService

# from src.repository import auth as auth_repository
# from src.services.auth import auth_service
# from src.services.email import send_email

router = APIRouter(prefix="/users", tags=["users"])
# HTTP 409 Conflict


@router.post(
    "/", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED
)
async def create_new_user(
    user_in: UserCreateSchema, db: AsyncSession = Depends(get_async_session)
):
    """
    Creates a new user.

    This endpoint creates a new user in the database using the provided data.
    """
    user_repo = UserRepository(db)
    # ПРИМІТКА: Цей виклик має бути в сервісному шарі, а не тут.
    # Я передаю hashed_password для демонстрації, але це не найкраща практика.
    hashed_password = await AuthService().hash_password(user_in.password)
    db_user = await user_repo.create_user(user_in, hashed_password)
    return db_user


@router.get("/", response_model=List[UserResponseSchema])
async def get_all_users(
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """
    Retrieves all user with pagination.

    This endpoint returns a paginated list of all users stored in the database.
    - **skip**: The number of records to skip (for pagination).
    - **limit**: The maximum number of records to return.
    """
    user_repo = UserRepository(db)
    users = await user_repo.get_users(skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserResponseSchema)
async def read_user(user_id: int, db: AsyncSession = Depends(get_async_session)):
    """
    Retrieves a single user by its ID.

    This endpoint returns a single user by its unique ID.
    - **user_id**: The unique identifier of the user.

    Raises:
        HTTPException: If the contact with the specified ID is not found.
    """
    user_repo = UserRepository(db)
    db_user = await user_repo.get_user_by_id(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return db_user


# @router.patch("/{user_id}", response_model=UserResponseSchema)
# async def update_user(
#     user_id: int,
#     user_update: UserUpdateSchema,
#     db: AsyncSession = Depends(get_async_session),
#     current_user: UserModel = Depends(AuthService().get_current_user),
# ):
#     """
#     Updates an existing user.
#     """
#     user_repo = UserRepository(db)
#     # Додаткова перевірка, щоб користувач міг оновлювати лише свій профіль
#     if user_id != current_user.id:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user.")

#     updated_user = await user_repo.update_user(user_id, user_update)
#     if updated_user is None:
#         raise HTTPException(status_code=404, detail="User not found.")
#     return updated_user


# @router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_user(
#     user_id: int,
#     db: AsyncSession = Depends(get_async_session),
#     current_user: UserModel = Depends(AuthService().get_current_user),
# ):
#     """
#     Deletes a user.
#     """
#     user_repo = UserRepository(db)
#     # Додаткова перевірка, щоб користувач міг видаляти лише свій профіль
#     if user_id != current_user.id:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user.")

#     deleted = await user_repo.delete_user(user_id)
#     if not deleted:
#         raise HTTPException(status_code=404, detail="User not found.")
#     return None