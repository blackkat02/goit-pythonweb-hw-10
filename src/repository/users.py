from datetime import datetime
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import UserModel
from src.schemas.users import UserCreateSchema, UserUpdateSchema


class UserRepository:
    def __init__(self, db: AsyncSession):
        """
        Initializes the repository with a database session.
        """
        self.db = db

    async def create_user(self, user_in: UserCreateSchema, hashed_password: str) -> UserModel:
        """
        Creates a new user in the database.
        """
        db_user = UserModel(
            # username=user_in.username,
            # email=user_in.email,
            # hashed_password=hashed_password,
            # avatar=user_in.avatar if user_in.avatar else None,
            # confirmed=user_in.confirmed if user_in.confirmed else False

            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
            avatar=user_in.avatar,
            confirmed=user_in.confirmed
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[UserModel]:
        """
        Retrieves a list of all contacts from the database.
        """
        stmt = select(UserModel).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        return users

    async def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """
        Retrieves a user by their email address.
        """
        stmt = select(UserModel).filter(UserModel.email == email)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_user_by_id(self, user_id: int) -> Optional[UserModel]:
        """
        Retrieves a user by their ID.
        """
        return await self.db.get(UserModel, user_id)

    async def update_user(
        self, user_id: int, user_in: UserUpdateSchema
    ) -> Optional[UserModel]:
        """
        Updates an existing user.
        """
        db_user = await self.db.get(UserModel, user_id)
        if db_user:
            for field, value in user_in.model_dump(exclude_unset=True).items():
                setattr(db_user, field, value)
            await self.db.commit()
            await self.db.refresh(db_user)
        return db_user

    async def delete_user(self, user_id: int) -> Optional[UserModel]:
        """
        Deletes a user by their ID.
        """
        db_user = await self.db.get(UserModel, user_id)
        if db_user:
            await self.db.delete(db_user)
            await self.db.commit()
            return db_user
        return None
