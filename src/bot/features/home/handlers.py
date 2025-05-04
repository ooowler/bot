from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from src.bot.triggers import Commands
from src.bot.features.home.keyboards import main_menu_keyboard

router = Router()


@router.message(Command(Commands.Home.START))
async def cmd_start(msg: Message, state: FSMContext):
    await msg.answer("Добро пожаловать!", reply_markup=main_menu_keyboard())


@router.message(Command(Commands.Home.REFRESH))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Состояния очищены!", reply_markup=main_menu_keyboard())


@router.message(Command(Commands.Home.HELP))
async def cmd_help(msg: Message):
    await msg.answer(
        "Доступные команды:\n" "/start – показать главное меню\n" "/help – справка\n"
    )
