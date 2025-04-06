from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger

from src.bot.callbacks import CallbackData
from src.bot.keyboards.account import get_exchanges_kb
from src.bot.fsm.account import AddAccountStates

account_router = Router()


@account_router.callback_query(F.data == CallbackData.ADD_ACCOUNT)
async def on_add_account(callback: CallbackQuery, state: FSMContext):
    logger.info("Пользователь нажал 'Добавить аккаунт'")
    await callback.message.edit_text("Выберите биржу:", reply_markup=get_exchanges_kb())


@account_router.callback_query(F.data == CallbackData.EXCHANGE_BACKPACK)
async def on_exchange_backpack(callback: CallbackQuery, state: FSMContext):
    logger.info("Пользователь выбрал Backpack")
    await state.set_state(AddAccountStates.enter_pubkey)
    await callback.message.edit_text("Введите публичный ключ:")


@account_router.message(AddAccountStates.enter_pubkey)
async def get_pubkey(message: Message, state: FSMContext):
    pubkey = message.text.strip()
    await state.update_data(pubkey=pubkey)
    await state.set_state(AddAccountStates.enter_privkey)
    await message.answer("Ок, теперь пришли приватный ключ:")


@account_router.message(AddAccountStates.enter_privkey)
async def get_privkey(message: Message, state: FSMContext):
    privkey = message.text.strip()
    data = await state.get_data()
    pubkey = data["pubkey"]

    # БД

    await message.answer(f"Аккаунт добавлен!\nPublic: {pubkey}\nPrivate: {privkey}")
    await state.clear()
