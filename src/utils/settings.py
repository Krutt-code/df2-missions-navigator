from typing import Optional
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # БД
    database_url: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_host: Optional[str] = None
    db_name: Optional[str] = None

    # Логирование
    # log_level: Optional[str] = "INFO"
    log_level: Optional[str] = "DEBUG"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def actual_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        elif all([self.db_user, self.db_password, self.db_host, self.db_name]):
            encoded_user = quote_plus(self.db_user)
            encoded_password = quote_plus(self.db_password)
            # TODO: Решить какую бд использовать
            return f"mysql+asyncmy://{encoded_user}:{encoded_password}@{self.db_host}/{self.db_name}"
        else:
            raise ValueError(
                "DATABASE_URL or all of DB_USER, DB_PASSWORD, DB_HOST, DB_NAME must be set."
            )


SETTINGS = Settings()
