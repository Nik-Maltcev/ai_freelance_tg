"""Authorize Telethon via QR code."""

import asyncio
import qrcode
from telethon import TelegramClient
from telethon.tl.functions.auth import ExportLoginTokenRequest, ImportLoginTokenRequest
from telethon.tl.types import auth
from dotenv import load_dotenv
import os
import base64

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

async def main():
    print("QR Code Authorization")
    print("=" * 40)
    
    client = TelegramClient("crypto_parser", API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Already authorized as: {me.first_name}")
        await client.disconnect()
        return
    
    # Request QR login token
    qr_login = await client(ExportLoginTokenRequest(
        api_id=API_ID,
        api_hash=API_HASH,
        except_ids=[]
    ))
    
    # Generate QR code
    token_url = f"tg://login?token={base64.urlsafe_b64encode(qr_login.token).decode('utf-8').rstrip('=')}"
    
    qr = qrcode.QRCode(version=1, box_size=2, border=1)
    qr.add_data(token_url)
    qr.make(fit=True)
    
    print("\nScan this QR code with Telegram on your phone:")
    print("(Settings → Devices → Link Desktop Device)\n")
    qr.print_ascii(invert=True)
    
    print("\nWaiting for authorization...")
    
    # Wait for user to scan
    while True:
        await asyncio.sleep(2)
        try:
            qr_login = await client(ExportLoginTokenRequest(
                api_id=API_ID,
                api_hash=API_HASH,
                except_ids=[]
            ))
            
            if isinstance(qr_login, auth.LoginTokenSuccess):
                break
            elif isinstance(qr_login, auth.LoginTokenMigrateTo):
                # Need to reconnect to another DC
                await client._switch_dc(qr_login.dc_id)
                qr_login = await client(ImportLoginTokenRequest(qr_login.token))
                if isinstance(qr_login, auth.LoginTokenSuccess):
                    break
        except Exception as e:
            if "TIMEOUT" in str(e) or "expired" in str(e).lower():
                print("QR expired, generating new one...")
                qr_login = await client(ExportLoginTokenRequest(
                    api_id=API_ID,
                    api_hash=API_HASH,
                    except_ids=[]
                ))
                token_url = f"tg://login?token={base64.urlsafe_b64encode(qr_login.token).decode('utf-8').rstrip('=')}"
                qr = qrcode.QRCode(version=1, box_size=2, border=1)
                qr.add_data(token_url)
                qr.make(fit=True)
                qr.print_ascii(invert=True)
            else:
                raise
    
    me = await client.get_me()
    print(f"\n✅ Authorized as: {me.first_name} (@{me.username})")
    print("Session file created: crypto_parser.session")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
