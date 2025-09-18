from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from src.database.db import get_async_session
from src.schemas.contacts import (
    ContactBase,
    ContactCreate,
    ContactRespons,
    ContactUpdate,
)
from src.schemas.users import (
    UserBaseSchema,
    UserCreateSchema,
    UserLoginSchema,
    UserResponseSchema,
    UserUpdateSchema,
)
from src.repository.contacts import ContactRepository
from src.services.auth import AuthService
from src.database.models import UserModel

from src.repository.users import UserRepository
from src.services.auth import AuthService
from src.database.models import UserModel


# Створюємо екземпляр роутера
print("Router for contacts is being defined.")
router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("/", response_model=ContactRespons, status_code=status.HTTP_201_CREATED)
async def create_new_contact(
    contact_in: ContactCreate,
    current_user: UserModel = Depends(AuthService.get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Creates a new contact.

    This endpoint creates a new contact in the database using the provided data.
    """
    contact_repo = ContactRepository(db)
    db_contact = await contact_repo.create_contact(contact_in, current_user.id)
    return db_contact


@router.get("/", response_model=List[ContactRespons])
async def get_all_contacts(
    db: AsyncSession = Depends(get_async_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """
    Retrieves all contacts with pagination.

    This endpoint returns a paginated list of all contacts stored in the database.
    - **skip**: The number of records to skip (for pagination).
    - **limit**: The maximum number of records to return.
    """
    contact_repo = ContactRepository(db)
    contacts = await contact_repo.get_contacts(skip=skip, limit=limit)
    return contacts


@router.get("/{contact_id}", response_model=ContactRespons)
async def read_contact(contact_id: int, db: AsyncSession = Depends(get_async_session)):
    """
    Retrieves a single contact by its ID.

    This endpoint returns a single contact by its unique ID.
    - **contact_id**: The unique identifier of the contact.

    Raises:
        HTTPException: If the contact with the specified ID is not found.
    """
    contact_repo = ContactRepository(db)
    db_contact = await contact_repo.get_contact_by_id(contact_id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found.")
    return db_contact


@router.patch("/{contact_id}", response_model=ContactRespons)
async def update_existing_contact(
    contact_id: int,
    contact_update: ContactUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Updates an existing contact.

    This endpoint performs a partial update on an existing contact using its ID.
    - **contact_id**: The ID of the contact to update.
    - **contact_update**: The fields to update.

    Raises:
        HTTPException: If the contact with the specified ID is not found.
    """
    contact_repo = ContactRepository(db)
    updated_contact = await contact_repo.update_contact(
        contact_id, contact_update
    )
    if updated_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found.")
    return updated_contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_contact(
    contact_id: int, db: AsyncSession = Depends(get_async_session)
):
    """
    Deletes a contact.

    This endpoint deletes a contact from the database using its ID.
    - **contact_id**: The ID of the contact to delete.

    Raises:
        HTTPException: If the contact with the specified ID is not found.
    """
    contact_repo = ContactRepository(db)
    deleted = await contact_repo.delete_contact(contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found.")
    return None


@router.post("/search", response_model=List[ContactRespons])
async def get_search_contacts(
    query: dict, db: AsyncSession = Depends(get_async_session)
):
    """
    Universal search for contacts.

    This endpoint performs a search based on one or more parameters provided in the request body.
    - A single key will perform a search on one parameter.
    - Multiple keys will perform a search on multiple parameters.
    """
    contact_repo = ContactRepository(db)
    contacts = await contact_repo.search_contacts_repo(query)

    if not contacts:
        raise HTTPException(
            status_code=404, detail="No contacts found for the given criteria."
        )

    return contacts


@router.get("/upcoming_birthdays/", response_model=List[ContactRespons])
async def get_coming_birthday_contacts(db: AsyncSession = Depends(get_async_session)):
    """
    Retrieves contacts with upcoming birthdays in the next 7 days.

    This endpoint returns a list of contacts whose birthdays fall within the next 7 days,
    including the current date. It correctly handles month and year transitions.
    """
    contact_repo = ContactRepository(db)
    return await contact_repo.get_contacts_upcoming_birthdays()
