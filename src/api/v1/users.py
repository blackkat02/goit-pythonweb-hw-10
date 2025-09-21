from fastapi import (
    Depends,
    APIRouter,
    HTTPException,
    status,
    BackgroundTasks,
    Request,
    Query,
    UploadFile, 
    File,
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
from src.services.auth import AuthService, get_current_user
from src.database.models import UserModel
from src.services.cloudinary_service import UploadFileService
from src.settings import settings


router = APIRouter(prefix="/users", tags=["users"])


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
    db_user = await user_repo.get_user_by_id(user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return db_user

@router.patch("/avatar", response_model=UserResponseSchema, status_code=status.HTTP_200_OK)
async def update_avatar_user(
    file: UploadFile = File(),
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    avatar_url = UploadFileService(
        settings.CLD_NAME, settings.CLD_API_KEY, settings.CLD_API_SECRET
    ).upload_file(file, user.username)

    user_repo = UserRepository(db)
    user = await user_repo.update_user_avatar(user.id, avatar_url)

    return user


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