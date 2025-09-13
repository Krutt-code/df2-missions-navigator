from functools import wraps
from typing import Optional

from curl_cffi import AsyncSession, requests


class RequestsManager:
    TOTAL_TIMEOUT = 10
    _session: Optional[AsyncSession] = None

    def __init__(self):
        self._session = self.get_session()

    async def __aenter__(self):
        self._session = self.get_session()
        return self

    async def close(self):
        if self._session is not None:
            await self._session.close()

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    def get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = AsyncSession(
                impersonate="chrome",
                max_clients=20,
            )
        return self._session

    @staticmethod
    def check_response(response: requests.Response) -> bool:
        return response.status_code == 200

    @staticmethod
    def get_session_decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if "session" not in kwargs or kwargs["session"] is None:
                kwargs["session"] = self.get_session()
            return func(self, *args, **kwargs)

        return wrapper

    @get_session_decorator
    async def request(
        self,
        method: str,
        url: str,
        data: Optional[dict] = None,
        session: Optional[AsyncSession] = None,
    ) -> Optional[requests.Response]:
        response = await session.request(
            method, url, data=data, timeout=self.TOTAL_TIMEOUT
        )
        if self.check_response(response):
            return response
        else:
            return None

    @get_session_decorator
    async def get_request(
        self,
        url: str,
        session: Optional[AsyncSession] = None,
    ) -> Optional[requests.Response]:
        return await self.request("GET", url, session=session)

    @get_session_decorator
    async def post_request(
        self,
        url: str,
        data: dict,
        session: Optional[AsyncSession] = None,
    ) -> Optional[requests.Response]:
        return await self.request("POST", url, data, session=session)

    @get_session_decorator
    async def put_request(
        self,
        url: str,
        data: dict,
        session: Optional[AsyncSession] = None,
    ) -> Optional[requests.Response]:
        return await self.request("PUT", url, data, session=session)

    @get_session_decorator
    async def delete_request(
        self,
        url: str,
        session: Optional[AsyncSession] = None,
    ) -> Optional[requests.Response]:
        return await self.request("DELETE", url, session=session)
