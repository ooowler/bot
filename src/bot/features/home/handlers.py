from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.features.home.keyboards import main_menu_keyboard
from src.bot.triggers import Commands
from src.core.repositories.user import ensure_user

router = Router()


@router.message(Command(Commands.Home.START))
async def cmd_start(msg: Message, state: FSMContext) -> None:
    await ensure_user(msg.from_user.id, msg.from_user.username)
    await msg.answer("Добро пожаловать!", reply_markup=main_menu_keyboard())


@router.message(Command(Commands.Home.REFRESH))
async def cmd_refresh(msg: Message, state: FSMContext) -> None:
    await state.clear()
    await msg.answer("Состояния очищены!", reply_markup=main_menu_keyboard())


@router.message(Command(Commands.Home.HELP))
async def cmd_help(msg: Message) -> None:
    await msg.answer(
        "Доступные команды:\n"
        "/start – главное меню\n"
        "/refresh – сбросить состояния\n"
        "/help – справка"
    )
