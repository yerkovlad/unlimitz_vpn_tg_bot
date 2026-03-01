import asyncio
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 0.5):
        self.rate = rate
        self._users: Dict[int, asyncio.Task] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id

        if user_id in self._users:
            await event.answer("⚠️ Не так быстро!")
            return

        self._users[user_id] = asyncio.create_task(self._clear(user_id))
        return await handler(event, data)

    async def _clear(self, user_id: int):
        await asyncio.sleep(self.rate)
        self._users.pop(user_id, None)