# Freelance Parser Bot

A Telegram bot service that automatically parses freelance job requests from 100+ Telegram chats using Telethon and analyzes them with Google Gemini AI.

## Architecture

The service consists of three main components:

- **Bot** (aiogram 3.x): Telegram bot for users to browse freelance requests by category
- **Worker** (APScheduler): Background process that parses chats and analyzes messages with Gemini AI
- **PostgreSQL**: Database for caching requests, categories, and parse logs

## Features

- 📋 Browse freelance requests by category (web dev, mobile, design, copywriting, marketing, etc.)
- 🔄 Automatic parsing every 2 hours (configurable)
- 🤖 AI-powered analysis using Google Gemini API
- 📊 Admin commands for monitoring and manual parsing
- 🗑️ Automatic cleanup of old requests (30 days TTL)
- 🚀 Easy deployment on Railway

## Prerequisites

- Python 3.11+
- PostgreSQL 12+ (or use Railway's PostgreSQL plugin)
- Telegram account (for Telethon userbot)
- Google Gemini API key
- Telegram Bot Token (from @BotFather)

## Environment Variables

Create a `.env` file with the following variables:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_here

# Admin user IDs (comma-separated)
ADMIN_IDS=123456789,987654321

# Telegram Userbot (for parsing)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890

# Google Gemini API
GEMINI_API_KEY=your_gemini_key

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/freelance_parser

# Optional: Configuration
PARSE_INTERVAL_HOURS=2
MESSAGES_TTL_DAYS=30
BATCH_SIZE=50
REQUEST_DELAY_SEC=1.5
```

### Getting Telegram API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your Telegram account
3. Create a new application
4. Copy `API_ID` and `API_HASH`
5. Your phone number is the one associated with your Telegram account

### Getting Gemini API Key

1. Go to https://aistudio.google.com/app/apikeys
2. Create a new API key
3. Copy the key to your `.env` file

### Getting Telegram Bot Token

1. Open Telegram and search for @BotFather
2. Send `/newbot` command
3. Follow the prompts to create a new bot
4. Copy the token to your `.env` file

## Local Development

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd freelance-parser-bot
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

5. Start PostgreSQL (using Docker):
```bash
docker run -d \
  --name freelance-parser-db \
  -e POSTGRES_USER=parser \
  -e POSTGRES_PASSWORD=parser_password \
  -e POSTGRES_DB=freelance_parser \
  -p 5432:5432 \
  postgres:16-alpine
```

### Running Locally

**Terminal 1 - Start the Bot:**
```bash
python -m bot.main
```

**Terminal 2 - Start the Worker:**
```bash
python -m worker.main
```

The bot will be ready to accept commands on Telegram.

### Running with Docker Compose

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database
- Bot service
- Worker service

View logs:
```bash
docker-compose logs -f bot
docker-compose logs -f worker
```

Stop services:
```bash
docker-compose down
```

## Bot Commands

### User Commands

- `/start` - Start the bot and select a category
- Select category → Select period (7 or 30 days) → Browse requests with pagination

### Admin Commands

- `/status` - Show last parse log with metrics
- `/parse` - Trigger manual parsing job
- `/stats` - Show request counts by category

Admin commands are only available to users in `ADMIN_IDS`.

## Configuration

### Categories Configuration

Edit `config/chats.yaml` to configure:
- Available categories
- Telegram chats to parse for each category
- Parse interval and TTL settings

Example:
```yaml
categories:
  - name: "Web Development"
    slug: "web_dev"
    chats:
      - "@freelance_web"
      - "@web_jobs"
  - name: "Mobile Development"
    slug: "mobile"
    chats:
      - "@mobile_dev"
      - "@ios_jobs"

settings:
  parse_interval_hours: 2
  ttl_days: 30
  batch_size: 50
  request_delay_sec: 1.5
```

## Deployment on Railway

### Пошаговая инструкция

#### Шаг 1: Подготовка учётных данных

Перед деплоем тебе нужно получить:

1. **Telegram Bot Token** — от @BotFather в Telegram
2. **Telegram API ID и Hash** — на https://my.telegram.org/apps
3. **Gemini API Key** — на https://aistudio.google.com/app/apikeys
4. **Твой Telegram ID** — узнать можно у бота @userinfobot

#### Шаг 2: Создание проекта на Railway

1. Зайди на https://railway.app и авторизуйся через GitHub
2. Нажми **"New Project"**
3. Выбери **"Deploy from GitHub repo"**
4. Найди и выбери репозиторий `ai_freelance_tg`
5. Railway автоматически создаст первый сервис (это будет Bot)

#### Шаг 3: Добавление базы данных PostgreSQL

1. В проекте нажми **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway создаст базу данных и переменную `DATABASE_URL`

#### Шаг 4: Настройка сервиса Bot

1. Кликни на сервис, созданный из репозитория
2. Перейди во вкладку **"Variables"**
3. Добавь переменные:
   ```
   BOT_TOKEN=твой_токен_от_BotFather
   ADMIN_IDS=твой_telegram_id
   GEMINI_API_KEY=твой_ключ_gemini
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   ```
4. Во вкладке **"Settings"** проверь:
   - Build Command: оставь пустым (используется Dockerfile)
   - Dockerfile Path: `Dockerfile.bot`

#### Шаг 5: Создание сервиса Worker

1. В проекте нажми **"New"** → **"GitHub Repo"**
2. Выбери тот же репозиторий `ai_freelance_tg`
3. Переименуй сервис в "Worker" (клик на название → Edit)
4. Перейди во вкладку **"Variables"** и добавь:
   ```
   TELEGRAM_API_ID=твой_api_id
   TELEGRAM_API_HASH=твой_api_hash
   TELEGRAM_PHONE=+79001234567
   GEMINI_API_KEY=твой_ключ_gemini
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   ```
5. Во вкладке **"Settings"**:
   - Dockerfile Path: `Dockerfile.worker`
   - Start Command: `python -m worker.main`

#### Шаг 6: Деплой

1. Оба сервиса должны автоматически начать деплой
2. Следи за логами во вкладке **"Deployments"**
3. Если всё ок — бот заработает в Telegram!

### Проверка работы

1. Напиши боту `/start` в Telegram
2. Админ-команды: `/status`, `/parse`, `/stats`

### Возможные проблемы

**Bot не отвечает:**
- Проверь `BOT_TOKEN` в переменных
- Посмотри логи в Railway

**Worker падает:**
- Проверь `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`
- При первом запуске Telethon может запросить код подтверждения — это нужно делать локально

**Ошибка базы данных:**
- Убедись что `DATABASE_URL` ссылается на `${{Postgres.DATABASE_URL}}`

### Важно: Первый запуск Telethon

Telethon требует авторизации при первом запуске. Рекомендую:

1. Сначала запустить worker локально:
   ```bash
   python -m worker.main
   ```
2. Ввести код подтверждения из Telegram
3. Скопировать файл `*.session` в репозиторий
4. Добавить его в Git и запушить
5. После этого деплоить на Railway

## Testing

Run tests locally:

```bash
pytest
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

Run property-based tests:
```bash
pytest -v
```

## Project Structure

```
.
├── bot/                    # Telegram bot (aiogram)
│   ├── handlers/          # Command and callback handlers
│   ├── keyboards.py       # Inline keyboard builders
│   ├── middlewares.py     # Admin whitelist middleware
│   └── main.py            # Bot entry point
├── worker/                # Background worker (APScheduler)
│   ├── jobs/
│   │   ├── parser.py      # Telethon chat parser
│   │   └── analyzer.py    # Gemini AI analyzer
│   ├── scheduler.py       # APScheduler setup
│   ├── telethon_client.py # Telethon singleton
│   └── main.py            # Worker entry point
├── core/                  # Core utilities
│   ├── config.py          # Settings and config loading
│   ├── database.py        # SQLAlchemy async setup
│   └── models.py          # Database models
├── services/              # Business logic
│   ├── request_service.py # Request CRUD and stats
│   └── category_service.py # Category management
├── config/
│   └── chats.yaml         # Categories and chat configuration
├── tests/                 # Test suite
├── requirements.txt       # Python dependencies
├── Dockerfile.bot         # Bot container
├── Dockerfile.worker      # Worker container
├── docker-compose.yml     # Local development setup
├── railway.json           # Railway deployment config
└── README.md              # This file
```

## Troubleshooting

### Bot not responding

1. Check bot token is correct in `.env`
2. Verify bot is running: `python -m bot.main`
3. Check logs for errors

### Worker not parsing

1. Verify Telegram credentials (API ID, API hash, phone)
2. Check Gemini API key is valid
3. Verify database connection
4. Check logs: `docker-compose logs worker`

### Database connection errors

1. Ensure PostgreSQL is running
2. Verify `DATABASE_URL` format
3. Check database credentials

### Gemini API errors

1. Verify API key is valid
2. Check API quota hasn't been exceeded
3. Ensure API is enabled in Google Cloud Console

## Performance Considerations

- **Parse interval**: Default 2 hours. Increase to reduce API calls, decrease for fresher data
- **Batch size**: Default 50 messages per Gemini API call. Adjust based on API limits
- **TTL**: Default 30 days. Older requests are automatically deleted
- **Request delay**: Default 1.5 seconds between chats to avoid rate limiting

## License

MIT

## Support

For issues and questions, please open an issue on GitHub.
