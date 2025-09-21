from fastapi import Depends, APIRouter, HTTPException, status, BackgroundTasks, Request
from fastapi_limiter.depends import RateLimiter
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db import get_async_session
from src.repository.users import UserRepository
from src.services.auth import AuthService, get_current_user
from src.schemas.users import (
    UserBaseSchema,
    UserCreateSchema,
    UserLoginSchema,
    UserResponseSchema,
    UserUpdateSchema,
)
from src.schemas.auth import RequestEmailSchema
from src.services.auth import AuthService, get_auth_service
from src.database.models import UserModel
from libgravatar import Gravatar

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get(
    "/me",
    response_model=UserResponseSchema,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))]
)
def read_current_user(current_user: UserModel = Depends(get_current_user)):
    return current_user

@router.post("/signup", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
async def signup(
    body: UserCreateSchema,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    auth_service: AuthService = Depends(get_auth_service) # Залежність для AuthService
):
    """
    Registers a new user and sends a confirmation email.
    """
    user_repo = UserRepository(db)
    
    # Перевіряємо, чи існує користувач
    user = await user_repo.get_user_by_email(body.email)
    if user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
        )

    # Хешуємо пароль за допомогою AuthService
    hashed_password = auth_service.hash_password(body.password)
    
    # Створюємо користувача в базі даних
    new_user = await user_repo.create_user(body, hashed_password)

    verification_token = auth_service.create_jwt_token({"email": body.email}, scope="verification_token")

    # Додаємо логування, щоб бачити токен
    logger.info(f"Generated verification token for {body.email}: {verification_token}")
    
    # Створюємо токен і передаємо його у фонову задачу
    background_tasks.add_task(
        auth_service.send_confirmation_email, 
        new_user.email, 
        new_user.username, 
        str(request.base_url)
    )
    
    return new_user

@router.post("/login")
async def login(body: OAuth2PasswordRequestForm = Depends(), db=Depends(get_async_session)):
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_username(body.username)
    auth_service = AuthService()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email"
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email is not verified"
        )
    if not auth_service.verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )

    access_token = auth_service.create_jwt_token(
        # Ключ payload змінено на "email" для сумісності з `get_current_user`
        payload={"email": user.email}
    )
    return {"access_token": access_token}


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db=Depends(get_async_session)):
    user_repo = UserRepository(db)
    
    # 1. Створюємо екземпляр AuthService
    auth_service = AuthService()

    email = await auth_service.decode_verification_token(token)
    
    # 2. Використовуємо екземпляр user_repo для отримання користувача
    user = await user_repo.get_user_by_email(email)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}

    # 3. Використовуємо екземпляр user_repo для оновлення користувача
    await user_repo.change_confirmed_email(email)
    
    return {"message": "Email confirmed"}


import logging
import asyncio

logger = logging.getLogger(__name__)


@router.post("/request_email")
async def request_email(
    body: RequestEmailSchema,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Requests a new confirmation email for a user.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_email(body.email)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    if user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Email is already confirmed"
        )
    
    # Schedule sending the new confirmation email
    background_tasks.add_task(
        auth_service.send_confirmation_email,
        email=user.email,
        username=user.username,
        host=str(request.base_url)
    )
    
    return {"message": "New confirmation email sent"}



# @router.get(
#     "/me", response_model=User, description="No more than 10 requests per minute"
# )
# @limiter.limit("10/minute")
# async def me(request: Request, user: User = Depends(get_current_user)):
#     return user


# @router.patch("/avatar", response_model=User)
# async def update_avatar_user(
#     file: UploadFile = File(),
#     user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     avatar_url = UploadFileService(
#         settings.CLD_NAME, settings.CLD_API_KEY, settings.CLD_API_SECRET
#     ).upload_file(file, user.username)

#     user_service = UserService(db)
#     user = await user_service.update_avatar_url(user.email, avatar_url)

#     return user