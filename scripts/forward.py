"""
Manba Telegram kanalidan (yopiq bo'lsa ham) yangi postlarni oladi, Gemini orqali
o'zbek tiliga tarjima qiladi va o'z (maqsad) kanaliga rasm bilan birga joylaydi.

Kerakli environment o'zgaruvchilar (GitHub Secrets orqali beriladi):
  TELEGRAM_API_ID       - my.telegram.org'dan olingan api_id
  TELEGRAM_API_HASH     - my.telegram.org'dan olingan api_hash
  TELEGRAM_SESSION      - generate_session.py orqali mahalliy olingan session string
  SOURCE_INVITE_LINK    - manba kanalning taklifnoma havolasi (https://t.me/+... yoki https://t.me/kanal)
  TELEGRAM_BOT_TOKEN    - @BotFather'dan olingan bot tokeni (maqsad kanalga joylash uchun)
  TELEGRAM_CHAT_ID      - maqsad kanal ID'si yoki @username (bot admin bo'lishi shart)
  GEMINI_API_KEY        - Google AI Studio'dan olingan Gemini API kaliti
  GEMINI_MODEL          - (ixtiyoriy) standart: gemini-2.0-flash
"""

import os
import sys
import io
import json
import time
import requests

from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.errors import UserAlreadyParticipantError, InviteHashExpiredError

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state", "last_id.json")

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION = os.environ["TELEGRAM_SESSION"]
SOURCE_INVITE_LINK = os.environ["SOURCE_INVITE_LINK"]

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
GEMINI_API = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

PHOTO_CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


def load_last_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("last_id")
    return None


def save_last_id(msg_id):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_id": msg_id}, f, ensure_ascii=False, indent=2)


def translate_uz(text):
    if not text:
        return ""
    prompt = (
        "Quyidagi matnni o'zbek tiliga tarjima qil. So'zma-so'z tarjima qilma — "
        "ma'noni saqlagan holda, tabiiy va ravon o'zbekcha uslubda qayta yoz. "
        "Faqat tarjima qilingan matnni qaytar, boshqa hech qanday izoh, sarlavha "
        "yoki tirnoq qo'shma:\n\n" + text
    )
    try:
        resp = requests.post(
            GEMINI_API,
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"Tarjimada xatolik: {e}", file=sys.stderr)
        return text


def send_photo_bytes(image_bytes, caption):
    caption = caption[:PHOTO_CAPTION_LIMIT]
    resp = requests.post(
        f"{TELEGRAM_API}/sendPhoto",
        data={"chat_id": CHAT_ID, "caption": caption},
        files={"photo": ("image.jpg", image_bytes)},
        timeout=60,
    )
    if not resp.ok:
        print(f"sendPhoto xato: {resp.text}", file=sys.stderr)
    return resp.ok


def send_text(text):
    text = text[:TEXT_LIMIT] or "(bo'sh post)"
    resp = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=30,
    )
    if not resp.ok:
        print(f"sendMessage xato: {resp.text}", file=sys.stderr)
    return resp.ok


def resolve_source_entity(client):
    link = SOURCE_INVITE_LINK.strip()
    if "/+" in link or "joinchat" in link:
        invite_hash = link.split("+")[-1].split("/")[-1]
        try:
            updates = client(ImportChatInviteRequest(invite_hash))
            return updates.chats[0]
        except UserAlreadyParticipantError:
            invite = client(CheckChatInviteRequest(invite_hash))
            return invite.chat
        except InviteHashExpiredError:
            print("Taklifnoma havolasi muddati tugagan — yangisini oling.", file=sys.stderr)
            sys.exit(1)
    else:
        # oddiy public username havola/nomi
        username = link.rstrip("/").split("/")[-1].lstrip("@")
        return client.get_entity(username)


def main():
    with TelegramClient(StringSession(SESSION), API_ID, API_HASH) as client:
        entity = resolve_source_entity(client)
        last_id = load_last_id()

        if last_id is None:
            # birinchi marta — eski postlarni spam qilmaslik uchun faqat holatni belgilaymiz
            latest = client.get_messages(entity, limit=1)
            if latest:
                save_last_id(latest[0].id)
            print("Birinchi marta ishga tushdi — holat saqlandi, eski postlar o'tkazib yuborildi.")
            return

        new_messages = list(client.iter_messages(entity, min_id=last_id, reverse=True))

        if not new_messages:
            print("Yangi post yo'q.")
            return

        posted_count = 0
        for msg in new_messages:
            text = msg.text or ""
            translated = translate_uz(text)

            if msg.photo:
                buf = io.BytesIO()
                client.download_media(msg, file=buf)
                buf.seek(0)
                ok = send_photo_bytes(buf, translated)
            else:
                if not translated.strip():
                    save_last_id(msg.id)
                    continue
                ok = send_text(translated)

            if ok:
                posted_count += 1
                save_last_id(msg.id)
                time.sleep(2)
            else:
                break

        print(f"{posted_count} ta yangi post joylandi.")


if __name__ == "__main__":
    main()
