from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import ContactsModel
from src.schemas.contacts import ContactBase, ContactCreate, ContactUpdate
from typing import List, Optional
from sqlalchemy import select, extract, or_, and_


class ContactRepository:
    def __init__(self, db: AsyncSession):
        """
        Initializes the repository with a database session.
        """
        self.db = db

    async def create_contact(self, contact: ContactCreate, user_id: int) -> ContactsModel:
        """
        Creates a new contact in the database.
        """
        db_contact = ContactsModel(
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=contact.email,
            phone_number=contact.phone_number,
            birthday=contact.birthday,
            other_info=contact.other_info,
            user_id=user_id
        )
        self.db.add(db_contact)
        await self.db.commit()
        await self.db.refresh(db_contact)
        return db_contact

    async def get_contacts(self, user_id: int, skip: int = 0, limit: int = 100) -> List[ContactsModel]:
        """
        Retrieves a list of all contacts from the database.
        """
        stmt = select(ContactsModel).where(ContactsModel.user_id == user_id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        contacts = result.scalars().all()
        return contacts

    async def get_contact_by_id(self, contact_id: int, user_id: int) -> Optional[ContactsModel]:
        """
        Retrieves a single contact by its ID.
        """
        stmt = select(ContactsModel).where(and_(ContactsModel.id == contact_id, ContactsModel.user_id == user_id))
        result = await self.db.execute(stmt)
        contact = result.scalars().first()
        return contact

    async def update_contact(self, contact_id: int, body: ContactUpdate, user_id: int) -> Optional[ContactsModel]:
        """
        Updates an existing contact in the database.
        """
        contact = await self.db.get(ContactsModel, contact_id)
        if contact and contact.user_id == user_id:
            for field, value in body.model_dump(exclude_unset=True).items():
                setattr(contact, field, value)
            await self.db.commit()
            await self.db.refresh(contact)
            return contact
        return None

    async def delete_contact(self, contact_id: int, user_id: int) -> Optional[ContactsModel]:
        """
        Deletes a contact by its ID.
        """
        db_contact = await self.db.get(ContactsModel, contact_id)
        if db_contact and db_contact.user_id == user_id:
            await self.db.delete(db_contact)
            await self.db.commit()
            return db_contact
        return None

    async def search_contacts_repo(self, filters: dict[str, str], user_id: int) -> List[ContactsModel]:
        """
        Performs a universal search for contacts based on one or more parameters.
        """
        if not filters:
            return []

        conditions = [ContactsModel.user_id == user_id]
        for field, value in filters.items():
            model_field = getattr(ContactsModel, field, None)
            if model_field is not None:
                conditions.append(model_field.ilike(f"%{value}%"))

        if not conditions:
            return []

        stmt = select(ContactsModel).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_contacts_upcoming_birthdays(self, user_id: int, days: int = 7) -> List[ContactsModel]:
        """
        Retrieves contacts with birthdays in the next specified number of days, including today.
        Handles month and year transitions correctly.
        """
        today = date.today()
        future_date = today + timedelta(days=days)

        if today.month == future_date.month:
            # Case 1: The entire period is within a single month.
            stmt = (
                select(ContactsModel)
                .where(
                    and_(
                        extract("month", ContactsModel.birthday) == today.month,
                        extract("day", ContactsModel.birthday).between(today.day, future_date.day),
                        ContactsModel.user_id == user_id,
                    )
                )
            )
        else:
            # Case 2: The period transitions between two months (e.g., Dec to Jan).
            stmt = (
                select(ContactsModel)
                .where(
                    and_(
                        or_(
                            and_(
                                extract("month", ContactsModel.birthday) == today.month,
                                extract("day", ContactsModel.birthday) >= today.day,
                            ),
                            and_(
                                extract("month", ContactsModel.birthday) == future_date.month,
                                extract("day", ContactsModel.birthday) <= future_date.day,
                            ),
                        ),
                        ContactsModel.user_id == user_id,
                    )
                )
            )

        result = await self.db.execute(stmt)
        return result.scalars().all()



# from datetime import date, timedelta
# from sqlalchemy.ext.asyncio import AsyncSession
# from src.database.models import ContactsModel
# from src.schemas.contacts import ContactBase, ContactCreate, ContactUpdate
# from typing import List, Optional
# from sqlalchemy import select, extract, or_, and_


# class ContactRepository:
#     def __init__(self, db: AsyncSession):
#         """
#         Initializes the repository with a database session.
#         """
#         self.db = db

#     async def create_contact(
#         self, contact: ContactCreate, user_id: int
#     ) -> ContactsModel:
#         """
#         Creates a new contact in the database.
#         """
#         db_contact = ContactsModel(
#             first_name=contact.first_name,
#             last_name=contact.last_name,
#             email=contact.email,
#             phone_number=contact.phone_number,
#             birthday=contact.birthday,
#             other_info=contact.other_info,
#             user_id=user_id
#         )
#         self.db.add(db_contact)
#         await self.db.commit()
#         await self.db.refresh(db_contact)
#         return db_contact

#     async def get_contacts(self, skip: int = 0, limit: int = 100) -> List[ContactsModel]:
#         """
#         Retrieves a list of all contacts from the database.
#         """
#         stmt = select(ContactsModel).offset(skip).limit(limit)
#         result = await self.db.execute(stmt)
#         contacts = result.scalars().all()
#         return contacts

#     async def get_contact_by_id(self, contact_id: int) -> Optional[ContactsModel]:
#         """
#         Retrieves a single contact by its ID.
#         """
#         return await self.db.get(ContactsModel, contact_id)

#     async def update_contact(self, contact_id: int, body: ContactUpdate) -> Optional[ContactsModel]:
#         """
#         Updates an existing contact in the database.
#         """
#         contact = await self.db.get(ContactsModel, contact_id)
#         if contact:
#             for field, value in body.model_dump(exclude_unset=True).items():
#                 setattr(contact, field, value)
#             await self.db.commit()
#             await self.db.refresh(contact)
#         return contact

#     async def delete_contact(self, contact_id: int) -> Optional[ContactsModel]:
#         """
#         Deletes a contact by its ID.
#         """
#         db_contact = await self.db.get(ContactsModel, contact_id)
#         if db_contact:
#             await self.db.delete(db_contact)
#             await self.db.commit()
#             return db_contact
#         return None

#     async def search_contacts_repo(self, filters: dict[str, str]) -> List[ContactsModel]:
#         """
#         Performs a universal search for contacts based on one or more parameters.
#         """
#         if not filters:
#             return []

#         conditions = []
#         for field, value in filters.items():
#             model_field = getattr(ContactsModel, field, None)
#             if model_field is not None:
#                 conditions.append(model_field.ilike(f"%{value}%"))

#         if not conditions:
#             return []

#         stmt = select(ContactsModel).filter(and_(*conditions))
#         result = await self.db.execute(stmt)
#         return result.scalars().all()

#     async def get_contacts_upcoming_birthdays(self, days: int = 7) -> List[ContactsModel]:
#         """
#         Retrieves contacts with birthdays in the next specified number of days, including today.

#         Handles month and year transitions correctly.
#         """
#         today = date.today()
#         future_date = today + timedelta(days=days)

#         if today.month == future_date.month:
#             # Case 1: The entire period is within a single month.
#             stmt = (
#                 select(ContactsModel)
#                 .where(
#                     and_(
#                         extract("month", ContactsModel.birthday) == today.month,
#                         extract("day", ContactsModel.birthday).between(today.day, future_date.day),
#                     )
#                 )
#             )
#         else:
#             # Case 2: The period transitions between two months (e.g., Dec to Jan).
#             stmt = (
#                 select(ContactsModel)
#                 .where(
#                     or_(
#                         # Days from the current date to the end of the current month.
#                         and_(
#                             extract("month", ContactsModel.birthday) == today.month,
#                             extract("day", ContactsModel.birthday) >= today.day,
#                         ),
#                         # Days from the start of the next month to the future_date.
#                         and_(
#                             extract("month", ContactsModel.birthday) == future_date.month,
#                             extract("day", ContactsModel.birthday) <= future_date.day,
#                         ),
#                     ),
#                 )
#             )

#         result = await self.db.execute(stmt)
#         return result.scalars().all()
