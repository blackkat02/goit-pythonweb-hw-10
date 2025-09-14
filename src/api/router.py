from fastapi import APIRouter
from src.api.v1.endpoints import contacts, utils

# Головний роутер для версіонування API
router = APIRouter()

# Включаємо роутер для контактів з префіксом версії
router.include_router(contacts.router, prefix="/v1")

# Включаємо утилітарний роутер без префікса версії
router.include_router(utils.router)