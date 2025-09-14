from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import ContactsModel
from src.schemas.schemas import ContactBase, ContactCreate, ContactUpdate, Contact
from typing import List, Optional
from sqlalchemy import select, extract, or_, and_


async def create_contact(db: AsyncSession, contact: ContactCreate) -> ContactsModel:
    """
    Creates a new contact in the database.

    Args:
        db (AsyncSession): The database session.
        contact (ContactCreate): The Pydantic schema with contact data.

    Returns:
        ContactsModel: The newly created contact object from the database.
    """
    db_contact = ContactsModel(
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone_number=contact.phone_number,
        birthday=contact.birthday,
        other_info=contact.other_info
    )
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact
    

async def get_contacts(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ContactsModel]:
    """
    Retrieves a list of all contacts from the database.

    Args:
        db (AsyncSession): The database session.
        skip (int): The number of records to skip (for pagination).
        limit (int): The maximum number of records to return.

    Returns:
        List[ContactsModel]: A list of contact objects.
    """
    stmt = select(ContactsModel).offset(skip).limit(limit)
    result = await db.execute(stmt)
    contacts = result.scalars().all()
    return contacts


async def get_contact_by_id(db: AsyncSession, contact_id: int) -> Optional[ContactsModel]:
    """
    Retrieves a single contact by its ID.

    Args:
        db (AsyncSession): The database session.
        contact_id (int): The ID of the contact to retrieve.

    Returns:
        Optional[ContactsModel]: The contact object or None if not found.
    """
    # Query the database to get a contact by its ID.
    return await db.get(ContactsModel, contact_id)


async def update_contact(db: AsyncSession, contact_id: int, body: ContactUpdate) -> Optional[ContactsModel]:
    """
    Updates an existing contact in the database.

    Args:
        db (AsyncSession): The database session.
        contact_id (int): The ID of the contact to update.
        body (ContactUpdate): Pydantic schema with the data for the update.

    Returns:
        Optional[ContactsModel]: The updated contact object or None if not found.
    """
    contact = await db.get(ContactsModel, contact_id)
    if contact:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(contact, field, value)
        await db.commit()
        await db.refresh(contact)
    return contact


async def delete_contact(db: AsyncSession, contact_id: int) -> Optional[ContactsModel]:
    """
    Deletes a contact by its ID.

    Args:
        db (AsyncSession): The database session.
        contact_id (int): The ID of the contact to delete.

    Returns:
        Optional[ContactsModel]: The deleted contact object or None if not found.
    """
    db_contact = await db.get(ContactsModel, contact_id)

    if db_contact:
        await db.delete(db_contact)
        await db.commit()
        return db_contact 

    return None


async def search_contacts_repo(db: AsyncSession, filters: dict[str, str]) -> List[ContactsModel]:
    """
    Performs a universal search for contacts based on one or more parameters.

    Args:
        db (AsyncSession): The database session.
        filters (dict[str, str]): A dictionary of key-value pairs for filtering.

    Returns:
        List[ContactsModel]: A list of contacts that match the search criteria.
    """
    if not filters:
        return []

    conditions = []
    for field, value in filters.items():
        model_field = getattr(ContactsModel, field, None)
        if model_field is not None:
            conditions.append(model_field.ilike(f"%{value}%"))

    if not conditions:
        return []

    stmt = select(ContactsModel).filter(and_(*conditions))
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_contacts_upcoming_birthdays(db: AsyncSession, days: int=7) -> List[ContactsModel]:
    """
    Retrieves contacts with birthdays in the next 7 days, including today.

    Handles month and year transitions correctly.

    Args:
        db (AsyncSession): The database session.

    Returns:
        List[ContactsModel]: A list of contacts with upcoming birthdays.
    """
    today = date.today()
    future_date = today + timedelta(days=days)

    if today.month == future_date.month:
        # Case 1: The entire 7-day period is within a single month.
        stmt = (
            select(ContactsModel)
            .where(
                and_(
                    extract("month", ContactsModel.birthday) == today.month,
                    extract("day", ContactsModel.birthday).between(today.day, future_date.day),
                )
            )
        )
    else:
        # Case 2: The 7-day period transitions between two months (e.g., Dec to Jan).
        # We need to build a query that checks for birthdays in the rest of the current month
        # and for birthdays at the beginning of the next month.
        stmt = (
            select(ContactsModel)
            .where(
                or_(
                    # Days from the current date to the end of the current month.
                    and_(
                        extract("month", ContactsModel.birthday) == today.month,
                        extract("day", ContactsModel.birthday) >= today.day,
                    ),
                    # Days from the start of the next month to the future_date.
                    and_(
                        extract("month", ContactsModel.birthday) == future_date.month,
                        extract("day", ContactsModel.birthday) <= future_date.day,
                    ),
                )
            )
        )

    result = await db.execute(stmt)
    return result.scalars().all()