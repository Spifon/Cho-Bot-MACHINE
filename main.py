import asyncio
import logging
import os
from threading import Thread

from flask import Flask, jsonify

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from config import BOT_TOKEN, GROQ_API_KEY, GROQ_MODEL, PORT


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("ChoVtoroi")


# ============================================================
# FLASK / RENDER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "☢️ Cho Второй 4.0 работает!"


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "bot": "Cho Второй 4.0"
    })


def run_web_server():
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )


# ============================================================
# TELEGRAM
# ============================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ============================================================
# START
# ============================================================

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "☢️ Cho Второй 4.0 запущен.\n\n"
        "Новая система постепенно активируется."
    )


# ============================================================
# HELP / COMMANDS
# ============================================================

@dp.message(Command("commands"))
@dp.message(Command("help"))
@dp.message(Command("?"))
async def commands_command(message: Message):
    await message.answer(
        "☢️ CHO ВТОРОЙ 4.0\n\n"
        "Основные команды:\n"
        "/start — запустить бота\n"
        "/commands — список команд\n"
        "/help — помощь\n"
        "/health — состояние системы\n\n"
        "🎮 Игры и другие системы будут подключены дальше."
    )


# ============================================================
# HEALTH
# ============================================================

@dp.message(Command("health"))
async def health_command(message: Message):
    await message.answer(
        "☢️ Система работает.\n"
        "Telegram: ✅\n"
        "Render: ✅\n"
        "AI: подготовка\n"
        "База данных: подготовка"
    )


# ============================================================
# MAIN
# ============================================================

async def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "❌ BOT_TOKEN не найден в Environment Variables."
        )

    if not GROQ_API_KEY:
        logger.warning(
            "⚠️ GROQ_API_KEY пока не установлен."
        )

    logger.info("☢️ Cho Второй 4.0 запускается...")
    logger.info("🎯 Модель: %s", GROQ_MODEL)

    # Удаляем старый webhook,
    # чтобы polling не конфликтовал с ним.
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("✅ Webhook очищен.")
    logger.info("🤖 Telegram polling запускается...")

    await dp.start_polling(bot)


def start():
    web_thread = Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    asyncio.run(main())


if __name__ == "__main__":
    start()
