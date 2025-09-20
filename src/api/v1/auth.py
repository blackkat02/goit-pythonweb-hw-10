from fastapi import Depends, APIRouter, HTTPException, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db import get_async_session
from src.repository.users import UserRepository
from src.services.auth import AuthService, auth_service
from src.services.email import send_email
from src.schemas.users import (
    UserBaseSchema,
    UserCreateSchema,
    UserLoginSchema,
    UserResponseSchema,
    UserUpdateSchema,
)
from src.schemas.auth import RequestEmailSchema
from src.services.auth import AuthService, get_auth_service
from libgravatar import Gravatar

router = APIRouter(prefix="/auth", tags=["auth"])


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

# @router.post("/login")
# async def login(body: OAuth2PasswordRequestForm = Depends(), db=Depends(get_async_session)):
#     user_repo = UserRepository(db)
#     user = await user_repo.get_user_by_username(body.username)
#     auth_service = AuthService()
#     if user is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email"
#         )
#     if not user.confirmed:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail="Email is not verified"
#         )
#     if not auth_service.verify_password(body.password, user.hashed_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
#         )

#     access_token = auth_service.create_jwt_token(
#         payload={"user_email": user.email}
#     )
#     return {"access_token": access_token}


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


# @router.post("/request_email")
# async def request_email(
#     body: RequestEmailSchema,
#     background_tasks: BackgroundTasks,
#     request: Request,
#     db: AsyncSession = Depends(get_async_session),
#     auth_service_instance: AuthService = Depends(get_auth_service),
# ):
#     user_repo = UserRepository(db)
#     user = await user_repo.get_user_by_email(body.email)

#     if user:
#         if user.confirmed:
#             return {"message": "Your email is already confirmed"}

#         # Передаємо всі необхідні аргументи в send_email
#         background_tasks.add_task(
#             auth_service_instance.send_email,
#             user.email,
#             user.username,
#             str(request.base_url)
#         )

#     return {"message": "Check your email for confirmation."}



import logging
import asyncio

logger = logging.getLogger(__name__)

@router.post("/signup", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
async def signup(
    body: UserCreateSchema,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    user_repo = UserRepository(db)

    hashed_password = auth_service.hash_password(body.password)
    # ... валідації, створення користувача ...
    new_user = await user_repo.create_user(body, hashed_password)

    # Лог перед плануванням
    logger.info("Scheduling confirmation email for user %s (%s)", new_user.username, new_user.email)

    # ВАРІАНТ A: асинхронна функція — обгорнути coroutine у task
    coro = auth_service.send_confirmation_email(email=new_user.email, username=new_user.username, host=str(request.base_url))
    background_tasks.add_task(asyncio.create_task, coro)
    logger.debug("BackgroundTasks: added asyncio.create_task for send_confirmation_email")

    return new_user


@router.post("/request_email")
async def request_email(
    body: RequestEmailSchema,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_email(body.email)
    
    if user:
        if user.confirmed:
            return {"message": "Your email is already confirmed"}
            
        background_tasks.add_task(
            auth_service.send_confirmation_email,
            email=user.email,
            username=user.username,
            host=str(request.base_url)
        )
    
    await send_email(
      email=user_repo.email,
      username=user_repo.username,
      host="http://localhost:8080"
    )
    return {"message": "Confirmation email sent"}