# Crypto Parser Bot

Telegram-бот для парсинга сообщений из крипто-чатов. Собирает сообщения за последние 2 дня и сохраняет в JSON.

## Возможности

- 📥 Парсинг 100+ крипто-чатов через Telethon
- 📄 Экспорт сообщений в JSON
- 🤖 Telegram-бот для управления
- ⏰ Автоматический парсинг каждые 6 часов

## Команды бота

- `/start` - Приветствие
- `/parse` - Запустить парсинг вручную
- `/export` - Скачать последний JSON
- `/status` - Статус последнего парсинга
- `/help` - Справка

## Установка

1. Клонируй репозиторий
2. Создай `.env` из `.env.example`:
```bash
cp .env.example .env
```

3. Заполни переменные:
- `BOT_TOKEN` - токен от @BotFather
- `ADMIN_IDS` - твой Telegram ID
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` - с https://my.telegram.org/apps
- `TELEGRAM_PHONE` - твой номер телефона
- `DATABASE_URL` - PostgreSQL

4. Установи зависимости:
```bash
pip install -r requirements.txt
```

5. Запусти PostgreSQL:
```bash
docker run -d --name crypto-parser-db \
  -e POSTGRES_USER=parser \
  -e POSTGRES_PASSWORD=parser \
  -e POSTGRES_DB=crypto_parser \
  -p 5432:5432 postgres:16-alpine
```

## Запуск

**Бот:**
```bash
python -m bot.main
```

**Worker (парсер):**
```bash
python -m worker.main
```

## Docker

```bash
docker-compose up -d
```

## Структура JSON

```json
{
  "parsed_at": "2025-01-21T12:00:00",
  "parse_days": 2,
  "chats_count": 100,
  "messages_count": 5000,
  "messages": [
    {
      "chat": "BinanceRussianSpeaking",
      "chat_title": "Binance Russian",
      "message_id": 123456,
      "date": "2025-01-21T10:30:00+00:00",
      "text": "Текст сообщения...",
      "sender_name": "Иван Иванов",
      "sender_username": "ivan"
    }
  ]
}
```

## Конфигурация чатов

Список чатов в `config/chats.yaml`. Формат:
```yaml
settings:
  parse_days: 2
  request_delay_sec: 1.5
  min_message_length: 10

chats:
  - "BinanceRussianSpeaking"
  - "BybitRussian"
  - "okx_russian"
```
