from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from loguru import logger

from src.bot.features.home.keyboards import main_menu_keyboard
from src.bot.triggers import Texts
from src.core.repositories import friends as friends_repo

router = Router()


class FriendStates(StatesGroup):
    waiting_username = State()


# ───────── список друзей ─────────
@router.message(Command("friends"))
async def friends_list(message: Message) -> None:
    links = await friends_repo.friends_for_user(message.from_user.id)
    if not links:
        await message.answer(
            "У вас пока нет друзей 🙁", reply_markup=main_menu_keyboard()
        )
        return

    lines = [
        f"{'✅' if l.confirmed else '⏳'} "
        f"{('@' + l.friend.username) if l.friend.username else l.friend_id}"
        for l in links
    ]
    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


# ───────── добавить друга ─────────
@router.message(Command("addfriend"))
@router.message(F.text == Texts.Friends.ADD)
async def friend_add_start(message: Message, state: FSMContext) -> None:
    await state.set_state(FriendStates.waiting_username)
    await message.answer(
        "Пришлите Telegram‑ник друга (можно с @):", reply_markup=main_menu_keyboard()
    )


@router.message(StateFilter(FriendStates.waiting_username))
async def friend_add_finish(message: Message, state: FSMContext, bot) -> None:
    raw_username = message.text.strip().lstrip("@")
    me = message.from_user

    try:
        already, confirmed_now, friend = await friends_repo.add_friend(
            me.id, me.username, raw_username
        )
    except LookupError:
        await message.answer(
            "❌ Пользователь ещё не зарегистрирован в боте.",
            reply_markup=main_menu_keyboard(),
        )
        await state.clear()
        return
    except ValueError:
        await message.answer(
            "Нельзя добавить самого себя 😉", reply_markup=main_menu_keyboard()
        )
        await state.clear()
        return

    await state.clear()

    if already:
        await message.answer(
            "Этот пользователь уже в вашем списке друзей.",
            reply_markup=main_menu_keyboard(),
        )
        return

    if confirmed_now:
        await message.answer(
            f"🎉 Вы и @{friend.username} теперь друзья!",
            reply_markup=main_menu_keyboard(),
        )
        try:
            await bot.send_message(
                friend.telegram_id,
                f"🎉 Пользователь @{me.username} принял вашу заявку в друзья!",
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление другу: {e}")
    else:
        await message.answer(
            f"Запрос отправлен! @{friend.username} появится после подтверждения.",
            reply_markup=main_menu_keyboard(),
        )
        try:
            await bot.send_message(
                friend.telegram_id,
                f"🆕 Пользователь @{me.username} отправил вам запрос в друзья.\n"
                f"Чтобы принять — /addfriend @{me.username}",
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление о заявке: {e}")


# ───────── удалить друга ─────────
@router.message(Command("delfriend"))
async def friend_delete(message: Message, bot) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer(
            "Формат: /delfriend <username>", reply_markup=main_menu_keyboard()
        )
        return

    removed, friend = await friends_repo.delete_friend(
        message.from_user.id, parts[1].lstrip("@")
    )

    if friend is None:
        await message.answer(
            "Пользователь не найден.", reply_markup=main_menu_keyboard()
        )
        return
    if not removed:
        await message.answer(
            "Этого пользователя нет в вашем списке.", reply_markup=main_menu_keyboard()
        )
        return

    await message.answer("Дружба удалена.", reply_markup=main_menu_keyboard())
    try:
        await bot.send_message(
            friend.telegram_id,
            f"Пользователь @{message.from_user.username} удалил вас из друзей.",
        )
    except Exception as e:
        logger.warning(f"Не удалось сообщить другу об удалении: {e}")
