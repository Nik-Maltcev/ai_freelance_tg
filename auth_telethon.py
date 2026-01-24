"""Script to authorize Telethon and create session file."""

import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")

async def main():
    print(f"Authorizing with phone: {PHONE}")
    print("Code will be sent to your Telegram app (check 'Telegram' chat)")
    print("If no code in app, it will call you - last digits = code")
    print()
    
    client = TelegramClient("crypto_parser", API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        await client.send_code_request(PHONE)
        
        code = input("Enter the code you received: ")
        
        try:
            await client.sign_in(PHONE, code)
        except SessionPasswordNeededError:
            password = input("Two-factor auth enabled. Enter password: ")
            await client.sign_in(password=password)
    
    me = await client.get_me()
    print(f"\nAuthorized as: {me.first_name} (@{me.username})")
    print("Session file created: crypto_parser.session")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
