from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from src.bot.features.home.keyboards import main_menu_keyboard

router = Router()


@router.message(Command("start"))
async def cmd_start(msg: Message):
    await msg.answer("Добро пожаловать!", reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "Доступные команды:\n"
        "/start – показать главное меню\n"
        "/help – справка\n"
        "/select_exchange – выбрать биржу\n"
        "/accounts – управлять аккаунтами\n"
        "/pools – управлять пулами\n"
        "/proxy – управлять прокси"
    )
