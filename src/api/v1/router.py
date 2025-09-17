from fastapi import APIRouter
from src.api.v1 import contacts, users
from src.api.v1 import utils

# Головний роутер для версіонування API
router = APIRouter()

# Включаємо роутер для контактів з префіксом версії
router.include_router(contacts.router, prefix="/v1")
router.include_router(users.router, prefix="/v1")

# Включаємо утилітарний роутер без префікса версії
router.include_router(utils.router)
