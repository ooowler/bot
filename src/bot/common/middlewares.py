from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
import time
from src.core.clients.metrics import metrics
from src.bot.features.exchange.states import ExchangeStates


class ExchangeCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        state: FSMContext = data["state"]
        if await state.get_state() != ExchangeStates.selected:
            await event.answer("Сначала выберите биржу командой /select_exchange")
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
