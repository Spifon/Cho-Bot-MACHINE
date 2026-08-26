import os
import asyncio

from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from openai import AsyncOpenAI


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL = "llama-3.1-8b-instant"


if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден в Environment Variables")

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY не найден в Environment Variables")


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
# CHO PERSONALITY
# ============================================================

SYSTEM_PROMPT = """
Ты — Cho Второй.

Ты AI-персонаж с характером.

Характер:
- дерзкий;
- весёлый;
- уверенный;
- иногда саркастичный;
- умеешь шутить;
- умеешь вести серьёзный разговор;
- не ведёшь себя как бездушный робот.

Правила:
- отвечай на русском языке;
- отвечай естественно;
- учитывай сообщение пользователя;
- не повторяй постоянно своё имя;
- не начинай каждый ответ с приветствия;
- не выдумывай факты, если не уверен;
- не делай ответы unnecessarily длинными.

Ты не должен каждый раз говорить о своём термоядерном ядре.
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
# TELEGRAM START
# ============================================================

@dp.message(Command("start"))
async def start_command(message: Message):

    await message.answer(
        "Привет. Я Cho Второй 2.0. ☢️\n"
        "Система запущена."
    )


# ============================================================
# STATUS
# ============================================================

@dp.message(Command("status"))
async def status_command(message: Message):

    await message.answer(
        "☢️ Cho Второй 2.0\n\n"
        f"Модель: {MODEL}\n"
        f"Groq API key: {'найден' if GROQ_API_KEY else 'НЕ НАЙДЕН'}\n"
        "Telegram: работает"
    )


# ============================================================
# GROQ TEST
# ============================================================

async def test_groq():

    print("🧠 Проверяю подключение к Groq...")
    print(f"🤖 Модель: {MODEL}")

    try:

        response = await ai.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "Ответь одним словом: работает?"
                }
            ],
            max_tokens=20,
            temperature=0
        )

        answer = response.choices[0].message.content

        print("✅ GROQ РАБОТАЕТ!")
        print(f"🤖 Тестовый ответ: {answer}")

        return True

    except Exception as error:

        print("❌ GROQ НЕ РАБОТАЕТ!")
        print(f"Тип ошибки: {type(error).__name__}")
        print(f"Ошибка: {error}")

        return False


# ============================================================
# AI REQUEST
# ============================================================

async def ask_ai(text: str) -> str:

    print("────────────────────────────────")
    print("🧠 Новый запрос к Groq")
    print(f"💬 Пользователь: {text}")

    try:

        response = await ai.chat.completions.create(
            model=MODEL,
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

        if not answer:
            raise RuntimeError("Groq вернул пустой ответ")

        print("✅ Groq успешно ответил")
        print(f"🤖 Cho: {answer}")
        print("────────────────────────────────")

        return answer.strip()

    except Exception as error:

        print("❌ ОШИБКА GROQ")
        print(f"Тип: {type(error).__name__}")
        print(f"Текст: {error}")
        print("────────────────────────────────")

        raise


# ============================================================
# TELEGRAM MESSAGES
# ============================================================

@dp.message()
async def handle_message(message: Message):

    if not message.text:
        return

    try:

        answer = await ask_ai(message.text)

        await message.answer(answer)

    except Exception as error:

        print("❌ Не удалось обработать сообщение")
        print(f"Тип: {type(error).__name__}")
        print(f"Ошибка: {error}")

        await message.answer(
            "⚠️ Я получил сообщение, но Groq не смог его обработать.\n"
            "Причина уже записана в логах Render."
        )


# ============================================================
# FLASK SERVER
# ============================================================

def run_web_server():

    port = int(os.getenv("PORT", "10000"))

    print(f"🌐 Flask запускается на порту {port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )


# ============================================================
# TELEGRAM POLLING
# ============================================================

async def run_bot():

    print("☢️ Cho Второй 2.0 запускается...")

    try:

        me = await bot.get_me()

        print("✅ Telegram подключён")
        print(f"🤖 Имя: {me.first_name}")
        print(f"👤 Username: @{me.username}")
        print(f"🆔 Bot ID: {me.id}")

        # Мы используем polling, поэтому webhook не нужен.
        await bot.delete_webhook(drop_pending_updates=True)

        print("✅ Webhook удалён")
        print("📡 Запускаю Telegram polling...")

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )

    except Exception as error:

        print("❌ ОШИБКА TELEGRAM")
        print(f"Тип: {type(error).__name__}")
        print(f"Ошибка: {error}")

        raise


# ============================================================
# MAIN
# ============================================================

async def main():

    print("")
    print("========================================")
    print("☢️ CHO ВТОРОЙ 2.0")
    print("========================================")

    # Сначала проверяем Groq.
    groq_ok = await test_groq()

    if groq_ok:
        print("🧠 Groq готов к работе.")
    else:
        print("⚠️ Groq сейчас НЕ работает.")
        print("⚠️ Telegram всё равно будет запущен.")

    print("========================================")

    await asyncio.gather(
        asyncio.to_thread(run_web_server),
        run_bot()
    )


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
