from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import TokenModel, UserModel
from datetime import datetime, timedelta, timezone


class TokenRepository:
    def __init__(self, db: AsyncSession):
        """
        Initializes the repository with a database session.
        """
        self.db = db

    async def create_token(
        self, user: UserModel, token_type: str, expires_delta: timedelta
    ) -> TokenModel:
        """
        Creates a new token for a user and stores it in the database.
        
        Args:
            user: The user model instance for whom the token is being created.
            token_type: The type of token (e.g., "refresh").
            expires_delta: The timedelta for the token's expiration.
            
        Returns:
            The created TokenModel instance.
        """
        expires_at = datetime.now(timezone.utc) + expires_delta
        
        db_token = TokenModel(
            user_id=user.id,
            token_type=token_type,
            expires_at=expires_at
        )
        self.db.add(db_token)
        await self.db.commit()
        await self.db.refresh(db_token)
        return db_token


    async def update_refresh_token(self, user: UserModel, refresh_token: str):
        """
        Updates the refresh token for a user.
        """
        user.refresh_token = refresh_token
        await self.db.commit()

    async def get_user_by_refresh_token(self, refresh_token: str) -> Optional[UserModel]:
        """
        Retrieves a user by their refresh token.
        """
        stmt = select(UserModel).filter(UserModel.refresh_token == refresh_token)
        result = await self.db.execute(stmt)
        return result.scalars().first()