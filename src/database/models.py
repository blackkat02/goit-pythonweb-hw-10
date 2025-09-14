from sqlalchemy import Column, Integer, String, DATE, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import date


class Base(DeclarativeBase):
    pass


class ContactsModel(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), index=True)
    last_name: Mapped[str] = mapped_column(String(50), index=True)
    email: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True)
    birthday: Mapped[date] = mapped_column(DATE, nullable=False, index=True)
    other_info: Mapped[str] = mapped_column(String(250), nullable=True)
