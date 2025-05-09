from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
import time
from src.core.clients.metrics import metrics
from src.bot.features.exchange.states import ExchangeStates
from aiogram.types import Message, CallbackQuery


class AccessMiddleware(BaseMiddleware):
    def __init__(self, allowed_user_ids: list[int]):
        self.allowed_user_id = allowed_user_ids
        super().__init__()

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user is None and hasattr(event, "message"):
            user = event.message.from_user
        if user is None and hasattr(event, "callback_query"):
            user = event.callback_query.from_user

        if user is None or user.id not in self.allowed_user_id:
            return

        return await handler(event, data)


class MetricsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        import time

        start = time.perf_counter()
        result = await handler(event, data)
        elapsed = time.perf_counter() - start

        handler_obj = data.get("handler")
        callback = getattr(handler_obj, "callback", handler_obj)
        name = f"handler_{callback.__name__}"

        metrics.record(name, elapsed)

        return result
