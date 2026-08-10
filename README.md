# Telegram kanal-forward boti (tarjima bilan, yopiq kanallar uchun ham)

Manba Telegram kanalidagi (public YOKI private) postlarni o'zbek tiliga
Gemini yordamida tarjima qilib, rasmi bilan birga o'z kanalingizga
har 5 daqiqada avtomatik joylaydi.

## Nega userbot (Telethon) kerak?

Manba kanal yopiq (faqat taklifnoma havolasi bilan kiriladigan) bo'lgani
uchun oddiy Bot API yetarli emas — bot faqat o'zi admin bo'lgan
kanallardagi postlarni ko'ra oladi. Shuning uchun bu loyiha sizning
shaxsiy Telegram akkauntingiz nomidan ishlaydigan "userbot" ishlatadi
(faqat o'qish uchun, hech narsa yozmaydi, faqat yangi postlarni kuzatadi).

## 1. Repo yaratish

GitHub'da **PRIVATE** repo yarating (majburiy — bu loyihada nozik
maʼlumotlar bilan ishlaysiz) va shu papkadagi fayllarni yuklang.

## 2. api_id va api_hash olish

1. https://my.telegram.org ga o'z telefon raqamingiz bilan kiring.
2. **API development tools** → istalgan nom bilan ariza to'ldiring.
3. Sizga **api_id** (raqam) va **api_hash** (harf-raqamli) beriladi.

## 3. Session string generatsiya qilish (FAQAT o'zingizning kompyuteringizda!)

```bash
pip install telethon
python generate_session.py
```

Telefon raqamingiz va SMS kod so'raladi. Oxirida uzun bir "session string"
chiqadi. **Bu stringni hech kimga, hech qanday chatga (shu jumladan
Claude'ga ham) yubormang** — u akkauntingizga to'liq kirish huquqini beradi.
To'g'ridan-to'g'ri GitHub Secrets'ga qo'ying.

## 4. Telegram bot yaratish (maqsad kanalga joylash uchun)

1. **@BotFather** → `/newbot` → token oling.
2. Botni **maqsad kanalingizga admin** qilib qo'shing ("Post messages"
   huquqi bilan).

## 5. Gemini API kalitini olish

https://aistudio.google.com/apikey — mavjud Google akkauntingiz bilan
kiring, **"Create API key"** tugmasini bosing. Kalit odatda `AIzaSy...`
bilan boshlanadi — shaklini tekshirib oling.

## 6. GitHub Secrets qo'shish

Repo'da: **Settings → Secrets and variables → Actions → New repository secret**

| Nomi | Qiymati |
|---|---|
| `TELEGRAM_API_ID` | my.telegram.org'dan olingan api_id |
| `TELEGRAM_API_HASH` | my.telegram.org'dan olingan api_hash |
| `TELEGRAM_SESSION` | generate_session.py orqali olingan session string |
| `SOURCE_INVITE_LINK` | manba kanalning taklifnoma havolasi (https://t.me/+...) |
| `TELEGRAM_BOT_TOKEN` | BotFather'dan olingan token |
| `TELEGRAM_CHAT_ID` | maqsad kanal (@username yoki -100... ID) |
| `GEMINI_API_KEY` | Google AI Studio'dan olingan kalit |

## 7. Ishga tushirish

- Avtomatik: har 5 daqiqada.
- Qo'lda tekshirish: repo → **Actions** → **Forward channel posts** →
  **Run workflow**.
- **Birinchi ishga tushishda** eski postlar yubormaydi — faqat "hozirgi
  holat"ni belgilaydi. Shundan keyingi yangi postlar tarjima qilinib
  joylanadi.

## Xavfsizlik bo'yicha muhim eslatma

`TELEGRAM_SESSION` — bu amalda sizning Telegram akkountingizning "kaliti".
Uni faqat GitHub Secrets'da saqlang, hech qachon kodga yozib qo'ymang yoki
biror joyga (chat, fayl, skrinshot) yubormang. Agar tasodifan oshkor
bo'lib qolsa, Telegram sozlamalarida **Settings → Devices**'dan o'sha
sessiyani darhol tugating.

## Ishlash tezligi va xarajat

Eng qisqa jadval intervali — 5 daqiqa (ba'zida GitHub yuklamasi tufayli
1-3 daqiqa kechikishi mumkin). Sizning hajmingizda (kuniga bir necha
o'nlab post) bu GitHub Actions'ning bepul 2,000 daqiqalik oylik limitidan
juda oz qismini ishlatadi.
