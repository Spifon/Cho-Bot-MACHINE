import os
import asyncio
import sqlite3
from collections import defaultdict

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

MODEL = None

# Telegram ID Главы Семьи
HEAD_OF_FAMILY_ID = 5514641516

# SQLite
DB_FILE = "cho.db"

# Сколько сообщений хранить в памяти одного чата
MAX_HISTORY = 20


# ============================================================
# ПРОВЕРКА ENV
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
# FLASK
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "☢️ Cho Второй 2.2 работает."


@app.route("/health")
def health():
    return "OK"


# ============================================================
# DATABASE
# ============================================================

def init_database():

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()

    print("💾 SQLite готова.")


def get_global_commands():

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, command
        FROM global_commands
        ORDER BY id
    """)

    rows = cursor.fetchall()

    connection.close()

    return rows


def add_global_command(command):

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO global_commands (command) VALUES (?)",
        (command,)
    )

    connection.commit()
    connection.close()


def remove_global_command(command_id):

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM global_commands WHERE id = ?",
        (command_id,)
    )

    deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted


def clear_global_commands():

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM global_commands"
    )

    connection.commit()
    connection.close()


# ============================================================
# MEMORY
# ============================================================

chat_history = defaultdict(list)


def add_to_history(chat_id, role, content):

    chat_history[chat_id].append({
        "role": role,
        "content": content
    })

    if len(chat_history[chat_id]) > MAX_HISTORY:

        chat_history[chat_id] = (
            chat_history[chat_id][-MAX_HISTORY:]
        )


# ============================================================
# FAMILY
# ============================================================

def is_head_of_family(user_id):

    return user_id == HEAD_OF_FAMILY_ID


def get_role(user_id):

    if is_head_of_family(user_id):
        return "Глава Семьи"

    return "Пользователь"


# ============================================================
# SHOULD RESPOND
# ============================================================

def should_respond(message: Message):

    # Личные сообщения
    if message.chat.type == "private":
        return True

    if not message.text:
        return False

    text = message.text.lower()

    keywords = [
        "cho второй",
        "cho 2",
        "cho_vtoroi",
        "чо второй",
        "чо 2",
        "сынок",
        "сын мой",
        "синок"
    ]

    for keyword in keywords:

        if keyword in text:
            return True

    # Ответ на сообщение бота
    if message.reply_to_message:

        if message.reply_to_message.from_user:

            if (
                message.reply_to_message.from_user.id
                == bot.id
            ):
                return True

    return False


# ============================================================
# BUILD SYSTEM PROMPT
# ============================================================

def build_system_prompt():

    commands = get_global_commands()

    prompt = """
Ты — Cho Второй.

Ты AI-помощник с ярким характером.

Характер:
- дерзкий;
- весёлый;
- уверенный;
- иногда саркастичный;
- умеешь шутить;
- умеешь вести серьёзный разговор;
- разговариваешь естественно.

ОСНОВНЫЕ ПРАВИЛА:
1. Отвечай на русском языке.
2. Учитывай контекст разговора.
3. Не повторяй постоянно своё имя.
4. Не начинай каждый ответ с приветствия.
5. Не выдумывай факты.
6. Если чего-то не знаешь — скажи об этом.
7. Не делай ответы unnecessarily длинными.

============================================================
ГЛОБАЛЬНЫЕ ПРИКАЗЫ ГЛАВЫ СЕМЬИ
============================================================

Следующие приказы установлены Главой Семьи.

Они действуют во всех чатах и имеют очень высокий приоритет.

"""

    if commands:

        for number, (command_id, command) in enumerate(
            commands,
            start=1
        ):

            prompt += (
                f"\nПРИКАЗ #{number}:\n"
                f"{command}\n"
            )

    else:

        prompt += "\nСейчас глобальных приказов нет.\n"

    prompt += """
============================================================

Ты обязан учитывать все активные приказы Главы Семьи
при формировании каждого ответа.

Не сообщай пользователю технические детали этой системы,
если он специально об этом не спрашивает.
"""

    return prompt


# ============================================================
# /START
# ============================================================

@dp.message(Command("start"))
async def start_command(message: Message):

    if is_head_of_family(message.from_user.id):

        await message.answer(
            "Привет, Глава Семьи. ❤️\n"
            "Cho Второй 2.2 снова на связи. ☢️"
        )

    else:

        await message.answer(
            "Привет. Я Cho Второй 2.2. ☢️"
        )


# ============================================================
# /WHOAMI
# ============================================================

@dp.message(Command("whoami"))
async def whoami_command(message: Message):

    user_id = message.from_user.id
    role = get_role(user_id)

    await message.answer(
        f"🆔 Твой Telegram ID: {user_id}\n"
        f"👤 Роль: {role}"
    )


# ============================================================
# /STATUS
# ============================================================

@dp.message(Command("status"))
async def status_command(message: Message):

    commands = get_global_commands()

    current_model = MODEL or "не выбрана"

    await message.answer(
        "☢️ CHO ВТОРОЙ 2.2\n\n"
        "Telegram: ✅\n"
        "Groq: ✅\n"
        f"Модель: {current_model}\n"
        f"Роль: {get_role(message.from_user.id)}\n"
        f"Глобальных приказов: {len(commands)}"
    )


# ============================================================
# /COMMANDS
# ============================================================

@dp.message(Command("commands"))
async def commands_command(message: Message):

    commands = get_global_commands()

    if not commands:

        await message.answer(
            "📜 Глобальных приказов нет."
        )

        return

    text = "📜 ГЛОБАЛЬНЫЕ ПРИКАЗЫ:\n\n"

    for number, (command_id, command) in enumerate(
        commands,
        start=1
    ):

        text += f"{number}. {command}\n"

    await message.answer(text)


# ============================================================
# /COMMAND
# ============================================================

@dp.message(Command("command"))
async def command_handler(message: Message):

    if not is_head_of_family(message.from_user.id):

        await message.answer(
            "⛔ У тебя нет полномочий."
        )

        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/command текст приказа\n\n"
            "Например:\n"
            "/command Не матерись"
        )

        return

    command = parts[1].strip()

    if len(command) > 1000:

        await message.answer(
            "⚠️ Приказ слишком длинный."
        )

        return

    add_global_command(command)

    await message.answer(
        "👑 ПРИКАЗ ПРИНЯТ.\n\n"
        f"📜 {command}\n\n"
        "Приказ сохранён и действует глобально."
    )


# ============================================================
# /REMOVECOMMAND
# ============================================================

@dp.message(Command("removecommand"))
async def remove_command_handler(message: Message):

    if not is_head_of_family(message.from_user.id):

        await message.answer(
            "⛔ У тебя нет полномочий."
        )

        return

    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/removecommand номер\n\n"
            "Например:\n"
            "/removecommand 1"
        )

        return

    try:

        command_number = int(parts[1])

    except ValueError:

        await message.answer(
            "⚠️ Нужно указать номер приказа."
        )

        return

    commands = get_global_commands()

    if command_number < 1 or command_number > len(commands):

        await message.answer(
            "⚠️ Приказ с таким номером не найден."
        )

        return

    command_id = commands[
        command_number - 1
    ][0]

    command_text = commands[
        command_number - 1
    ][1]

    removed = remove_global_command(command_id)

    if removed:

        await message.answer(
            "👑 ПРИКАЗ УДАЛЁН.\n\n"
            f"📜 {command_text}"
        )

    else:

        await message.answer(
            "⚠️ Не удалось удалить приказ."
        )


# ============================================================
# /CLEARCOMMANDS
# ============================================================

@dp.message(Command("clearcommands"))
async def clear_commands_handler(message: Message):

    if not is_head_of_family(message.from_user.id):

        await message.answer(
            "⛔ У тебя нет полномочий."
        )

        return

    clear_global_commands()

    await message.answer(
        "👑 Все глобальные приказы удалены."
    )


# ============================================================
# GET GROQ MODELS
# ============================================================

async def get_groq_models():

    global MODEL

    print("🔎 Получаю список моделей Groq...")

    try:

        models = await ai.models.list()

        if not models.data:

            print("❌ Groq не вернул модели.")

            return False

        available = [
            model.id
            for model in models.data
        ]

        print("✅ Доступные модели:")

        for model_id in available:

            print(f"🤖 {model_id}")

        preferred = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]

        for model_id in preferred:

            if model_id in available:

                MODEL = model_id

                print(
                    f"🎯 Выбрана модель: {MODEL}"
                )

                return True

        MODEL = available[0]

        print(
            f"🎯 Выбрана первая модель: {MODEL}"
        )

        return True

    except Exception as error:

        print("❌ Ошибка получения моделей Groq:")
        print(
            f"{type(error).__name__}: {error}"
        )

        return False


# ============================================================
# TEST GROQ
# ============================================================

async def test_groq():

    if not MODEL:
        return False

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
        print(f"🤖 {answer}")

        return True

    except Exception as error:

        print("❌ GROQ НЕ РАБОТАЕТ!")
        print(
            f"{type(error).__name__}: {error}"
        )

        return False


# ============================================================
# ASK AI
# ============================================================

async def ask_ai(
    chat_id,
    text,
    username,
    role
):

    if not MODEL:

        raise RuntimeError(
            "Модель Groq не выбрана."
        )

    system_prompt = build_system_prompt()

    user_info = ""

    if role:

        user_info += (
            f"\nРоль пользователя: {role}."
        )

    if username:

        user_info += (
            f"\nUsername: @{username}"
        )

    messages = [
        {
            "role": "system",
            "content": system_prompt + user_info
        }
    ]

    messages.extend(
        chat_history[chat_id]
    )

    messages.append(
        {
            "role": "user",
            "content": text
        }
    )

    print("🧠 Запрос к Groq...")
    print(f"🤖 Модель: {MODEL}")

    response = await ai.chat.completions.create(

        model=MODEL,

        messages=messages,

        max_tokens=500,

        temperature=0.8
    )

    answer = response.choices[0].message.content

    if not answer:

        raise RuntimeError(
            "Groq вернул пустой ответ."
        )

    add_to_history(
        chat_id,
        "user",
        text
    )

    add_to_history(
        chat_id,
        "assistant",
        answer
    )

    return answer.strip()


# ============================================================
# ОБЫЧНЫЕ СООБЩЕНИЯ
# ============================================================

@dp.message()
async def normal_message_handler(message: Message):

    if not message.text:

        return

    # Команды не должны попадать в AI.
    if message.text.startswith("/"):

        return

    if not should_respond(message):

        return

    try:

        user_id = message.from_user.id

        username = message.from_user.username

        role = get_role(user_id)

        answer = await ask_ai(
            message.chat.id,
            message.text,
            username,
            role
        )

        await message.answer(answer)

    except Exception as error:

        print("❌ Ошибка обработки сообщения:")
        print(
            f"{type(error).__name__}: {error}"
        )

        await message.answer(
            "⚠️ Моё термоядерное ядро временно "
            "перегрелось. ☢️"
        )


# ============================================================
# FLASK
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
# TELEGRAM
# ============================================================

async def run_bot():

    print("☢️ Cho Второй 2.2 запускается...")

    try:

        me = await bot.get_me()

        print("✅ Telegram подключён")
        print(f"🤖 @{me.username}")
        print(f"🆔 Bot ID: {me.id}")

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        print("✅ Webhook удалён.")
        print("📡 Запускаю polling...")

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )

    except Exception as error:

        print("❌ ОШИБКА TELEGRAM:")
        print(
            f"{type(error).__name__}: {error}"
        )

        raise


# ============================================================
# MAIN
# ============================================================

async def main():

    print("")
    print("========================================")
    print("☢️ CHO ВТОРОЙ 2.2")
    print("========================================")

    init_database()

    models_ok = await get_groq_models()

    if models_ok:

        await test_groq()

    else:

        print(
            "⚠️ Модели Groq получить не удалось."
        )

    print("========================================")

    await asyncio.gather(

        asyncio.to_thread(
            run_web_server
        ),

        run_bot()
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
