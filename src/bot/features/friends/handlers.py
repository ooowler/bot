from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy import select, exists, literal, BigInteger

from src.bot.triggers import Texts
from src.bot.features.home.keyboards import main_menu_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import User, UserFriend

router = Router()


# ───────────────────────────── FSM ─────────────────────────────
class FriendStates(StatesGroup):
    waiting_username = State()


# ───────────────────────────── STEP 1 — кнопка «Добавить друга» ─────────────────────────────
@router.message(F.text == Texts.Friends.ADD)
async def friend_add_start(message: Message, state: FSMContext):
    await state.set_state(FriendStates.waiting_username)
    await message.answer(
        "Пришлите Telegram‑ник друга (можно c @):",
        reply_markup=main_menu_keyboard(),
    )


# ───────────────────────────── STEP 2 — получаем ник ─────────────────────────────
@router.message(StateFilter(FriendStates.waiting_username))
async def friend_add_finish(message: Message, state: FSMContext):
    my_tid: int = message.from_user.id
    raw_username = message.text.strip().lstrip("@").lower()

    async with pg.session_maker() as session:
        # 1) ищем пользователя по username
        friend = await session.scalar(
            select(User).where(User.username.ilike(raw_username))
        )
        if not friend:
            await message.answer(
                "❌ Этот пользователь ещё не зарегистрирован в боте.",
                reply_markup=main_menu_keyboard(),
            )
            await state.clear()
            return

        # 2) нельзя добавить самого себя
        if friend.telegram_id == my_tid:
            await message.answer(
                "Нельзя добавить самого себя 😉",
                reply_markup=main_menu_keyboard(),
            )
            await state.clear()
            return

        # 3) проверяем, нет ли уже связи (BIGINT → явное literal)
        already = await session.scalar(
            select(
                exists().where(
                    (UserFriend.user_id == literal(my_tid, type_=BigInteger()))
                    & (
                        UserFriend.friend_id
                        == literal(friend.telegram_id, type_=BigInteger())
                    )
                )
            )
        )
        if already:
            await message.answer(
                "Этот пользователь уже в вашем списке друзей.",
                reply_markup=main_menu_keyboard(),
            )
            await state.clear()
            return

        # 4) создаём двустороннюю связь
        session.add_all(
            [
                UserFriend(user_id=my_tid, friend_id=friend.telegram_id),
                UserFriend(user_id=friend.telegram_id, friend_id=my_tid),
            ]
        )
        await session.commit()

    await state.clear()
    await message.answer(
        f"Пользователь @{friend.username} добавлен в друзья ✅",
        reply_markup=main_menu_keyboard(),
    )
