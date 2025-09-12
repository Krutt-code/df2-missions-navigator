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

    # Сервер
    my_server: Optional[bool] = False
    ip_server: Optional[str] = None

    # Playwright
    headless: Optional[bool] = True

    # Многопроцессность
    num_workers: Optional[int] = 1
    num_processes: Optional[int] = 1
    new_task_sleep: Optional[int] = 5

    # Логирование
    log_level: Optional[str] = "INFO"

    # Шифрование
    encryption_key: Optional[str] = None
    encryption_iv: Optional[str] = None

    # Настройки пула БД (на процесс)
    db_pool_size: Optional[int] = 2
    db_max_overflow: Optional[int] = 0
    db_pool_timeout: Optional[int] = 25

    # Централизация сетевых задержек/лимитов (на процесс)
    max_concurrent_navigations: Optional[int] = 2
    max_concurrent_contexts: Optional[int] = 2
    max_concurrent_pages: Optional[int] = 4

    # Дополнительные лимиты для экстремальной нагрузки
    max_concurrent_clicks: Optional[int] = 10  # Лимит одновременных кликов
    max_concurrent_scrolls: Optional[int] = 5  # Лимит одновременных скроллов
    global_rate_limit_delay: Optional[float] = (
        0.1  # Глобальная задержка между операциями
    )

    # Таймауты Playwright (мс)
    navigation_timeout_ms: Optional[int] = 45000
    selector_timeout_ms: Optional[int] = 10000

    # Ретрраи и бэкофф
    max_retries_navigation: Optional[int] = 2
    retry_backoff_base: Optional[float] = 1.5

    # Настройки safe_click для высокой нагрузки
    safe_click_max_retries: Optional[int] = 5
    safe_click_timeout_ms: Optional[int] = 8000
    safe_click_retry_delay: Optional[float] = 0.5

    # Ограничения работы скрипта
    deny_authorization: Optional[bool] = False
    deny_mobile: Optional[bool] = False
    deny_yandex_search: Optional[bool] = False

    # Сетевые оптимизации
    block_resources: Optional[bool] = True

    # Watchdog/перезапуски/лимиты логов
    memory_watchdog_interval_sec: Optional[int] = 60
    browser_restart_contexts_threshold: Optional[int] = 0  # 0 — выключено
    memory_soft_restart_rss_mb: Optional[int] = 0  # 0 — выключено
    max_log_lines_per_task: Optional[int] = 5000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def actual_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        elif all([self.db_user, self.db_password, self.db_host, self.db_name]):
            encoded_user = quote_plus(self.db_user)
            encoded_password = quote_plus(self.db_password)
            return f"mysql+asyncmy://{encoded_user}:{encoded_password}@{self.db_host}/{self.db_name}"
        else:
            raise ValueError(
                "DATABASE_URL or all of DB_USER, DB_PASSWORD, DB_HOST, DB_NAME must be set."
            )


SETTINGS = Settings()
