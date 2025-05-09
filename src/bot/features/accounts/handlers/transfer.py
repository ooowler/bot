# src/bot/features/accounts/handlers/transfer.py
import json
import html
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from src.bot.features.accounts.keyboards import (
    accounts_keyboard,
    accounts_actions_keyboard,
)
from src.bot.features.accounts.states import (
    AccountsStates,
    TransferStates,
)
from src.bot.triggers import Texts
from src.core.repositories import accounts as accounts_repo

router = Router()


def _format_result_html(res: dict) -> str:
    dumped = json.dumps(res, indent=2, ensure_ascii=False)
    return f"<pre>{html.escape(dumped)}</pre>"


router = Router()


@router.message(
    F.text == Texts.Accounts.TRANSFER,
    StateFilter(AccountsStates.account_selected),
)
async def transfer_start(message: Message, state: FSMContext) -> None:
    me_tid = message.from_user.id
    data = await state.get_data()
    from_id = data["account_id"]

    # 1) получаем из репозитория список только parent + sub-аккантов
    #    сперва узнаём parent_id текущего
    from_acc = await accounts_repo.get_by_id(from_id)
    targets = await accounts_repo.get_transfer_targets(
        owner_tid=me_tid,
        from_acc_id=from_id,
        parent_id=from_acc.parent_id,
    )

    if not targets:
        await message.answer(
            "У этого аккаунта нет ни sub-аккаунтов, ни родительского.",
            reply_markup=accounts_actions_keyboard(),
        )
        return

    # 2) строим клавиатуру из targets
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=acc.name)] for acc in targets],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await state.update_data(from_acc_id=from_id)
    await state.set_state(TransferStates.choosing_target)
    await message.answer(
        "Кому переводим? Выберите sub-аккаунт или родительский:",
        reply_markup=kb,
    )


@router.message(StateFilter(TransferStates.choosing_target))
async def transfer_choose_target(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    # сначала по name, потом по api_key/name
    acc = await accounts_repo.get_by_api_or_name(raw)
    if not acc:
        await message.answer(
            "Аккаунт не найден. Пожалуйста, выберите из списка.",
            reply_markup=accounts_keyboard(),
        )
        return

    await state.update_data(to_acc_id=acc.id, to_acc_name=acc.name)
    await state.set_state(TransferStates.entering_amount)
    await message.answer(
        f"Введите сумму для перевода на аккаунт {acc.name}:",
        reply_markup=accounts_keyboard(),
    )


@router.message(StateFilter(TransferStates.entering_amount))
async def transfer_enter_amount(message: Message, state: FSMContext) -> None:
    txt = message.text.strip()
    try:
        amount = str(Decimal(txt))
    except InvalidOperation:
        await message.answer(
            "❌ Некорректная сумма. Повторите ввод:",
            reply_markup=accounts_keyboard(),
        )
        return

    data = await state.get_data()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, перевести", callback_data="transfer:confirm"
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="transfer:cancel")],
        ]
    )
    await state.update_data(amount=amount)
    await state.set_state(TransferStates.confirming)
    await message.answer(
        f"Подтвердите перевод {amount} на аккаунт {data['to_acc_name']}:",
        reply_markup=kb,
    )


@router.callback_query(
    F.data == "transfer:cancel", StateFilter(TransferStates.confirming)
)
async def transfer_cancel(cb, state: FSMContext) -> None:
    await cb.answer("Перевод отменён", show_alert=True)
    await state.clear()
    await cb.message.edit_reply_markup(None)
    await cb.message.answer("Отмена.", reply_markup=accounts_actions_keyboard())


@router.callback_query(
    F.data == "transfer:confirm", StateFilter(TransferStates.confirming)
)
async def transfer_confirm(cb, state: FSMContext) -> None:
    data = await state.get_data()
    from_id = data["from_acc_id"]
    to_id = data["to_acc_id"]
    amount = data["amount"]

    # 1) получаем deposit-адрес через репозиторий
    deposit = await accounts_repo.get_deposit_address(to_id)
    if not deposit:
        await cb.answer("❌ У аккаунта нет адреса для депозита.", show_alert=True)
        await state.clear()
        return

    client = await accounts_repo.get_backpack_client_by_account_id(from_id)
    result = await client.request_withdrawal(
        address=deposit.address,
        blockchain="Solana",
        symbol="SOL",
        quantity=amount,
    )

    await cb.message.edit_reply_markup(None)
    await cb.message.answer(
        "💸 Результат перевода:\n" + _format_result_html(result),
        parse_mode="HTML",
        reply_markup=accounts_actions_keyboard(),
    )
    await state.clear()
