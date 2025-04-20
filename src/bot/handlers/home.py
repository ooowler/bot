from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from src.bot.keyboards.start.start import get_welcome_keyboard

home_router = Router()


@home_router.message(F.text == "/home")
async def cmd_home(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Главное меню", reply_markup=get_welcome_keyboard())
