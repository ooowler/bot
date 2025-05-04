from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from src.bot.triggers import Commands
from src.bot.features.home.keyboards import main_menu_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import User

router = Router()


async def _ensure_user_exists(message: Message) -> None:
    tg_id = message.from_user.id
    username = message.from_user.username

    async with pg.session_maker() as session:
        exists = await session.scalar(select(User.id).where(User.telegram_id == tg_id))
        if not exists:
            session.add(User(telegram_id=tg_id, username=username))
            await session.commit()


@router.message(Command(Commands.Home.START))
async def cmd_start(msg: Message, state: FSMContext):
    await _ensure_user_exists(msg)
    await msg.answer("Добро пожаловать!", reply_markup=main_menu_keyboard())


@router.message(Command(Commands.Home.REFRESH))
async def cmd_refresh(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Состояния очищены!", reply_markup=main_menu_keyboard())


@router.message(Command(Commands.Home.HELP))
async def cmd_help(msg: Message):
    await msg.answer(
        "Доступные команды:\n"
        "/start – показать главное меню\n"
        "/refresh – сбросить состояния\n"
        "/help – справка"
    )
