import asyncio
import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

# ============ SOZLAMALAR ============
# Railway'da "Variables" bo'limiga BOT_TOKEN nomi bilan tokenni kiritasiz.
# Agar mahalliy kompyuterda sinamoqchi bo'lsangiz, pastdagi "yoki" qismidagi
# tokenni ishlating.
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "8978959722:AAF39wYJJ2ZcbOO1NGbXClNs3krsg8yFq6k"
ADMIN_IDS = [8241969249]                      # Jaloliddin - admin
DB_PATH = os.environ.get("DB_PATH", "movies.db")
# =====================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            title TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()


def add_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def get_users_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_movies_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM movies")
    count = cur.fetchone()[0]
    conn.close()
    return count


def save_movie(code: str, file_id: str, title: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO movies (code, file_id, title) VALUES (?, ?, ?)",
        (code, file_id, title),
    )
    conn.commit()
    conn.close()


def get_movie(code: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT file_id, title FROM movies WHERE code = ?", (code,))
    row = cur.fetchone()
    conn.close()
    return row


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ------------- /start -------------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    add_user(message.from_user.id)
    await message.answer(
        "Salom! 🎬\n\n"
        "Film kodini yuboring, men sizga filmni topib beraman.\n"
        "Masalan: <b>001</b>",
        parse_mode="HTML",
    )


# ------------- /stats (faqat admin uchun) -------------
@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id):
        return

    users_count = get_users_count()
    movies_count = get_movies_count()

    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👤 Foydalanuvchilar soni: <b>{users_count}</b>\n"
        f"🎬 Filmlar soni: <b>{movies_count}</b>",
        parse_mode="HTML",
    )


# ------------- Admin: video yuborib, keyin kod berish -------------
# Admin avval videoni botga forward/yuboradi, bot file_id ni saqlab qo'yadi
# so'ng caption sifatida kod yozadi: masalan caption = "001 Fast and Furious"

@dp.message(F.video)
async def handle_video(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Kechirasiz, faqat admin video qo'sha oladi.")
        return

    caption = message.caption
    if not caption:
        await message.answer(
            "Video qabul qilindi, lekin kod berilmadi.\n"
            "Videoni caption bilan yuboring, masalan:\n"
            "<code>001 Titanik</code>",
            parse_mode="HTML",
        )
        return

    parts = caption.strip().split(maxsplit=1)
    code = parts[0]
    title = parts[1] if len(parts) > 1 else ""

    file_id = message.video.file_id
    save_movie(code, file_id, title)

    await message.answer(f"✅ Film saqlandi!\nKod: <b>{code}</b>\nNomi: {title or '—'}", parse_mode="HTML")


# ------------- Foydalanuvchi: kod yuboradi -------------
@dp.message(F.text)
async def handle_code(message: Message):
    add_user(message.from_user.id)
    code = message.text.strip()
    row = get_movie(code)

    if row is None:
        await message.answer("❌ Bunday kodli film topilmadi. Kodni tekshirib qayta yuboring.")
        return

    file_id, title = row
    caption = title if title else f"Kod: {code}"
    await message.answer_video(video=file_id, caption=caption)


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
