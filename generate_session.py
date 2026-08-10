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
    session_string = client.session.save()

    with open("session.txt", "w", encoding="utf-8") as f:
        f.write(session_string)

    print("\n--- Session string 'session.txt' fayliga yozildi ---")
    print("--- Uni Notepad'da oching, Ctrl+A -> Ctrl+C qiling va GitHub Secrets'ga shu tarzda qo'ying ---")
    print("--- Diqqat: bu faylni hech kimga bermang, ishlatib bo'lgach o'chirib tashlang ---\n")
