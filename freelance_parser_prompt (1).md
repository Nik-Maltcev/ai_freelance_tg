# Промт для Claude Code: Telegram бот парсинга фриланс-запросов

Создай сервис для парсинга фриланс-запросов из 100+ Telegram чатов с фоновым воркером и мгновенной выдачей юзеру.

---

## Архитектура

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Worker         │     │    PostgreSQL    │     │   Telegram Bot   │
│   (фоновый)      │────▶│    (кеш данных)  │◀────│   (отдаёт юзеру) │
│                  │     │                  │     │                  │
│ • Парсит чаты    │     │ • requests       │     │ • /start         │
│ • Анализ Claude  │     │ • categories     │     │ • Выбор категории│
│ • Каждые 2 часа  │     │ • parse_logs     │     │ • Мгновенный ответ│
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## Стек

- Python 3.11+
- aiogram 3.x — Telegram бот
- Telethon — парсинг чатов (userbot)
- google-genai — Gemini API для анализа
- SQLAlchemy + PostgreSQL — хранение
- APScheduler — планировщик фоновых задач
- Docker + docker-compose — деплой

---

## Структура проекта

```
freelance_parser/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Запуск бота
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py         # /start, выбор категории
│   │   ├── requests.py      # Показ запросов
│   │   └── admin.py         # Админ-команды (статус, ручной парсинг)
│   ├── keyboards.py         # Inline-клавиатуры
│   └── middlewares.py       # Проверка whitelist
│
├── worker/
│   ├── __init__.py
│   ├── main.py              # Запуск воркера
│   ├── scheduler.py         # APScheduler конфиг
│   ├── jobs/
│   │   ├── __init__.py
│   │   ├── parser.py        # Парсинг чатов через Telethon
│   │   └── analyzer.py      # Анализ через Claude
│   └── telethon_client.py   # Singleton клиент Telethon
│
├── core/
│   ├── __init__.py
│   ├── config.py            # Pydantic Settings
│   ├── database.py          # SQLAlchemy async engine
│   └── models.py            # ORM модели
│
├── services/
│   ├── __init__.py
│   ├── request_service.py   # CRUD для запросов
│   └── category_service.py  # Работа с категориями
│
├── config/
│   └── chats.yaml           # Конфиг чатов по категориям
│
├── alembic/                 # Миграции БД
├── docker-compose.yml
├── Dockerfile.bot
├── Dockerfile.worker
├── .env.example
├── requirements.txt
└── README.md
```

---

## Конфиг чатов (config/chats.yaml)

```yaml
categories:
  web_dev:
    name: "🌐 Веб-разработка"
    description: "Frontend, Backend, Fullstack"
    chats:
      - "@webdev_jobs"
      - "@frontend_work"
      - "@backend_jobs"
      - -1001234567890  # ID приватного чата
      
  mobile:
    name: "📱 Мобильная разработка"
    description: "iOS, Android, Flutter, React Native"
    chats:
      - "@ios_jobs"
      - "@android_dev_jobs"
      
  design:
    name: "🎨 Дизайн"
    description: "UI/UX, графический дизайн, 3D"
    chats:
      - "@design_freelance"
      - "@ui_ux_jobs"
      
  copywriting:
    name: "✍️ Копирайтинг"
    description: "Тексты, переводы, SMM"
    chats:
      - "@copywriters_ru"
      - "@smm_jobs"
      
  marketing:
    name: "📈 Маркетинг"
    description: "SEO, контекст, таргет"
    chats:
      - "@marketing_jobs"
      - "@seo_freelance"

  # Добавь остальные категории...

settings:
  parse_interval_hours: 2      # Как часто парсить
  messages_ttl_days: 30        # Сколько хранить в БД
  batch_size: 50               # Сообщений на один запрос Claude
  request_delay_sec: 1.5       # Пауза между чатами (антибан)
```

---

## Модели БД (core/models.py)

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class FreelanceRequest(Base):
    __tablename__ = "freelance_requests"
    
    id = Column(Integer, primary_key=True)
    
    # Основные поля
    category = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    budget = Column(String(100))
    skills = Column(JSON, default=list)  # ["Python", "Django", "PostgreSQL"]
    contact = Column(String(500))
    urgency = Column(String(20), default="normal")  # urgent / normal
    
    # Источник
    source_chat = Column(String(100))
    source_message_id = Column(Integer)
    message_date = Column(DateTime, nullable=False)
    message_text_hash = Column(String(64), unique=True)  # Дедупликация
    
    # Мета
    parsed_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        Index("idx_category_date", "category", "message_date"),
        Index("idx_active_category", "is_active", "category"),
    )


class ParseLog(Base):
    __tablename__ = "parse_logs"
    
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String(20))  # running / success / failed
    chats_parsed = Column(Integer, default=0)
    messages_found = Column(Integer, default=0)
    requests_extracted = Column(Integer, default=0)
    error_message = Column(Text)


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True)
    slug = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    chats_count = Column(Integer, default=0)
    last_parsed_at = Column(DateTime)
```

---

## Парсер (worker/jobs/parser.py)

```python
import asyncio
import hashlib
from datetime import datetime, timedelta
from telethon import TelegramClient
from core.config import settings
from core.database import async_session
from core.models import FreelanceRequest
import logging

logger = logging.getLogger(__name__)


class ChatParser:
    def __init__(self, client: TelegramClient):
        self.client = client
        
    async def parse_chat(self, chat_id: str | int, days: int = 7) -> list[dict]:
        """Парсит один чат за N дней"""
        messages = []
        since = datetime.now() - timedelta(days=days)
        
        try:
            async for msg in self.client.iter_messages(
                chat_id,
                offset_date=since,
                limit=1000  # Лимит на чат
            ):
                if not msg.text or len(msg.text) < 50:
                    continue
                    
                # Пропускаем ботов и сервисные сообщения
                if msg.sender and getattr(msg.sender, 'bot', False):
                    continue
                
                messages.append({
                    "chat_id": str(chat_id),
                    "message_id": msg.id,
                    "date": msg.date.isoformat(),
                    "text": msg.text[:2000],  # Обрезаем длинные
                    "hash": hashlib.sha256(msg.text.encode()).hexdigest()[:16]
                })
                
        except Exception as e:
            logger.error(f"Ошибка парсинга {chat_id}: {e}")
            
        return messages
    
    async def parse_category(
        self, 
        category_slug: str, 
        chat_ids: list[str | int],
        days: int = 7
    ) -> list[dict]:
        """Парсит все чаты категории с паузами"""
        all_messages = []
        
        for i, chat_id in enumerate(chat_ids):
            logger.info(f"[{category_slug}] Парсинг {i+1}/{len(chat_ids)}: {chat_id}")
            
            messages = await self.parse_chat(chat_id, days)
            for msg in messages:
                msg["category"] = category_slug
            all_messages.extend(messages)
            
            # Антибан пауза
            if i < len(chat_ids) - 1:
                await asyncio.sleep(settings.REQUEST_DELAY_SEC)
                
        logger.info(f"[{category_slug}] Собрано {len(all_messages)} сообщений")
        return all_messages
```

---

## Анализатор Gemini (worker/jobs/analyzer.py)

```python
import json
import google.generativeai as genai
from core.config import settings
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — эксперт по анализу фриланс-чатов. Твоя задача — извлечь ТОЛЬКО реальные запросы на работу (заказы).

ИЗВЛЕКАЙ запросы где человек ИЩЕТ исполнителя:
- "Нужен разработчик...", "Ищу дизайнера...", "Требуется..."
- "Сделать сайт...", "Нарисовать логотип..."
- "Бюджет: ...", "Оплата: ..."

ИГНОРИРУЙ:
- Резюме и самопрезентации ("Я разработчик, ищу работу")
- Вопросы и обсуждения ("Как лучше сделать...?")
- Рекламу курсов, каналов, сервисов
- Сообщения без конкретной задачи
- Откровенный спам

Для каждого запроса верни JSON объект:
{
  "title": "Краткое название (до 60 символов)",
  "description": "Суть задачи в 1-2 предложениях",
  "budget": "Бюджет или 'Не указан'",
  "skills": ["skill1", "skill2"],
  "contact": "Контакт если есть или null",
  "urgency": "urgent" или "normal",
  "source_message_id": <id сообщения из входных данных>
}

Верни ТОЛЬКО JSON массив без markdown-обёртки. Если запросов нет — верни []."""


class GeminiAnalyzer:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json"  # Гарантирует JSON ответ
            )
        )
        
    async def analyze_batch(self, messages: list[dict]) -> list[dict]:
        """Анализирует батч сообщений"""
        if not messages:
            return []
            
        # Форматируем для Gemini
        formatted = "\n\n---\n\n".join([
            f"[ID: {m['message_id']}] [Дата: {m['date']}]\n{m['text']}"
            for m in messages
        ])
        
        try:
            response = await self.model.generate_content_async(
                f"Проанализируй сообщения и извлеки запросы на работу:\n\n{formatted}"
            )
            
            # Gemini с response_mime_type="application/json" возвращает чистый JSON
            text = response.text
            
            # На всякий случай убираем markdown если есть
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            return json.loads(text.strip())
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от Gemini: {e}")
            return []
        except Exception as e:
            logger.error(f"Ошибка Gemini API: {e}")
            return []
    
    async def analyze_all(
        self, 
        messages: list[dict], 
        batch_size: int = 100  # Gemini имеет большой контекст, можно больше
    ) -> list[dict]:
        """Анализирует все сообщения батчами"""
        all_requests = []
        
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            logger.info(f"Анализ батча {i//batch_size + 1}/{(len(messages)-1)//batch_size + 1}")
            
            requests = await self.analyze_batch(batch)
            
            # Добавляем метаданные
            msg_map = {m["message_id"]: m for m in batch}
            for req in requests:
                msg_id = req.get("source_message_id")
                if msg_id and msg_id in msg_map:
                    req["source_chat"] = msg_map[msg_id]["chat_id"]
                    req["message_date"] = msg_map[msg_id]["date"]
                    req["category"] = msg_map[msg_id]["category"]
                    req["message_text_hash"] = msg_map[msg_id]["hash"]
                    
            all_requests.extend(requests)
            
        return all_requests
```

---

## Планировщик (worker/scheduler.py)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from worker.jobs.parser import ChatParser
from worker.jobs.analyzer import GeminiAnalyzer
from worker.telethon_client import get_telethon_client
from services.request_service import RequestService
from core.config import settings, load_chats_config
from core.database import async_session
import logging

logger = logging.getLogger(__name__)


async def parse_and_analyze_job():
    """Главная джоба: парсинг + анализ + сохранение"""
    logger.info("=== Запуск парсинга ===")
    
    config = load_chats_config()
    client = await get_telethon_client()
    parser = ChatParser(client)
    analyzer = GeminiAnalyzer()
    
    async with async_session() as session:
        request_service = RequestService(session)
        
        # Создаём лог
        log_id = await request_service.create_parse_log()
        
        total_messages = 0
        total_requests = 0
        
        try:
            for category_slug, category_data in config["categories"].items():
                chat_ids = category_data.get("chats", [])
                if not chat_ids:
                    continue
                    
                logger.info(f"Категория: {category_slug} ({len(chat_ids)} чатов)")
                
                # Парсим
                messages = await parser.parse_category(
                    category_slug, 
                    chat_ids,
                    days=7
                )
                total_messages += len(messages)
                
                if not messages:
                    continue
                
                # Анализируем
                requests = await analyzer.analyze_all(messages)
                total_requests += len(requests)
                
                # Сохраняем (с дедупликацией)
                await request_service.save_requests(requests)
                
            # Удаляем старые записи
            await request_service.cleanup_old_requests(days=30)
            
            # Обновляем лог
            await request_service.finish_parse_log(
                log_id,
                status="success",
                messages_found=total_messages,
                requests_extracted=total_requests
            )
            
            logger.info(f"=== Готово: {total_messages} сообщений → {total_requests} запросов ===")
            
        except Exception as e:
            logger.exception("Ошибка в джобе парсинга")
            await request_service.finish_parse_log(log_id, status="failed", error=str(e))


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    
    # Каждые N часов
    scheduler.add_job(
        parse_and_analyze_job,
        trigger=IntervalTrigger(hours=settings.PARSE_INTERVAL_HOURS),
        id="main_parser",
        name="Парсинг фриланс-чатов",
        replace_existing=True
    )
    
    # Сразу при старте
    scheduler.add_job(
        parse_and_analyze_job,
        id="initial_parse",
        name="Первичный парсинг"
    )
    
    return scheduler
```

---

## Telegram бот — хендлеры (bot/handlers/start.py)

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from bot.keyboards import get_categories_keyboard, get_period_keyboard
from services.category_service import CategoryService
from core.database import async_session

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 <b>Привет! Я бот для поиска фриланс-заказов.</b>\n\n"
        "Я собираю запросы из 100+ чатов и показываю их в удобном виде.\n\n"
        "Выбери категорию:",
        reply_markup=get_categories_keyboard()
    )


@router.callback_query(F.data.startswith("category:"))
async def select_category(callback: CallbackQuery):
    category_slug = callback.data.split(":")[1]
    
    async with async_session() as session:
        service = CategoryService(session)
        category = await service.get_by_slug(category_slug)
        
    await callback.message.edit_text(
        f"📁 <b>{category.name}</b>\n\n"
        f"{category.description}\n\n"
        "За какой период показать запросы?",
        reply_markup=get_period_keyboard(category_slug)
    )
```

---

## Telegram бот — показ запросов (bot/handlers/requests.py)

```python
from aiogram import Router, F
from aiogram.types import CallbackQuery
from services.request_service import RequestService
from bot.keyboards import get_pagination_keyboard, get_back_keyboard
from core.database import async_session

router = Router()

REQUESTS_PER_PAGE = 5


@router.callback_query(F.data.startswith("requests:"))
async def show_requests(callback: CallbackQuery):
    """Показывает запросы по категории и периоду"""
    _, category_slug, days, page = callback.data.split(":")
    days = int(days)
    page = int(page)
    
    async with async_session() as session:
        service = RequestService(session)
        
        requests, total = await service.get_requests(
            category=category_slug,
            days=days,
            offset=page * REQUESTS_PER_PAGE,
            limit=REQUESTS_PER_PAGE
        )
    
    if not requests:
        await callback.message.edit_text(
            f"😕 За {days} дней в этой категории запросов не найдено.\n\n"
            "Попробуй выбрать другой период или категорию.",
            reply_markup=get_back_keyboard()
        )
        return
    
    # Форматируем
    text = f"📋 <b>Найдено {total} запросов</b> (стр. {page + 1}/{(total - 1) // REQUESTS_PER_PAGE + 1})\n\n"
    
    for i, req in enumerate(requests, start=page * REQUESTS_PER_PAGE + 1):
        text += f"<b>{i}. {req.title}</b>\n"
        text += f"{req.description}\n"
        text += f"💰 {req.budget}"
        
        if req.skills:
            skills_str = ", ".join(req.skills[:3])
            text += f" | 🛠 {skills_str}"
            
        if req.contact:
            text += f"\n📩 {req.contact}"
            
        if req.urgency == "urgent":
            text += " 🔥"
            
        text += "\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pagination_keyboard(category_slug, days, page, total, REQUESTS_PER_PAGE)
    )


@router.callback_query(F.data == "refresh")
async def refresh_requests(callback: CallbackQuery):
    """Обновить данные (показать что последний парсинг был в ...)"""
    async with async_session() as session:
        service = RequestService(session)
        last_log = await service.get_last_parse_log()
        
    if last_log:
        await callback.answer(
            f"✅ Данные обновлены: {last_log.finished_at.strftime('%H:%M')}\n"
            f"Следующее обновление через ~{2 - (datetime.now() - last_log.finished_at).seconds // 3600} ч.",
            show_alert=True
        )
    else:
        await callback.answer("⏳ Парсинг ещё не запускался", show_alert=True)
```

---

## Клавиатуры (bot/keyboards.py)

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import load_chats_config


def get_categories_keyboard() -> InlineKeyboardMarkup:
    config = load_chats_config()
    buttons = []
    
    for slug, data in config["categories"].items():
        buttons.append([
            InlineKeyboardButton(
                text=data["name"],
                callback_data=f"category:{slug}"
            )
        ])
    
    # Кнопка "Все категории"
    buttons.append([
        InlineKeyboardButton(text="🌐 Все категории", callback_data="category:all")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_period_keyboard(category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 7 дней", callback_data=f"requests:{category}:7:0"),
            InlineKeyboardButton(text="📅 30 дней", callback_data=f"requests:{category}:30:0"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back:start")
        ]
    ])


def get_pagination_keyboard(
    category: str, 
    days: int, 
    page: int, 
    total: int,
    per_page: int
) -> InlineKeyboardMarkup:
    buttons = []
    nav_row = []
    
    # Кнопка "Назад"
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="◀️", callback_data=f"requests:{category}:{days}:{page - 1}")
        )
    
    # Счётчик страниц
    nav_row.append(
        InlineKeyboardButton(text=f"{page + 1}/{(total - 1) // per_page + 1}", callback_data="noop")
    )
    
    # Кнопка "Вперёд"
    if (page + 1) * per_page < total:
        nav_row.append(
            InlineKeyboardButton(text="▶️", callback_data=f"requests:{category}:{days}:{page + 1}")
        )
    
    buttons.append(nav_row)
    
    # Дополнительные кнопки
    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh"),
        InlineKeyboardButton(text="◀️ Категории", callback_data="back:start")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back:start")]
    ])
```

---

## Конфигурация (core/config.py)

```python
from pydantic_settings import BaseSettings
from functools import lru_cache
import yaml


class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []  # Whitelist админов
    
    # Telethon (userbot)
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_PHONE: str
    
    # Gemini
    GEMINI_API_KEY: str
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/freelance_parser"
    
    # Parser settings
    PARSE_INTERVAL_HOURS: int = 2
    REQUEST_DELAY_SEC: float = 1.5
    MESSAGES_TTL_DAYS: int = 30
    BATCH_SIZE: int = 50
    
    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


@lru_cache
def load_chats_config() -> dict:
    with open("config/chats.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
```

---

## Docker Compose

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: freelance
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: freelance_parser
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U freelance"]
      interval: 5s
      timeout: 5s
      retries: 5

  bot:
    build:
      context: .
      dockerfile: Dockerfile.bot
    depends_on:
      postgres:
        condition: service_healthy
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://freelance:${DB_PASSWORD}@postgres:5432/freelance_parser
    restart: unless-stopped

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    depends_on:
      postgres:
        condition: service_healthy
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://freelance:${DB_PASSWORD}@postgres:5432/freelance_parser
    volumes:
      - ./sessions:/app/sessions  # Telethon сессии
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## .env.example

```bash
# Telegram Bot
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=[123456789, 987654321]

# Telethon (получить на my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+79001234567

# Gemini API (получить на aistudio.google.com)
GEMINI_API_KEY=AIzaSy...

# Database
DB_PASSWORD=supersecretpassword

# Settings
PARSE_INTERVAL_HOURS=2
REQUEST_DELAY_SEC=1.5
```

---

## Первый запуск

1. Клонировать проект
2. Скопировать `.env.example` → `.env` и заполнить
3. Заполнить `config/chats.yaml` своими чатами
4. Запустить:

```bash
# Первый раз — авторизация Telethon
docker-compose run --rm worker python -c "from worker.telethon_client import auth; auth()"

# Запуск всего
docker-compose up -d

# Логи
docker-compose logs -f worker
docker-compose logs -f bot
```

---

## Админ-команды (опционально)

```
/status — статус последнего парсинга
/parse — запустить парсинг вручную
/stats — статистика (сколько запросов по категориям)
```

---

## Важные моменты

1. **Telethon сессия** — сохраняется в volume, не потеряется при рестарте
2. **Дедупликация** — по хешу текста сообщения, дубли не создаются
3. **Антибан** — пауза 1.5 сек между чатами, можно увеличить если банят
4. **TTL записей** — старые запросы удаляются через 30 дней
5. **Whitelist** — добавь ADMIN_IDS чтобы не все могли юзать бота

---

Готово! Начни с `docker-compose up` и смотри логи воркера.
