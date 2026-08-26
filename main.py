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

HEAD_OF_FAMILY_ID = 5514641516

DB_FILE = "cho.db"

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
    return "☢️ Cho Второй 2.3 работает."


@app.route("/health")
def health():
    return "OK"


# ============================================================
# DATABASE
# ============================================================

def init_database():

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    # Глобальные приказы
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL
        )
    """)

    # Семья
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family (
            user_id INTEGER PRIMARY KEY,
            role TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()

    # Добавляем Главу Семьи автоматически
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO family
        (user_id, role)
        VALUES (?, ?)
    """, (
        HEAD_OF_FAMILY_ID,
        "Глава Семьи"
    ))

    connection.commit()
    connection.close()

    print("💾 SQLite готова.")


# ============================================================
# GLOBAL COMMANDS
# ============================================================

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
# FAMILY
# ============================================================

FAMILY_LEVELS = {
    "Глава Семьи": 100,
    "Отец": 80,
    "Мать": 80,
    "Дедушка": 80,
}


def get_family_role(user_id):

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT role FROM family WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return None


def set_family_role(user_id, role):

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO family
        (user_id, role)
        VALUES (?, ?)
    """, (
        user_id,
        role
    ))

    connection.commit()
    connection.close()


def remove_family_role(user_id):

    # Нельзя удалить Главу Семьи
    if user_id == HEAD_OF_FAMILY_ID:
        return False

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM family WHERE user_id = ?",
        (user_id,)
    )

    deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted


def get_family():

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT user_id, role
        FROM family
        ORDER BY
            CASE role
                WHEN 'Глава Семьи' THEN 1
                WHEN 'Отец' THEN 2
                WHEN 'Мать' THEN 3
                WHEN 'Дедушка' THEN 4
                ELSE 5
            END
    """)

    rows = cursor.fetchall()

    connection.close()

    return rows


# ============================================================
# ROLE
# ============================================================

def get_role_level(role):

    return FAMILY_LEVELS.get(role, 0)


def get_user_role(user_id):

    role = get_family_role(user_id)

    if role:
        return role

    return "Пользователь"


def is_head_of_family(user_id):

    return user_id == HEAD_OF_FAMILY_ID


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
# GROUP RESPONSE
# ============================================================

def should_respond(message: Message):

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

    if message.reply_to_message:

        if message.reply_to_message.from_user:

            if (
                message.reply_to_message.from_user.id
                == bot.id
            ):
                return True

    return False


# ============================================================
# SYSTEM PROMPT
# ============================================================

def build_system_prompt():

    commands = get_global_commands()

    prompt = """
Ты — Cho Второй.

Ты AI-помощник с характером.

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
6. Если чего-то не знаешь — честно скажи.
7. Не делай ответы unnecessarily длинными.

============================================================
ГЛОБАЛЬНЫЕ ПРИКАЗЫ ГЛАВЫ СЕМЬИ
============================================================

Эти правила установлены Главой Семьи.

Они действуют во всех чатах.

"""

    if commands:

        for number, (_, command) in enumerate(
            commands,
            start=1
        ):

            prompt += (
                f"\nПРИКАЗ #{number}:\n"
                f"{command}\n"
            )

    else:

        prompt += "\nПриказов нет.\n"

    prompt += """
============================================================
СИСТЕМА СЕМЬИ
============================================================

У пользователей могут быть семейные роли.

Семейная роль означает особое отношение к пользователю.

Глава Семьи имеет высший авторитет.

Не выдумывай семейные роли.
Используй только ту роль, которая передана тебе системой.

"""

    return prompt


# ============================================================
# /START
# ============================================================

@dp.message(Command("start"))
async def start_command(message: Message):

    role = get_user_role(
        message.from_user.id
    )

    if role == "Глава Семьи":

        await message.answer(
            "Привет, Глава Семьи. ❤️\n"
            "Cho Второй 2.3 на связи. ☢️"
        )

    elif role in FAMILY_LEVELS:

        await message.answer(
            f"Привет, {role}. ❤️\n"
            "Cho Второй на связи. ☢️"
        )

    else:

        await message.answer(
            "Привет. Я Cho Второй 2.3. ☢️"
        )


# ============================================================
# /WHOAMI
# ============================================================

@dp.message(Command("whoami"))
async def whoami_command(message: Message):

    user_id = message.from_user.id

    role = get_user_role(user_id)

    level = get_role_level(role)

    await message.answer(
        f"🆔 ID: {user_id}\n"
        f"👤 Роль: {role}\n"
        f"⭐ Уровень: {level}"
    )


# ============================================================
# /FAMILY
# ============================================================

@dp.message(Command("family"))
async def family_command(message: Message):

    family = get_family()

    if not family:

        await message.answer(
            "👨‍👩‍👧 Семья пока пуста."
        )

        return

    text = "👨‍👩‍👧 СЕМЬЯ CHO ВТОРОГО:\n\n"

    for user_id, role in family:

        level = get_role_level(role)

        text += (
            f"• {role}\n"
            f"  ID: {user_id}\n"
            f"  Уровень: {level}\n\n"
        )

    await message.answer(text)


# ============================================================
# /SETROLE
# ============================================================

@dp.message(Command("setrole"))
async def setrole_command(message: Message):

    if not is_head_of_family(
        message.from_user.id
    ):

        await message.answer(
            "⛔ Только Глава Семьи может "
            "назначать семейные роли."
        )

        return

    parts = message.text.split()

    if len(parts) < 3:

        await message.answer(
            "Использование:\n"
            "/setrole ID роль\n\n"
            "Пример:\n"
            "/setrole 123456789 Отец"
        )

        return

    try:

        user_id = int(parts[1])

    except ValueError:

        await message.answer(
            "⚠️ ID должен быть числом."
        )

        return

    role = " ".join(parts[2:]).strip()

    allowed_roles = [
        "Отец",
        "Мать",
        "Дедушка"
    ]

    if role not in allowed_roles:

        await message.answer(
            "⚠️ Допустимые роли:\n"
            "Отец\n"
            "Мать\n"
            "Дедушка"
        )

        return

    if user_id == HEAD_OF_FAMILY_ID:

        await message.answer(
            "👑 Этот ID уже является Главой Семьи."
        )

        return

    set_family_role(
        user_id,
        role
    )

    await message.answer(
        "👑 РОЛЬ НАЗНАЧЕНА.\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Роль: {role}\n"
        f"⭐ Уровень: {get_role_level(role)}"
    )


# ============================================================
# /REMOVEROLE
# ============================================================

@dp.message(Command("removerole"))
async def removerole_command(message: Message):

    if not is_head_of_family(
        message.from_user.id
    ):

        await message.answer(
            "⛔ Только Глава Семьи может "
            "удалять семейные роли."
        )

        return

    parts = message.text.split()

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/removerole ID"
        )

        return

    try:

        user_id = int(parts[1])

    except ValueError:

        await message.answer(
            "⚠️ ID должен быть числом."
        )

        return

    if user_id == HEAD_OF_FAMILY_ID:

        await message.answer(
            "👑 Нельзя удалить Главу Семьи."
        )

        return

    removed = remove_family_role(
        user_id
    )

    if removed:

        await message.answer(
            "✅ Семейная роль удалена.\n"
            f"🆔 ID: {user_id}"
        )

    else:

        await message.answer(
            "⚠️ У этого пользователя "
            "нет семейной роли."
        )


# ============================================================
# /STATUS
# ============================================================

@dp.message(Command("status"))
async def status_command(message: Message):

    commands = get_global_commands()

    family = get_family()

    current_model = MODEL or "не выбрана"

    await message.answer(
        "☢️ CHO ВТОРОЙ 2.3\n\n"
        "Telegram: ✅\n"
        "Groq: ✅\n"
        f"Модель: {current_model}\n"
        f"Твоя роль: {get_user_role(message.from_user.id)}\n"
        f"Приказов: {len(commands)}\n"
        f"Членов Семьи: {len(family)}"
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

    for number, (_, command) in enumerate(
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

    if not is_head_of_family(
        message.from_user.id
    ):

        await message.answer(
            "⛔ Только Глава Семьи может "
            "отдавать глобальные приказы."
        )

        return

    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/command текст приказа"
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
        "Приказ сохранён глобально."
    )


# ============================================================
# /REMOVECOMMAND
# ============================================================

@dp.message(Command("removecommand"))
async def removecommand_command(message: Message):

    if not is_head_of_family(
        message.from_user.id
    ):

        await message.answer(
            "⛔ Только Глава Семьи может "
            "удалять приказы."
        )

        return

    parts = message.text.split()

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/removecommand номер"
        )

        return

    try:

        number = int(parts[1])

    except ValueError:

        await message.answer(
            "⚠️ Укажи номер приказа."
        )

        return

    commands = get_global_commands()

    if number < 1 or number > len(commands):

        await message.answer(
            "⚠️ Такого приказа нет."
        )

        return

    command_id, command_text = commands[
        number - 1
    ]

    remove_global_command(
        command_id
    )

    await message.answer(
        "👑 ПРИКАЗ УДАЛЁН.\n\n"
        f"📜 {command_text}"
    )


# ============================================================
# /CLEARCOMMANDS
# ============================================================

@dp.message(Command("clearcommands"))
async def clearcommands_command(message: Message):

    if not is_head_of_family(
        message.from_user.id
    ):

        await message.answer(
            "⛔ Только Глава Семьи может "
            "очищать приказы."
        )

        return

    clear_global_commands()

    await message.answer(
        "👑 Все глобальные приказы удалены."
    )


# ============================================================
# GROQ MODELS
# ============================================================

async def get_groq_models():

    global MODEL

    print("🔎 Получаю список моделей Groq...")

    try:

        models = await ai.models.list()

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

        if available:

            MODEL = available[0]

            print(
                f"🎯 Выбрана первая модель: {MODEL}"
            )

            return True

        return False

    except Exception as error:

        print("❌ Ошибка моделей Groq:")
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

        print("✅ GROQ РАБОТАЕТ!")
        print(
            f"🤖 {response.choices[0].message.content}"
        )

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
# ОЧНЫЕ СООБЩЕНИЯ
# ============================================================

@dp.message()
async def normal_message_handler(message: Message):

    if not message.text:
        return

    # Команды не передаём AI
    if message.text.startswith("/"):
        return

    if not should_respond(message):
        return

    try:

        user_id = message.from_user.id

        username = message.from_user.username

        role = get_user_role(user_id)

        answer = await ask_ai(
            message.chat.id,
            message.text,
            username,
            role
        )

        await message.answer(answer)

    except Exception as error:

        print("❌ Ошибка обработки:")
        print(
            f"{type(error).__name__}: {error}"
        )

        await message.answer(
            "⚠️ Моё термоядерное ядро "
            "временно перегрелось. ☢️"
        )


# ============================================================
# WEB SERVER
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
# BOT
# ============================================================

async def run_bot():

    print("☢️ Cho Второй 2.3 запускается...")

    try:

        me = await bot.get_me()

        print("✅ Telegram подключён")
        print(f"🤖 @{me.username}")
        print(f"🆔 Bot ID: {me.id}")

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        print("✅ Webhook удалён.")
        print("📡 Polling запущен.")

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
    print("☢️ CHO ВТОРОЙ 2.3")
    print("========================================")

    init_database()

    models_ok = await get_groq_models()

    if models_ok:

        await test_groq()

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
