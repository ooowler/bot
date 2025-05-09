from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from src.bot.triggers import Texts
from src.bot.features.friends.states import FriendStates
from src.bot.features.friends.keyboards import get_cancel_keyboard, get_main_keyboard
from src.core.repositories import friends as friends_repo
from src.core.repositories.user import ensure_user

router = Router()


@router.message(F.text == Texts.Friends.HOME)
async def friend_menu(message: Message, state: FSMContext):
    # Ensure user exists
    await ensure_user(message.from_user.id, message.from_user.username)
    await state.set_state(FriendStates.menu)
    await message.answer(
        "Выберите действие для управления друзьями:", reply_markup=get_main_keyboard()
    )


@router.message(F.text == "Отмена")
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Операция отменена.", reply_markup=get_main_keyboard())


@router.message(F.text == "Список друзей", StateFilter(FriendStates.menu))
async def list_friends(message: Message, state: FSMContext):
    links = await friends_repo.friends_for_user(message.from_user.id)
    if not links:
        await message.answer(
            "У вас пока нет друзей 🙁", reply_markup=get_main_keyboard()
        )
    else:
        lines = []
        for l in links:
            mark = "✅" if l.confirmed else "⏳"
            uname = "@" + l.friend.username if l.friend.username else str(l.friend_id)
            lines.append(f"{mark} {uname}")
        await message.answer(
            "Ваши друзья:\n" + "\n".join(lines), reply_markup=get_main_keyboard()
        )
    await state.clear()


@router.message(F.text == "Добавить друга", StateFilter(FriendStates.menu))
async def add_friend_start(message: Message, state: FSMContext):
    await state.set_state(FriendStates.waiting_add_username)
    await message.answer(
        "Пришлите Telegram‑ник друга (без @):", reply_markup=get_cancel_keyboard()
    )


@router.message(StateFilter(FriendStates.waiting_add_username))
async def add_friend_finish(message: Message, state: FSMContext):
    raw_username = message.text.strip().lstrip("@")
    me = message.from_user
    try:
        already, confirmed_now, friend = await friends_repo.add_friend(
            me.id, me.username, raw_username
        )
    except LookupError:
        await message.answer(
            "❌ Пользователь ещё не зарегистрирован.", reply_markup=get_main_keyboard()
        )
        await state.clear()
        return
    except ValueError:
        await message.answer(
            "Нельзя добавить самого себя 😉", reply_markup=get_main_keyboard()
        )
        await state.clear()
        return
    await state.clear()
    if already:
        await message.answer(
            "Этот пользователь уже в списке.", reply_markup=get_main_keyboard()
        )
        return
    if confirmed_now:
        await message.answer(
            f"🎉 Вы и @{friend.username} теперь друзья!",
            reply_markup=get_main_keyboard(),
        )
    else:
        await message.answer(
            f"Запрос отправлен! @{friend.username} появится после подтверждения.",
            reply_markup=get_main_keyboard(),
        )


@router.message(F.text == "Удалить друга", StateFilter(FriendStates.menu))
async def remove_friend_start(message: Message, state: FSMContext):
    await state.set_state(FriendStates.waiting_remove_username)
    await message.answer(
        "Введите Telegram‑ник для удаления (без @):", reply_markup=get_cancel_keyboard()
    )


@router.message(StateFilter(FriendStates.waiting_remove_username))
async def remove_friend_finish(message: Message, state: FSMContext):
    username = message.text.strip().lstrip("@")
    removed, friend = await friends_repo.delete_friend(message.from_user.id, username)
    await state.clear()
    if friend is None:
        await message.answer(
            "Пользователь не найден.", reply_markup=get_main_keyboard()
        )
    elif not removed:
        await message.answer(
            "Этот пользователь не в вашем списке.", reply_markup=get_main_keyboard()
        )
    else:
        await message.answer("Дружба удалена.", reply_markup=get_main_keyboard())
