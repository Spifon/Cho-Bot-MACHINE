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

# Пока модель специально НЕ задаём.
# Сначала получим список моделей от Groq.
MODEL = None


# ============================================================
# ПРОВЕРКА КЛЮЧЕЙ
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден!")

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY не найден!")


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

Ты AI-помощник с характером.

Характер:
- дерзкий;
- весёлый;
- уверенный;
- иногда саркастичный;
- умеешь шутить;
- умеешь нормально разговаривать на серьёзные темы.

Правила:
- отвечай только на русском языке;
- отвечай естественно;
- учитывай контекст разговора;
- не повторяй постоянно своё имя;
- не начинай каждый ответ с приветствия;
- не выдумывай факты;
- если не знаешь ответа — честно скажи об этом;
- не делай каждый ответ огромным.

Ты — Cho Второй.
"""


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "☢️ Cho Второй 2.0 работает."


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
        "Термоядерное ядро запущено."
    )


# ============================================================
# STATUS
# ============================================================

@dp.message(Command("status"))
async def status_command(message: Message):

    current_model = MODEL if MODEL else "не выбрана"

    await message.answer(
        "☢️ СТАТУС CHO ВТОРОГО\n\n"
        f"Telegram: ✅\n"
        f"Groq API: {'✅' if GROQ_API_KEY else '❌'}\n"
        f"Модель: {current_model}"
    )


# ============================================================
# ПОЛУЧЕНИЕ МОДЕЛЕЙ GROQ
# ============================================================

async def get_groq_models():

    global MODEL

    print("========================================")
    print("🔎 Получаю список моделей Groq...")
    print("========================================")

    try:

        models = await ai.models.list()

        if not models.data:
            print("❌ Groq не вернул ни одной модели.")
            return False

        print("✅ Доступные модели:")

        for model in models.data:

            model_id = model.id

            print(f"🤖 {model_id}")

        # ----------------------------------------------------
        # Пытаемся выбрать подходящую текстовую модель.
        # ----------------------------------------------------

        preferred_models = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
        ]

        available_ids = [model.id for model in models.data]

        for preferred in preferred_models:

            if preferred in available_ids:

                MODEL = preferred

                print("========================================")
                print(f"🎯 Выбрана модель: {MODEL}")
                print("========================================")

                return True

        # ----------------------------------------------------
        # Если ни одна предпочитаемая модель не найдена,
        # выбираем первую модель из списка.
        # ----------------------------------------------------

        MODEL = available_ids[0]

        print("⚠️ Предпочитаемая модель не найдена.")
        print(f"🎯 Временно выбрана первая модель: {MODEL}")

        return True

    except Exception as error:

        print("========================================")
        print("❌ НЕ УДАЛОСЬ ПОЛУЧИТЬ МОДЕЛИ GROQ")
        print(f"Тип ошибки: {type(error).__name__}")
        print(f"Ошибка: {error}")
        print("========================================")

        return False


# ============================================================
# ТЕСТ GROQ
# ============================================================

async def test_groq():

    if not MODEL:

        print("❌ Невозможно протестировать Groq: модель не выбрана.")

        return False

    print("🧠 Проверяю выбранную модель...")
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

        print("========================================")
        print("✅ GROQ РАБОТАЕТ!")
        print(f"🤖 Ответ модели: {answer}")
        print("========================================")

        return True

    except Exception as error:

        print("========================================")
        print("❌ GROQ НЕ РАБОТАЕТ!")
        print(f"Тип ошибки: {type(error).__name__}")
        print(f"Ошибка: {error}")
        print("========================================")

        return False


# ============================================================
# ЗАПРОС К ИИ
# ============================================================

async def ask_ai(text: str):

    if not MODEL:

        raise RuntimeError(
            "Модель Groq не выбрана."
        )

    print("----------------------------------------")
    print("🧠 Новый запрос к Groq")
    print(f"💬 Сообщение: {text}")
    print(f"🤖 Модель: {MODEL}")

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

            raise RuntimeError(
                "Groq вернул пустой ответ."
            )

        print("✅ Groq ответил!")
        print(f"🤖 Cho: {answer}")
        print("----------------------------------------")

        return answer.strip()

    except Exception as error:

        print("----------------------------------------")
        print("❌ ОШИБКА GROQ")
        print(f"Тип: {type(error).__name__}")
        print(f"Ошибка: {error}")
        print("----------------------------------------")

        raise


# ============================================================
# ОБЫЧНЫЕ СООБЩЕНИЯ
# ============================================================

@dp.message()
async def handle_message(message: Message):

    if not message.text:
        return

    try:

        answer = await ask_ai(message.text)

        await message.answer(answer)

    except Exception as error:

        print("❌ Ошибка обработки сообщения:")
        print(f"{type(error).__name__}: {error}")

        await message.answer(
            "⚠️ Я получил сообщение, но ИИ сейчас не смог ответить.\n"
            "Причина записана в логах Render."
        )


# ============================================================
# FLASK SERVER
# ============================================================

def run_web_server():

    port = int(
        os.getenv("PORT", "10000")
    )

    print(
        f"🌐 Flask запускается на порту {port}"
    )

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

        # Мы используем polling.
        # Поэтому webhook нам не нужен.
        await bot.delete_webhook(
            drop_pending_updates=True
        )

        print("✅ Webhook удалён")
        print("📡 Запускаю Telegram polling...")

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )

    except Exception as error:

        print("========================================")
        print("❌ ОШИБКА TELEGRAM")
        print(f"Тип ошибки: {type(error).__name__}")
        print(f"Ошибка: {error}")
        print("========================================")

        raise


# ============================================================
# MAIN
# ============================================================

async def main():

    print("")
    print("========================================")
    print("☢️ CHO ВТОРОЙ 2.0")
    print("========================================")

    # --------------------------------------------------------
    # 1. Получаем доступные модели
    # --------------------------------------------------------

    models_ok = await get_groq_models()

    # --------------------------------------------------------
    # 2. Проверяем Groq
    # --------------------------------------------------------

    if models_ok:

        groq_ok = await test_groq()

        if groq_ok:

            print("🧠 Groq полностью готов.")

        else:

            print(
                "⚠️ Groq доступен, "
                "но тестовый запрос не прошёл."
            )

    else:

        print(
            "⚠️ Не удалось получить список моделей Groq."
        )

    print("========================================")

    # --------------------------------------------------------
    # 3. Запускаем Flask + Telegram
    # --------------------------------------------------------

    await asyncio.gather(

        asyncio.to_thread(
            run_web_server
        ),

        run_bot()
    )


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
