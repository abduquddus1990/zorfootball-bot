"""
Manba Telegram kanalidan (yopiq bo'lsa ham) yangi postlarni oladi, Gemini orqali
o'zbek tiliga tarjima qiladi va o'z (maqsad) kanaliga rasm/video bilan birga joylaydi.

Kerakli environment o'zgaruvchilar (GitHub Secrets orqali beriladi):
  TELEGRAM_API_ID       - my.telegram.org'dan olingan api_id
  TELEGRAM_API_HASH     - my.telegram.org'dan olingan api_hash
  TELEGRAM_SESSION      - generate_session.py orqali mahalliy olingan session string
  SOURCE_INVITE_LINK    - manba kanalning taklifnoma havolasi (https://t.me/+... yoki https://t.me/kanal)
  TELEGRAM_BOT_TOKEN    - @BotFather'dan olingan bot tokeni (maqsad kanalga joylash uchun)
  TELEGRAM_CHAT_ID      - maqsad kanal ID'si yoki @username (bot admin bo'lishi shart)
  GEMINI_API_KEY        - Google AI Studio'dan olingan Gemini API kaliti
  GEMINI_MODEL          - (ixtiyoriy) standart: gemini-flash-latest
"""

import os
import re
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
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
GEMINI_API = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

PHOTO_CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096

# Har bir postning oxiriga qo'shiladigan o'z kanal reklamasi — manba
# kanalning o'z reklamasi (agar postda bo'lsa) shu bilan almashtiriladi.
FOOTER_LABEL = "ZO'RFUTBOL!"
CHANNEL_URL = "https://t.me/" + CHAT_ID.lstrip("@")

# Bitta post yuborilmasa, shuncha marta (har safar keyingi ishga tushishda)
# qayta urinib ko'radi. Shundan keyin ham bo'lmasa, dastur abadiy "qotib
# qolmasligi" uchun o'sha post o'tkazib yuboriladi.
MAX_RETRIES = 5


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(**kwargs):
    state = load_state()
    state.update(kwargs)
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def translate_uz(text):
    if not text:
        return ""
    prompt = (
        "Quyidagi matnni o'zbek tiliga tarjima qil. So'zma-so'z tarjima qilma — "
        "ma'noni saqlagan holda, tabiiy va ravon o'zbekcha uslubda qayta yoz. "
        "Hech qanday markdown belgilaridan (**, __, #, * va h.k.) foydalanma — "
        "faqat oddiy matn qaytar. Boshqa hech qanday izoh, sarlavha yoki tirnoq "
        "qo'shma:\n\n" + text
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
        log(f"Tarjimada xatolik: {e}")
        return text


def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def strip_source_footer(text):
    """Manba postining oxiridagi o'z reklama/obuna havolasini (t.me link) olib tashlaydi."""
    if not text:
        return text
    lines = text.rstrip().split("\n")
    while lines and re.search(r"https?://t\.me/\S+", lines[-1]):
        lines.pop()
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def build_message(translated, limit):
    """Tarjima qilingan matnni HTML uchun tayyorlaydi va oxiriga o'z kanal
    havolasini qo'shadi (markdown ** belgilari olib tashlanadi)."""
    footer = f'⚽️ <a href="{CHANNEL_URL}">{FOOTER_LABEL}</a>'
    body = escape_html(translated.replace("**", "").strip())
    max_body_len = max(limit - len(footer) - 2, 0)
    if len(body) > max_body_len:
        body = body[:max_body_len]
    return f"{body}\n\n{footer}" if body else footer


def send_photo_bytes(image_bytes, caption):
    resp = requests.post(
        f"{TELEGRAM_API}/sendPhoto",
        data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
        files={"photo": ("image.jpg", image_bytes)},
        timeout=120,
    )
    if not resp.ok:
        log(f"sendPhoto xato: {resp.text}")
    return resp.ok


def send_video_bytes(video_bytes, caption):
    resp = requests.post(
        f"{TELEGRAM_API}/sendVideo",
        data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
        files={"video": ("video.mp4", video_bytes)},
        timeout=180,
    )
    if not resp.ok:
        log(f"sendVideo xato: {resp.text}")
    return resp.ok


def send_text(text):
    resp = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=30,
    )
    if not resp.ok:
        log(f"sendMessage xato: {resp.text}")
    return resp.ok


def send_media_group(items, caption):
    """items: [("photo"|"video", BytesIO), ...] — 2 tadan ortiq bo'lsa albom."""
    media = []
    files = {}
    for i, (kind, buf) in enumerate(items):
        name = f"file{i}"
        media.append({"type": kind, "media": f"attach://{name}"})
        files[name] = (f"{name}.mp4" if kind == "video" else f"{name}.jpg", buf)
    if caption:
        media[0]["caption"] = caption
        media[0]["parse_mode"] = "HTML"

    resp = requests.post(
        f"{TELEGRAM_API}/sendMediaGroup",
        data={"chat_id": CHAT_ID, "media": json.dumps(media)},
        files=files,
        timeout=180,
    )
    if not resp.ok:
        log(f"sendMediaGroup xato: {resp.text}")
    return resp.ok


def resolve_source_entity(client):
    link = SOURCE_INVITE_LINK.strip()
    try:
        if "/+" in link or "joinchat" in link:
            invite_hash = link.split("+")[-1].split("/")[-1]
            try:
                updates = client(ImportChatInviteRequest(invite_hash))
                return updates.chats[0]
            except UserAlreadyParticipantError:
                invite = client(CheckChatInviteRequest(invite_hash))
                return invite.chat
        else:
            username = link.rstrip("/").split("/")[-1].lstrip("@")
            return client.get_entity(username)
    except InviteHashExpiredError:
        log("Taklifnoma havolasi muddati tugagan — yangisini SOURCE_INVITE_LINK'ga qo'ying.")
        sys.exit(1)
    except Exception as e:
        log(f"Manba kanalga ulanishda xatolik: {e}")
        sys.exit(1)


def group_messages(messages):
    """Ketma-ket kelgan, bitta albomga tegishli (grouped_id bir xil)
    xabarlarni birlashtiradi — bo'lmasa har biri o'z holicha 1 elementli guruh."""
    groups = []
    current = []
    current_gid = None
    for m in messages:
        if m.grouped_id is not None and m.grouped_id == current_gid:
            current.append(m)
        else:
            if current:
                groups.append(current)
            current = [m]
            current_gid = m.grouped_id
    if current:
        groups.append(current)
    return groups


def send_group(client, group):
    """Bitta post (yoki albom)ni yuboradi. Muvaffaqiyatli bo'lsa True qaytaradi."""
    text = next((m.text for m in group if m.text), "") or ""
    text = strip_source_footer(text)
    translated = translate_uz(text)

    if len(group) > 1:
        items = []
        for m in group:
            if not (m.photo or m.video):
                log(f"Albomda qo'llab-quvvatlanmaydigan media turi (ID={m.id}) — butun albom o'tkazib yuborildi.")
                return False
            buf = io.BytesIO()
            client.download_media(m, file=buf)
            buf.seek(0)
            items.append(("video" if m.video else "photo", buf))
        return send_media_group(items, build_message(translated, PHOTO_CAPTION_LIMIT))

    msg = group[0]
    if msg.photo:
        buf = io.BytesIO()
        client.download_media(msg, file=buf)
        buf.seek(0)
        return send_photo_bytes(buf, build_message(translated, PHOTO_CAPTION_LIMIT))
    if msg.video:
        buf = io.BytesIO()
        client.download_media(msg, file=buf)
        buf.seek(0)
        return send_video_bytes(buf, build_message(translated, PHOTO_CAPTION_LIMIT))
    if not translated.strip():
        return True  # bo'sh/qo'llab-quvvatlanmaydigan xabar — shunchaki o'tkazib yuboriladi
    return send_text(build_message(translated, TEXT_LIMIT))


def main():
    with TelegramClient(StringSession(SESSION), API_ID, API_HASH) as client:
        entity = resolve_source_entity(client)
        state = load_state()

        if state.get("channel_id") != entity.id:
            log("Manba kanal o'zgardi (yoki birinchi marta ishga tushdi) — holat qayta boshlanmoqda.")
            latest = client.get_messages(entity, limit=1)
            save_state(
                channel_id=entity.id,
                last_id=latest[0].id if latest else 0,
                fail_msg_id=None,
                fail_count=0,
            )
            return

        last_id = state.get("last_id")
        new_messages = list(client.iter_messages(entity, min_id=last_id, reverse=True))

        if not new_messages:
            log("Yangi post yo'q.")
            return

        posted_count = 0
        for group in group_messages(new_messages):
            group_id = group[-1].id
            ok = send_group(client, group)

            if ok:
                posted_count += 1
                save_state(last_id=group_id, fail_msg_id=None, fail_count=0)
                time.sleep(2)
                continue

            fail_count = state.get("fail_count", 0) + 1 if state.get("fail_msg_id") == group_id else 1
            state["fail_msg_id"] = group_id
            state["fail_count"] = fail_count
            save_state(fail_msg_id=group_id, fail_count=fail_count)

            if fail_count >= MAX_RETRIES:
                log(f"Post (ID={group_id}) {MAX_RETRIES} marta urinishdan keyin ham yuborilmadi — o'tkazib yuborildi.")
                save_state(last_id=group_id, fail_msg_id=None, fail_count=0)
                continue

            log(f"Post (ID={group_id}) yuborilmadi ({fail_count}/{MAX_RETRIES} urinish) — keyingi ishga tushishda qayta uriniladi.")
            break

        log(f"{posted_count} ta yangi post joylandi.")


if __name__ == "__main__":
    main()
