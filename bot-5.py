import logging
import os
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from dotenv import load_dotenv
from pdf_generator import create_pdf

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "8297534017:AAHZLSpK2fKUwhDOwC7GFhQgmAyVdRT-6e4"
GROQ_API_KEY = "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"

user_sessions = {}

def ask_claude(prompt):
    """Groq API ga requests orqali murojaat"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=120
    )
    result = response.json()
    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    elif "error" in result:
        raise Exception(f"API xato: {result['error']['message']}")
    else:
        raise Exception(f"Noma'lum javob: {str(result)[:200]}")

PROMPTS = {
    "slayd": """Sen tajribali o'qituvchi va prezentatsiya mutaxassisisin. Quyidagi mavzu bo'yicha o'zbek tilida 10 ta slayd uchun to'liq kontent tayyorla.

Mavzu: {topic}

Format:
SLAYD 1: SARLAVHA SLAYD
Mavzu: {topic}

SLAYD 2: KIRISH
• [nuqta 1]
• [nuqta 2]
• [nuqta 3]

(shu tarzda 10 ta slayd)

SLAYD 10: XULOSA VA SAVOLLAR
[Xulosa matni]""",

    "mustaqil": """Sen tajribali akademik yozuvchisan. Quyidagi mavzu bo'yicha o'zbek tilida to'liq mustaqil ish yaz.

Mavzu: {topic}

MUNDARIJA

KIRISH
- Mavzuning dolzarbligi
- Ishning maqsadi va vazifalari

BOB I. NAZARIY ASOSLAR
1.1. [Birinchi bo'lim]
1.2. [Ikkinchi bo'lim]

BOB II. ASOSIY TAHLIL
2.1. [Birinchi tahlil]
2.2. [Ikkinchi tahlil]

XULOSA

FOYDALANILGAN ADABIYOTLAR
1. [Manba]
2. [Manba]
3. [Manba]

Har bo'lim kamida 200-300 so'z bo'lsin.""",

    "kurs": """Sen tajribali akademik yozuvchisan. Quyidagi mavzu bo'yicha o'zbek tilida to'liq kurs ishi yoz.

Mavzu: {topic}

MUNDARIJA

KIRISH
- Tadqiqotning dolzarbligi
- Tadqiqotning maqsadi
- Tadqiqotning vazifalari
- Tadqiqot ob'ekti va predmeti

BOB I. NAZARIY-METODOLOGIK ASOSLAR
1.1. {topic} tushunchasi va mohiyati
1.2. {topic} ning rivojlanish tarixi
1.3. Xorijiy va mahalliy tadqiqotlar tahlili

BOB II. ZAMONAVIY HOLAT VA TAHLIL
2.1. Hozirgi holat tahlili
2.2. Asosiy muammolar
2.3. Misollar va faktlar

BOB III. TAKOMILLASHTIRISH YO'LLARI
3.1. Xorijiy tajriba
3.2. Tavsiyalar va takliflar

XULOSA

FOYDALANILGAN ADABIYOTLAR

Har bob kamida 400-500 so'z. Akademik uslubda.""",

    "insho": """Sen iste'dodli yozuvchisan. Quyidagi mavzu bo'yicha o'zbek tilida chiroyli insho yoz.

Mavzu: {topic}

KIRISH
(Diqqat tortuvchi bosh gap)

ASOSIY QISM
(3-4 xat boshi, dalillar va misollar bilan)

XULOSA
(Kuchli yakuniy fikr)

Kamida 400-500 so'z.""",

    "krossvord": """Sen krossvord muallifisin. Quyidagi mavzu bo'yicha 15 ta savol asosida krossvord tayyorla.

Mavzu: {topic}

KROSSVORD: {topic}

GORIZONTAL:
1. [Savol] — Javob: [SO'Z]
2. [Savol] — Javob: [SO'Z]
3. [Savol] — Javob: [SO'Z]
4. [Savol] — Javob: [SO'Z]
5. [Savol] — Javob: [SO'Z]
6. [Savol] — Javob: [SO'Z]
7. [Savol] — Javob: [SO'Z]
8. [Savol] — Javob: [SO'Z]

VERTIKAL:
9. [Savol] — Javob: [SO'Z]
10. [Savol] — Javob: [SO'Z]
11. [Savol] — Javob: [SO'Z]
12. [Savol] — Javob: [SO'Z]
13. [Savol] — Javob: [SO'Z]
14. [Savol] — Javob: [SO'Z]
15. [Savol] — Javob: [SO'Z]

JAVOBLAR: 1.SO'Z 2.SO'Z 3.SO'Z ...""",

    "test": """Sen tajribali o'qituvchisan. Quyidagi mavzu bo'yicha 20 ta test savoli tuz.

Mavzu: {topic}

7 ta oson, 8 ta o'rta, 5 ta qiyin savol.

Format:
1. [Savol]
A) [variant]
B) [variant]
C) [variant]
D) [variant]
To'g'ri javob: [A/B/C/D]

---""",

    "flashcard": """Quyidagi mavzu bo'yicha 20 ta flashcard tayyorla.

Mavzu: {topic}

KARTOCHKA 1
SAVOL: [savol]
JAVOB: [javob]
MASLAHAT: [eslab qolish usuli]

---""",

    "maqola": """Quyidagi mavzu bo'yicha ilmiy-ommabop maqola yoz.

Mavzu: {topic}

SARLAVHA: [sarlavha]
ANNOTATSIYA: [qisqa]
KIRISH
ASOSIY QISM
XULOSA
ADABIYOTLAR

Kamida 600 so'z.""",

    "tezis": """Quyidagi mavzu bo'yicha ilmiy tezis yarat.

Mavzu: {topic}

ASOSIY TEZIS
TADQIQOT SAVOLLARI
ASOSIY ARGUMENTLAR
DALILLAR
XULOSA TEZISI""",

    "dars_rejasi": """Quyidagi mavzu bo'yicha to'liq dars rejasi tayyorla.

Mavzu: {topic}

DARS REJASI
Muddat: 45 daqiqa

1. TASHKILIY QISM (5 daqiqa)
2. TAKRORLASH (10 daqiqa)
3. YANGI MAVZU (20 daqiqa)
4. MUSTAHKAMLASH (7 daqiqa)
5. BAHOLASH (3 daqiqa)
UY VAZIFASI""",

    "rezyume": """Quyidagi ma'lumotlar asosida professional rezyume tayyorla.

Ma'lumot: {topic}

REZYUME
SHAXSIY MA'LUMOTLAR
KASBIY MAQSAD
ISH TAJRIBASI
TA'LIM
KO'NIKMALAR
TILLAR
YUTUQLAR""",

    "podkast": """Quyidagi mavzu bo'yicha podkast skriptini yoz.

Mavzu: {topic}

PODKAST: {topic}
Davomiylik: 20 daqiqa

INTRO
QISM 1
QISM 2
QISM 3
AMALIY MASLAHATLAR
OUTRO""",

    "tabrik": """Quyidagi ma'lumotlar asosida tabriknoma yoz.

Ma'lumot: {topic}

VARIANT 1 — RASMIY:
[matn]

VARIANT 2 — SAMIMIY:
[matn]

VARIANT 3 — QIZIQARLI:
[matn]

SMS VARIANT:
[qisqa]""",

    "rasm": """Quyidagi mavzu uchun AI rasm prompti yarat.

Mavzu: {topic}

O'ZBEKCHA TAVSIF:
[tavsif]

ASOSIY PROMPT (inglizcha):
[prompt]

VARIANT 1 — FOTOREALISTIK:
[prompt]

VARIANT 2 — RASM USLUBI:
[prompt]

NEGATIVE PROMPT:
[prompt]"""
}

MENU_LABELS = {
    "slayd": "📊 Slayd yaratish",
    "mustaqil": "📝 Mustaqil ish/Referat",
    "kurs": "📚 Kurs ishi",
    "insho": "✍️ Insho",
    "krossvord": "🔤 Krossvord",
    "test": "❓ Test (20 ta savol)",
    "flashcard": "🃏 Flashcard",
    "maqola": "📰 Maqola",
    "tezis": "📌 Tezis",
    "dars_rejasi": "📋 Dars rejasi",
    "rezyume": "📄 Rezyume",
    "podkast": "🎙️ Podkast skripti",
    "tabrik": "🎉 Tabriknoma",
    "rasm": "🎨 Rasm prompti",
}

HINTS = {
    "slayd": "Masalan: Fotosintez | O'zbekiston tarixi",
    "mustaqil": "Masalan: Globallashuv va iqtisodiyot",
    "kurs": "Masalan: Sun'iy intellektning ta'limdagi o'rni",
    "insho": "Masalan: Kitob o'qishning foydasi",
    "krossvord": "Masalan: Biologiya | Matematika",
    "test": "Masalan: Kimyo elementlari | Fizika",
    "flashcard": "Masalan: Ingliz tili so'zlari",
    "maqola": "Masalan: Yoshlarning rivojlanishi",
    "tezis": "Masalan: Ta'limdagi texnologiyalar",
    "dars_rejasi": "Masalan: 7-sinf, Algebra",
    "rezyume": "Masalan: Dasturchi, 3 yil tajriba",
    "podkast": "Masalan: Sog'lom turmush tarzi",
    "tabrik": "Masalan: Do'stim Alining 20 yoshi",
    "rasm": "Masalan: Bahorgi Samarqand",
}

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Slayd", callback_data="slayd"),
         InlineKeyboardButton("📝 Mustaqil ish", callback_data="mustaqil")],
        [InlineKeyboardButton("📚 Kurs ishi", callback_data="kurs"),
         InlineKeyboardButton("✍️ Insho", callback_data="insho")],
        [InlineKeyboardButton("🔤 Krossvord", callback_data="krossvord"),
         InlineKeyboardButton("❓ Test", callback_data="test")],
        [InlineKeyboardButton("🃏 Flashcard", callback_data="flashcard"),
         InlineKeyboardButton("📰 Maqola", callback_data="maqola")],
        [InlineKeyboardButton("📌 Tezis", callback_data="tezis"),
         InlineKeyboardButton("📋 Dars rejasi", callback_data="dars_rejasi")],
        [InlineKeyboardButton("📄 Rezyume", callback_data="rezyume"),
         InlineKeyboardButton("🎙️ Podkast", callback_data="podkast")],
        [InlineKeyboardButton("🎉 Tabriknoma", callback_data="tabrik"),
         InlineKeyboardButton("🎨 Rasm prompti", callback_data="rasm")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Salom, {user.first_name}!\n\n"
        "🤖 Men ta'lim materiallari yaratuvchi AI botman.\n"
        "📄 Barcha materiallar PDF formatda yuklab beriladi!\n\n"
        "📚 Bo'limni tanlang:",
        reply_markup=main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    user_id = query.from_user.id

    if action == "back_menu":
        await query.edit_message_text(
            "📚 Bo'limni tanlang:",
            reply_markup=main_menu_keyboard()
        )
        return

    if action in PROMPTS:
        user_sessions[user_id] = {"action": action}
        label = MENU_LABELS.get(action, action)
        hint = HINTS.get(action, "")
        await query.edit_message_text(
            f"{label} tanlandi!\n\n"
            f"Mavzuni yozing:\n"
            f"Masalan: {hint}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Orqaga", callback_data="back_menu")]
            ])
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    topic = update.message.text.strip()

    if user_id not in user_sessions or not user_sessions[user_id].get("action"):
        await update.message.reply_text(
            "Iltimos, /start bosing.",
            reply_markup=main_menu_keyboard()
        )
        return

    action = user_sessions[user_id]["action"]
    label = MENU_LABELS.get(action, action)

    progress_msg = await update.message.reply_text(
        f"Tayyorlanmoqda: {label}\n"
        f"Mavzu: {topic}\n"
        f"20-40 soniya kuting..."
    )

    try:
        prompt = PROMPTS[action].format(topic=topic)
        content = ask_claude(prompt)

        await progress_msg.edit_text("Matn tayyor! PDF tayyorlanmoqda...")

        safe_topic = re.sub(r'[^\w\s-]', '', topic)[:25].strip().replace(' ', '_')
        filename = f"{action}_{safe_topic}.pdf"

        pdf_path = create_pdf(content, filename, topic, label)

        with open(pdf_path, 'rb') as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=filename,
                caption=f"{label} tayyor!\nMavzu: {topic}"
            )

        await progress_msg.delete()

        try:
            os.remove(pdf_path)
        except:
            pass

        await update.message.reply_text(
            "Yana biror narsa kerakmi?",
            reply_markup=main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Xato: {e}")
        await progress_msg.edit_text(f"Xatolik: {str(e)[:100]}\nQaytadan urinib ko'ring.")
        await update.message.reply_text(
            "Bo'limni qaytadan tanlang:",
            reply_markup=main_menu_keyboard()
        )
    finally:
        user_sessions.pop(user_id, None)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
