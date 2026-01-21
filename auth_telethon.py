"""Script to authorize Telethon and create session file."""

import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")

async def main():
    print(f"Authorizing with phone: {PHONE}")
    
    client = TelegramClient("crypto_parser", API_ID, API_HASH)
    await client.start(phone=PHONE)
    
    me = await client.get_me()
    print(f"Authorized as: {me.first_name} (@{me.username})")
    print("Session file created: crypto_parser.session")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
