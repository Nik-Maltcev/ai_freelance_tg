"""Start command handler for the Telegram bot."""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()


@router.message(Command("start"))
async def start_command(message: Message):
    """Handle /start command."""
    welcome_text = (
        "👋 Добро пожаловать в Crypto Parser Bot!\n\n"
        "Этот бот парсит сообщения из крипто-чатов "
        "и сохраняет их в JSON.\n\n"
        "Доступные команды:\n"
        "/parse - Запустить парсинг чатов\n"
        "/export - Скачать последний JSON\n"
        "/status - Статус последнего парсинга\n"
        "/help - Справка"
    )
    await message.answer(welcome_text)
