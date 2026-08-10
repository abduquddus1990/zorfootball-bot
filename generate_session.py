"""
BIR MARTALIK skript — FAQAT O'ZINGIZNING KOMPYUTERINGIZDA ishga tushiring.
Bu GitHub Actions ichida ISHLAMAYDI (chunki SMS kod so'raydi, interaktiv).

Ishlatish:
    pip install telethon
    python generate_session.py

So'raladi: api_id, api_hash (my.telegram.org'dan), telefon raqamingiz, SMS kod.
Natijada uzun "session string" chiqadi — shuni GitHub Secrets'dagi
TELEGRAM_SESSION nomiga qo'ying. Bu stringni HECH KIMGA, hech qanday
chatga (shu jumladan Claude'ga ham) yubormang — u akkauntingizga to'liq
kirish huquqini beradi.
"""

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("api_id: ").strip())
api_hash = input("api_hash: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n--- SESSION STRING (buni GitHub Secrets -> TELEGRAM_SESSION ga qo'ying) ---\n")
    print(client.session.save())
    print("\n--- Diqqat: bu stringni hech kimga bermang ---\n")
