from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    WHATSAPP_TOKEN: str
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_VERIFY_TOKEN: str
    WHATSAPP_API_VERSION: str
    DATABASE_URL: str
    ZOHO_CLIENT_ID: str
    ZOHO_CLIENT_SECRET: str
    ZOHO_REFRESH_TOKEN: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
