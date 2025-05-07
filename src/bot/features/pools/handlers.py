from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.triggers import Texts
from src.core.repositories.pools import (
    create_pool,
    add_account_to_pool,
    remove_account_from_pool,
    list_pools_for_user,
    list_pool_accounts,
)
from src.core.repositories.user import ensure_user

router = Router()


@router.message(Command("pool_create"))
async def cmd_pool_create(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Использование: /pool_create <label>")

    label = parts[1].strip()

    # здесь ensure_user гарантирует, что запись в users есть
    await ensure_user(message.from_user.id, message.from_user.username)

    # create_pool теперь сам найдёт user.id
    pool = await create_pool(label=label, owner_telegram_id=message.from_user.id)
    await message.answer(f"✅ Пул «{pool.label}» создан (ID={pool.id}).")


@router.message(Command("pool_add"))
async def cmd_pool_add(message: Message):
    """
    /pool_add <pool_id> <account_id>
    """
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        return await message.answer("Использование: /pool_add <pool_id> <account_id>")

    pool_id = int(parts[1])
    acc_id = int(parts[2])

    await add_account_to_pool(pool_id=pool_id, account_id=acc_id)
    await message.answer(f"✅ Аккаунт {acc_id} добавлен в пул {pool_id}.")


@router.message(Command("pool_remove"))
async def cmd_pool_remove(message: Message):
    """
    /pool_remove <pool_id> <account_id>
    """
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        return await message.answer(
            "Использование: /pool_remove <pool_id> <account_id>"
        )

    pool_id = int(parts[1])
    acc_id = int(parts[2])

    await remove_account_from_pool(pool_id=pool_id, account_id=acc_id)
    await message.answer(f"✅ Аккаунт {acc_id} удалён из пула {pool_id}.")


@router.message(Command("pools"))
async def cmd_pools_list(message: Message):
    """
    /pools — список ваших пулов
    """
    # убедимся, что пользователь есть
    await ensure_user(message.from_user.id, message.from_user.username)

    pools = await list_pools_for_user(owner_id=message.from_user.id)
    if not pools:
        return await message.answer("У вас пока нет пулов.")

    text = "\n".join(
        f"{p.id}: {p.label} (active={p.is_active}, status={p.status})" for p in pools
    )
    await message.answer("Ваши пулы:\n" + text)


@router.message(Command("pool_accounts"))
async def cmd_pool_accounts(message: Message):
    """
    /pool_accounts <pool_id> — список аккаунтов в пуле
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        return await message.answer("Использование: /pool_accounts <pool_id>")

    pool_id = int(parts[1])
    accounts = await list_pool_accounts(pool_id=pool_id)
    if not accounts:
        return await message.answer("В этом пуле нет аккаунтов.")

    text = "\n".join(f"{acc.id}: {acc.name}" for acc in accounts)
    await message.answer("Аккаунты в пуле:\n" + text)
