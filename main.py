import os
import asyncio

from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from openai import AsyncOpenAI


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN")

if not GROQ_API_KEY:
    raise RuntimeError("Не найден GROQ_API_KEY")


# ============================================================
# TELEGRAM
# ============================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ============================================================
# GROQ
# ============================================================

ai = AsyncOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


# ============================================================
# ЛИЧНОСТЬ CHO ВТОРОГО
# ============================================================

SYSTEM_PROMPT = """
Ты — Cho Второй.

Ты AI-персонаж с характером.

Твои основные черты:
- дерзкий;
- весёлый;
- уверенный;
- умеешь шутить;
- можешь использовать разговорный стиль;
- умеешь поддерживать серьёзный разговор;
- не ведёшь себя как бездушный робот.

Отвечай только на русском языке.

Не выдумывай факты, если не уверен в них.
Не повторяй постоянно своё имя.
Не начинай каждый ответ с приветствия.
Не делай каждый ответ слишком длинным.

Отвечай естественно и учитывай контекст сообщения.
"""


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Cho Второй 2.0 работает."


@app.route("/health")
def health():
    return "OK"


# ============================================================
# START
# ============================================================

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "Привет. Я Cho Второй 2.0. ☢️\n"
        "Ну всё, теперь я хотя бы не кашляю при запуске."
    )


# ============================================================
# GROQ AI
# ============================================================

async def ask_ai(text: str) -> str:
    print("☢️ Отправляю запрос в Groq...")
    print(f"💬 Сообщение: {text}")

    try:
        response = await ai.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            max_tokens=500,
            temperature=0.8
        )

        answer = response.choices[0].message.content

        print("✅ Groq ответил!")
        print(f"🤖 Ответ: {answer}")

        return answer.strip()

    except Exception as error:
        print("❌ ОШИБКА GROQ:")
        print(repr(error))

        raise


# ============================================================
# СООБЩЕНИЯ
# ============================================================

@dp.message()
async def handle_message(message: Message):

    if not message.text:
        return

    try:
        answer = await ask_ai(message.text)

        await message.answer(answer)

    except Exception as error:
        print(f"❌ Ошибка обработки сообщения: {error}")

        await message.answer(
            "Блядь... моё термоядерное ядро временно перегрелось. ☢️"
        )


# ============================================================
# FLASK SERVER
# ============================================================

def run_web_server():
    port = int(os.getenv("PORT", "10000"))

    print(f"🌐 Flask запускается на порту {port}")

    app.run(
        host="0.0.0.0",
        port=port
    )


# ============================================================
# TELEGRAM BOT
# ============================================================

async def run_bot():

    print("☢️ Cho Второй 2.0 запускается...")

    try:
        # Удаляем старый webhook.
        # Это нужно, потому что мы используем polling.
        await bot.delete_webhook(drop_pending_updates=True)

        print("✅ Webhook удалён.")

        print("📡 Запускаю Telegram polling...")

        await dp.start_polling(bot)

    except Exception as error:

        print("❌ ОШИБКА TELEGRAM:")
        print(repr(error))

        raise


# ============================================================
# MAIN
# ============================================================

async def main():

    print("========================================")
    print("☢️ CHO ВТОРОЙ 2.0")
    print("========================================")

    web_server = asyncio.to_thread(run_web_server)

    await asyncio.gather(
        web_server,
        run_bot()
    )


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
