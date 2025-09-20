import cloudinary
import cloudinary.uploader
from src.settings import settings
from fastapi import Depends

class CloudinaryService:
    """ Сервіс для завантаження файлів на Cloudinary. """

    def __init__(self):
        cloudinary.config(
            cloud_name=settings.cloudinary_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
        )

    def upload_image(self, file_path: str, public_id: str):
        result = cloudinary.uploader.upload(file_path, public_id=public_id, overwrite=True)
        return result['secure_url']

# Цей об'єкт буде створений лише коли буде викликана залежність.
def get_cloudinary_service():
    return CloudinaryService()