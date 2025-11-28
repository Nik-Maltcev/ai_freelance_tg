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

### Quick Start

1. Fork this repository on GitHub
2. Go to https://railway.app
3. Create a new project
4. Connect your GitHub repository
5. Add PostgreSQL plugin
6. Set environment variables in Railway dashboard
7. Deploy!

### Environment Variables on Railway

Set these in the Railway dashboard:

- `BOT_TOKEN` - Your Telegram bot token
- `ADMIN_IDS` - Comma-separated admin user IDs
- `TELEGRAM_API_ID` - Your Telegram API ID
- `TELEGRAM_API_HASH` - Your Telegram API hash
- `TELEGRAM_PHONE` - Your Telegram phone number
- `GEMINI_API_KEY` - Your Google Gemini API key
- `DATABASE_URL` - Will be auto-set by Railway PostgreSQL plugin

### Deploying Worker on Railway

The `railway.json` is configured for the bot. To deploy the worker:

1. Create a second Railway project
2. Connect the same GitHub repository
3. Override the start command: `python -m worker.main`
4. Set the same environment variables
5. Deploy!

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
