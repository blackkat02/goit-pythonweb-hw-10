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
    """
    Retrieves the current authenticated user's profile.

    This endpoint requires a valid access token. It is used to get details
    about the logged-in user.

    Args:
        current_user (UserModel): The user model object obtained from the
                                  `get_current_user` dependency.

    Returns:
        UserResponseSchema: The user object containing their profile data.
    """
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

    This endpoint creates a new user account with a hashed password and schedules a
    background task to send an email verification link.

    Args:
        body (UserCreateSchema): The user data for registration.
        background_tasks (BackgroundTasks): Dependency to run tasks in the background.
        request (Request): The incoming request object.
        db (AsyncSession): The database session dependency.
        auth_service (AuthService): The authentication service dependency.

    Returns:
        UserResponseSchema: The newly created user object.

    Raises:
        HTTPException: If an account with the provided email already exists.
    """
    user_repo = UserRepository(db)
    
    # Check if user already exists
    user = await user_repo.get_user_by_email(body.email)
    if user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
        )

    # Hash the password using AuthService
    hashed_password = auth_service.hash_password(body.password)
    
    # Create the user in the database
    new_user = await user_repo.create_user(body, hashed_password)

    verification_token = auth_service.create_jwt_token({"email": body.email}, scope="verification_token")

    # Add logging to see the token
    logger.info(f"Generated verification token for {body.email}: {verification_token}")
    
    # Create the token and pass it to a background task
    background_tasks.add_task(
        auth_service.send_confirmation_email, 
        new_user.email, 
        new_user.username, 
        str(request.base_url)
    )
    
    return new_user

@router.post("/login")
async def login(body: OAuth2PasswordRequestForm = Depends(), db=Depends(get_async_session)):
    """
    Authenticates a user and provides an access token.

    This endpoint validates the user's credentials and, if successful, returns a JWT
    access token for subsequent authenticated requests.

    Args:
        body (OAuth2PasswordRequestForm): Form data containing the username and password.
        db (AsyncSession): The database session dependency.

    Returns:
        dict: A dictionary containing the access token.

    Raises:
        HTTPException: If the email is invalid, the email is not confirmed, or the password is wrong.
    """
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
        # The payload key is changed to "email" for compatibility with `get_current_user`
        payload={"email": user.email}
    )
    return {"access_token": access_token}


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db=Depends(get_async_session)):
    """
    Confirms a user's email address using a verification token.

    This endpoint verifies the token received via email and updates the user's
    'confirmed' status in the database.

    Args:
        token (str): The verification token from the email link.
        db (AsyncSession): The database session dependency.

    Returns:
        dict: A message confirming the email confirmation status.

    Raises:
        HTTPException: If the token is invalid or the user is not found.
    """
    user_repo = UserRepository(db)
    
    # Create an instance of AuthService
    auth_service = AuthService()

    email = await auth_service.decode_verification_token(token)
    
    # Use the user_repo instance to get the user
    user = await user_repo.get_user_by_email(email)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}

    # Use the user_repo instance to update the user
    await user_repo.change_confirmed_email(email)
    
    return {"message": "Email confirmed"}


@router.post("/request_email")
async def request_email(
    body: RequestEmailSchema,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Requests a new confirmation email for an unconfirmed user.

    This endpoint checks if the user exists and is not yet confirmed. If so, it
    schedules a new confirmation email to be sent.

    Args:
        body (RequestEmailSchema): The schema containing the user's email.
        background_tasks (BackgroundTasks): Dependency to run tasks in the background.
        request (Request): The incoming request object.
        db (AsyncSession): The database session dependency.
        auth_service (AuthService): The authentication service dependency.

    Returns:
        dict: A message confirming that a new email has been sent.

    Raises:
        HTTPException: If the user is not found or their email is already confirmed.
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