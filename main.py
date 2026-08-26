import asyncio
import logging
from threading import Thread

from flask import Flask, jsonify

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from config import BOT_TOKEN, GROQ_API_KEY, GROQ_MODEL, PORT
from ai.groq import ask_groq


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
# /START
# ============================================================

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "☢️ Cho Второй 4.0 запущен.\n\n"
        "Новая система постепенно активируется."
    )


# ============================================================
# /COMMANDS / /HELP / /?
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
# /HEALTH
# ============================================================

@dp.message(Command("health"))
async def health_command(message: Message):
    await message.answer(
        "☢️ Система работает.\n\n"
        "Telegram: ✅\n"
        "Render: ✅\n"
        f"AI: {'✅' if GROQ_API_KEY else '❌'}\n"
        f"Модель: {GROQ_MODEL}\n"
        "База данных: ⏳"
    )


# ============================================================
# AI — ОБЫЧНЫЕ СООБЩЕНИЯ
# ============================================================

@dp.message()
async def ai_message(message: Message):

    # Игнорируем сообщения без текста
    if not message.text:
        return

    try:
        logger.info(
            "💬 Сообщение от %s: %s",
            message.from_user.id if message.from_user else "unknown",
            message.text
        )

        # Groq синхронный, поэтому запускаем его
        # в отдельном потоке, чтобы не блокировать Telegram.
        answer = await asyncio.to_thread(
            ask_groq,
            message.text
        )

        # Защита от пустого ответа
        if not answer or not answer.strip():
            logger.warning("⚠️ AI вернул пустой ответ.")
            return

        await message.answer(answer)

    except Exception as e:

        logger.error(
            "❌ AI ERROR: %s",
            e,
            exc_info=True
        )

        # Не отправляем пустое сообщение в Telegram.
        await message.answer(
            "☢️ Блядь... моё термоядерное ядро временно перегрелось."
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    # Проверяем Telegram-токен
    if not BOT_TOKEN:
        raise RuntimeError(
            "❌ BOT_TOKEN не найден в Environment Variables."
        )

    # Проверяем Groq
    if not GROQ_API_KEY:
        logger.warning(
            "⚠️ GROQ_API_KEY не найден."
        )

    logger.info(
        "☢️ Cho Второй 4.0 запускается..."
    )

    logger.info(
        "🎯 Выбрана модель: %s",
        GROQ_MODEL
    )

    # Удаляем webhook и старые ожидающие обновления.
    # Это предотвращает часть конфликтов между webhook/polling.
    await bot.delete_webhook(
        drop_pending_updates=True
    )

    logger.info(
        "✅ Webhook очищен."
    )

    logger.info(
        "🤖 Telegram polling запускается..."
    )

    # Запускаем получение сообщений
    await dp.start_polling(bot)


# ============================================================
# START PROGRAM
# ============================================================

def start():

    # Flask запускается отдельно,
    # чтобы Render видел работающий Web Service.
    web_thread = Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    # Запускаем Telegram-бота
    asyncio.run(main())


if __name__ == "__main__":
    start()
