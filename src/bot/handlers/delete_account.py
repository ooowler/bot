from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select, delete
from loguru import logger

from src.bot.callbacks import Callbacks
from src.bot.keyboards.start.start import get_welcome_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import (
    User,
    Account,
    UserAccountLink,
    DepositAddress,
)

delete_router = Router()


# ─────────────────────── FSM ────────────────────────
class DeleteAccount(StatesGroup):
    waiting_api_key = State()


# ─────────── кнопка «Удалить аккаунт» ────────────
@delete_router.callback_query(F.data == Callbacks.Accounts.DELETE)
async def ask_pub_key(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DeleteAccount.waiting_api_key)
    await cb.message.edit_text(
        "⚠️ Пришлите PUBLIC API‑KEY аккаунта, который хотите удалить.\n"
        "Удаление доступно только администраторам аккаунта.",
    )
    await cb.answer()


# ─────────────── само удаление ────────────────
@delete_router.message(DeleteAccount.waiting_api_key)
async def delete_account(msg: Message, state: FSMContext) -> None:
    api_key = msg.text.strip()

    async with pg.session_maker() as session:
        # текущий Telegram‑пользователь
        user: User | None = await session.scalar(
            select(User).where(User.telegram_id == str(msg.from_user.id))
        )
        if user is None:
            await state.clear()
            await msg.answer(
                "❌ Сначала выполните /start.", reply_markup=get_welcome_keyboard()
            )
            return

        # проверяем, что этот пользователь админ выбранного аккаунта
        link: UserAccountLink | None = await session.scalar(
            select(UserAccountLink)
            .join(Account, Account.id == UserAccountLink.account_id)
            .where(
                Account.api_key == api_key,
                UserAccountLink.user_id == user.id,
                UserAccountLink.is_admin.is_(True),
            )
        )
        if link is None:
            await state.clear()
            await msg.answer(
                "🚫 Такого аккаунта не существует.", reply_markup=get_welcome_keyboard()
            )
            return

        account_id = (
            link.account_id
        )  # не обращаемся к link.account (избегаем ленивой загрузки)

        # удаляем связанные сущности и сам аккаунт
        await session.execute(
            delete(DepositAddress).where(DepositAddress.account_id == account_id)
        )
        await session.execute(
            delete(UserAccountLink).where(UserAccountLink.account_id == account_id)
        )
        await session.execute(delete(Account).where(Account.id == account_id))
        await session.commit()

        logger.info("Account %s удалён пользователем %s", account_id, msg.from_user.id)

    await state.clear()
    await msg.answer("✅ Аккаунт удалён.", reply_markup=get_welcome_keyboard())
