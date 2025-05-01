from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from prometheus_client import Histogram
from src.bot.features.exchange.states import ExchangeStates

handler_latency = Histogram(
    "telegram_handler_latency_seconds",
    "Latency of handler execution",
    ["handler"],
)


class ExchangeCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        state: FSMContext = data["state"]
        if await state.get_state() != ExchangeStates.selected:
            await event.answer("Сначала выберите биржу командой /select_exchange")
            return
        return await handler(event, data)


class MetricsMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        import time, inspect

        start = time.monotonic()
        result = await handler(event, data)
        elapsed = time.monotonic() - start
        handler_latency.labels(handler=data["handler"].callback.__name__).observe(
            elapsed
        )
        return result
