from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from loguru import logger

from src.bot.keyboards.account import get_welcome_keyboard

start_router = Router()


@start_router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    logger.info("Получена команда /start")
    await message.answer("Привет!", reply_markup=get_welcome_keyboard())
