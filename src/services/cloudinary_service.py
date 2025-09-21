# import cloudinary
# import cloudinary.uploader
# from pydantic import BaseModel
# import os

# class CloudinaryConfig(BaseModel):
#     cloud_name: str
#     api_key: str
#     api_secret: str

#     class Config:
#         env_file = ".env.docker"
#         env_file_encoding = "utf-8"

# def get_cloudinary_config():
#     return CloudinaryConfig(
#         cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
#         api_key=os.getenv("CLOUDINARY_API_KEY"),
#         api_secret=os.getenv("CLOUDINARY_API_SECRET"),
#     )

# class CloudinaryService:
#     def __init__(self):
#         config = get_cloudinary_config()
#         cloudinary.config(
#             cloud_name=config.cloud_name,
#             api_key=config.api_key,
#             api_secret=config.api_secret,
#             secure=True,
#         )

#     async def upload_avatar(self, file_content):
#         """
#         Завантажує файл аватара на Cloudinary.
#         """
#         try:
#             upload_result = cloudinary.uploader.upload(
#                 file_content,
#                 folder="avatars",  # Назва папки в Cloudinary
#                 overwrite=True,
#                 resource_type="image",
#             )
#             return upload_result.get("url")
#         except Exception as e:
#             raise Exception(f"Помилка завантаження на Cloudinary: {e}")


import cloudinary
import cloudinary.uploader

class UploadFileService:
    def __init__(self, cloud_name, api_key, api_secret):
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

    @staticmethod
    def upload_file(file, username) -> str:
        public_id = f"RestApp/{username}"
        r = cloudinary.uploader.upload(file.file, public_id=public_id, overwrite=True)
        src_url = cloudinary.CloudinaryImage(public_id).build_url(
            width=250, height=250, crop="fill", version=r.get("version")
        )
        return src_url
