from aiogram import Router, F
from aiogram.types import Message
from loguru import logger
from sqlalchemy import select
from src.core.models import User
from src.core.clients.databases.postgres import pg
from src.bot.keyboards.start.start import get_welcome_keyboard

start_router = Router()


@start_router.message(F.text == "/start")
async def cmd_start(message: Message):
    logger.info("/start from %s", message.from_user.id)

    async with pg.session_maker() as session:
        stmt = select(User).where(User.telegram_id == str(message.from_user.id))
        result = await session.execute(stmt)
        user: User | None = result.scalar_one_or_none()

        is_new = False
        if not user:
            user = User(
                telegram_id=str(message.from_user.id),
                username=message.from_user.username,
            )
            session.add(user)
            is_new = True

        await session.commit()

    if is_new:
        await message.answer(
            "Привет! Я сохранил твой профиль ✅",
            reply_markup=get_welcome_keyboard(),
        )
    else:
        await message.answer(
            "С возвращением!",
            reply_markup=get_welcome_keyboard(),
        )
