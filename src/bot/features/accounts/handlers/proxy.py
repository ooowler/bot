from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from loguru import logger

from src.bot.features.accounts.keyboards import accounts_actions_keyboard
from src.bot.features.accounts.states import AccountsStates
from src.bot.triggers import Texts
from src.core.repositories import accounts as accounts_repo


router = Router()

# Вспомогательная функция для загрузки proxy и fake headers/cookies
from sqlalchemy import select
from src.core.models import Proxy, FakeHeader
from src.core.clients.databases.postgres import pg


@router.message(
    F.text == Texts.Accounts.PROXY_CHECK, StateFilter(AccountsStates.account_selected)
)
async def proxy_check(message: Message, state: FSMContext) -> None:
    """
    Обработчик для проверки текущего proxy через ipinfo.
    """
    data = await state.get_data()
    account_id = data.get("account_id")
    if account_id is None:
        return await message.answer(
            "Сначала выберите аккаунт.",
            reply_markup=accounts_actions_keyboard(),
        )

    client = await accounts_repo.get_backpack_client_by_account_id(account_id)
    if not client:
        return await message.answer(
            "Аккаунт не найден.",
            reply_markup=accounts_actions_keyboard(),
        )
    await message.answer(
        "🕵️ Проверяю текущий proxy…",
        reply_markup=accounts_actions_keyboard(),
    )
    try:
        info = await client.check_proxy()
    except Exception as e:
        logger.warning(f"Proxy check error: {e}")
        return await message.answer(
            "❌ Не удалось проверить proxy.",
            reply_markup=accounts_actions_keyboard(),
        )

    # Формируем ответ по ключевым полям
    ip = info.get("ip")
    city = info.get("city")
    region = info.get("region")
    country = info.get("country")
    org = info.get("org")
    response_time = float(info.get("response_time", 0))

    text = (
        f"✅ Текущий proxy:\n"
        f"IP: {ip}\n"
        f"Location: {city}, {region}, {country}\n"
        f"Provider: {org}\n"
        f"Response time: {round(response_time, 3)} sec"
    )
    await message.answer(
        text,
        reply_markup=accounts_actions_keyboard(),
    )


@router.message(
    F.text == Texts.Accounts.PROXY_CHANGE, StateFilter(AccountsStates.account_selected)
)
async def proxy_change(message: Message, state: FSMContext) -> None:
    """
    Обработчик для смены proxy у аккаунта.
    """
    data = await state.get_data()
    account_id = data.get("account_id")
    if account_id is None:
        return await message.answer(
            "Сначала выберите аккаунт.",
            reply_markup=accounts_actions_keyboard(),
        )

    client = await accounts_repo.get_backpack_client_by_account_id(account_id)
    if not client:
        return await message.answer(
            "Аккаунт не найден.",
            reply_markup=accounts_actions_keyboard(),
        )

    await message.answer(
        "🔄 Смена proxy…",
        reply_markup=accounts_actions_keyboard(),
    )
    try:
        await client.change_proxy()
    except Exception as e:
        logger.warning(f"Proxy change error: {e}")
        return await message.answer(
            "❌ Не удалось сменить proxy.",
            reply_markup=accounts_actions_keyboard(),
        )

    try:
        info = await client.check_proxy()
        ip = info.get("ip")
    except Exception:
        ip = None

    if ip:
        await message.answer(
            f"✅ Proxy сменён. Новый IP: {ip}",
            reply_markup=accounts_actions_keyboard(),
        )
    else:
        await message.answer(
            "✅ Proxy сменён.",
            reply_markup=accounts_actions_keyboard(),
        )
