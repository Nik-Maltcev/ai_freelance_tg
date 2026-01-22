"""Start command and main menu handlers."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from bot.keyboards import get_main_keyboard

router = Router()


@router.message(Command("start"))
async def start_command(message: Message):
    """Handle /start command."""
    welcome_text = (
        "👋 Привет! Я Crypto Parser Bot.\n\n"
        "Я собираю сообщения из 100+ крипто-чатов "
        "и сохраняю их в JSON.\n\n"
        "Нажми кнопку ниже чтобы начать:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Return to main menu."""
    welcome_text = (
        "👋 Crypto Parser Bot\n\n"
        "Выбери действие:"
    )
    await callback.message.edit_text(welcome_text, reply_markup=get_main_keyboard())
    await callback.answer()
