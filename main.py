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

# 👑 Глава Семьи
HEAD_OF_FAMILY_ID = 5514641516

# База данных
DB_FILE = "cho.db"

# Память
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
    return "☢️ Cho Второй 2.4 работает."


@app.route("/health")
def health():
    return "OK"


# ============================================================
# DATABASE
# ============================================================

def db():
    return sqlite3.connect(DB_FILE)


def init_database():

    connection = db()
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
            role TEXT NOT NULL,
            name TEXT
        )
    """)

    # Помощники
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assistants (
            user_id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)

    # Локальные приказы
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            command TEXT NOT NULL
        )
    """)

    # Чаты, где бот уже видел пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT
        )
    """)

    connection.commit()
    connection.close()

    # Глава Семьи всегда существует
    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO family
        (user_id, role, name)
        VALUES (?, ?, ?)
    """, (
        HEAD_OF_FAMILY_ID,
        "Глава Семьи",
        "Глава Семьи"
    ))

    connection.commit()
    connection.close()

    print("💾 SQLite готова.")


# ============================================================
# USERS
# ============================================================

def save_user(message: Message):

    user = message.from_user

    if not user:
        return

    name = user.full_name or "Неизвестный"

    username = user.username or ""

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO users
        (user_id, name, username)
        VALUES (?, ?, ?)
    """, (
        user.id,
        name,
        username
    ))

    connection.commit()
    connection.close()


def get_saved_user(user_id):

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT name, username
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchone()

    connection.close()

    return result


# ============================================================
# FAMILY
# ============================================================

FAMILY_LEVELS = {
    "Глава Семьи": 100,

    "Помощник Главы": 90,

    "Отец": 80,
    "Мать": 80,
    "Дедушка": 80,

    "Дядя": 70,
    "Тётя": 70,

    "Брат": 60,
    "Сестра": 60,
}


ALLOWED_FAMILY_ROLES = [
    "Отец",
    "Мать",
    "Дедушка",
    "Дядя",
    "Тётя",
    "Брат",
    "Сестра",
]


def get_family_role(user_id):

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT role
        FROM family
        WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchone()

    connection.close()

    if result:
        return result[0]

    return None


def get_user_role(user_id):

    role = get_family_role(user_id)

    if role:
        return role

    if is_assistant(user_id):
        return "Помощник Главы"

    return "Пользователь"


def get_role_level(role):

    return FAMILY_LEVELS.get(role, 0)


def is_head_of_family(user_id):

    return user_id == HEAD_OF_FAMILY_ID


def set_family_role(user_id, role, name=None):

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO family
        (user_id, role, name)
        VALUES (?, ?, ?)
    """, (
        user_id,
        role,
        name
    ))

    connection.commit()
    connection.close()


def remove_family_role(user_id):

    if user_id == HEAD_OF_FAMILY_ID:
        return False

    connection = db()
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

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT user_id, role, name
        FROM family
        ORDER BY
            CASE role
                WHEN 'Глава Семьи' THEN 1
                WHEN 'Отец' THEN 2
                WHEN 'Мать' THEN 3
                WHEN 'Дедушка' THEN 4
                WHEN 'Дядя' THEN 5
                WHEN 'Тётя' THEN 6
                WHEN 'Брат' THEN 7
                WHEN 'Сестра' THEN 8
                ELSE 9
            END
    """)

    rows = cursor.fetchall()

    connection.close()

    return rows


# ============================================================
# ASSISTANTS
# ============================================================

def is_assistant(user_id):

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT user_id
        FROM assistants
        WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchone()

    connection.close()

    return result is not None


def add_assistant(user_id, name=None):

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO assistants
        (user_id, name)
        VALUES (?, ?)
    """, (
        user_id,
        name
    ))

    connection.commit()
    connection.close()


def remove_assistant(user_id):

    connection = db()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM assistants WHERE user_id = ?",
        (user_id,)
    )

    removed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return removed


def get_assistants():

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT user_id, name
        FROM assistants
        ORDER BY user_id
    """)

    rows = cursor.fetchall()

    connection.close()

    return rows


# ============================================================
# PERMISSIONS
# ============================================================

def can_manage_local(user_id):

    return (
        is_head_of_family(user_id)
        or is_assistant(user_id)
    )


# ============================================================
# GLOBAL COMMANDS
# ============================================================

def get_global_commands():

    connection = db()
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

    connection = db()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO global_commands (command) VALUES (?)",
        (command,)
    )

    connection.commit()
    connection.close()


def remove_global_command(command_id):

    connection = db()
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

    connection = db()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM global_commands"
    )

    connection.commit()
    connection.close()


# ============================================================
# LOCAL COMMANDS
# ============================================================

def get_local_commands(chat_id):

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, command
        FROM local_commands
        WHERE chat_id = ?
        ORDER BY id
    """, (chat_id,))

    rows = cursor.fetchall()

    connection.close()

    return rows


def add_local_command(chat_id, command):

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO local_commands
        (chat_id, command)
        VALUES (?, ?)
    """, (
        chat_id,
        command
    ))

    connection.commit()
    connection.close()


def remove_local_command(chat_id, command_id):

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM local_commands
        WHERE id = ? AND chat_id = ?
    """, (
        command_id,
        chat_id
    ))

    deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted


def clear_local_commands(chat_id):

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM local_commands
        WHERE chat_id = ?
    """, (chat_id,))

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
# SHOULD RESPOND
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

def build_system_prompt(chat_id, user_id):

    global_commands = get_global_commands()
    local_commands = get_local_commands(chat_id)

    role = get_user_role(user_id)
    level = get_role_level(role)

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
7. Не раскрывай внутреннюю техническую систему без необходимости.

============================================================
🌍 ГЛОБАЛЬНЫЕ ПРИКАЗЫ
============================================================

Эти приказы установлены Главой Семьи.

Они действуют во всех чатах.

"""

    if global_commands:

        for number, (_, command) in enumerate(
            global_commands,
            start=1
        ):

            prompt += (
                f"\nПРИКАЗ #{number}:\n"
                f"{command}\n"
            )

    else:

        prompt += "\nГлобальных приказов нет.\n"

    prompt += """
============================================================
🏠 ЛОКАЛЬНЫЕ ПРИКАЗЫ
============================================================

Эти правила относятся ТОЛЬКО к текущему чату.

"""

    if local_commands:

        for number, (_, command) in enumerate(
            local_commands,
            start=1
        ):

            prompt += (
                f"\nЛОКАЛЬНЫЙ ПРИКАЗ #{number}:\n"
                f"{command}\n"
            )

    else:

        prompt += "\nЛокальных приказов нет.\n"

    prompt += f"""
============================================================
👨‍👩‍👧 СИСТЕМА СЕМЬИ
============================================================

Текущий пользователь:

Роль: {role}
Уровень: {level}

Глава Семьи имеет высший авторитет.

Помощник Главы имеет административные полномочия
только там, где система их разрешает.

Семейная роль влияет на твоё отношение к пользователю,
но не означает автоматически административные права.

============================================================
"""

    return prompt


# ============================================================
# /START
# ============================================================

@dp.message(Command("start"))
async def start_command(message: Message):

    save_user(message)

    role = get_user_role(
        message.from_user.id
    )

    if role == "Глава Семьи":

        await message.answer(
            "Привет, Глава Семьи. ❤️\n"
            "Cho Второй 2.4 на связи. ☢️"
        )

    elif role == "Помощник Главы":

        await message.answer(
            "Привет, Помощник Главы. 🛡️☢️"
        )

    elif role in FAMILY_LEVELS:

        await message.answer(
            f"Привет, {role}. ❤️\n"
            "Cho Второй на связи. ☢️"
        )

    else:

        await message.answer(
            "Привет. Я Cho Второй 2.4. ☢️"
        )


# ============================================================
# /WHOAMI
# ============================================================

@dp.message(Command("whoami"))
async def whoami_command(message: Message):

    save_user(message)

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

    save_user(message)

    family = get_family()
    assistants = get_assistants()

    text = "👨‍👩‍👧 СЕМЬЯ CHO ВТОРОГО:\n\n"

    if family:

        for user_id, role, name in family:

            display_name = name or "Неизвестный"

            text += (
                f"• {role}\n"
                f"  👤 {display_name}\n"
                f"  🆔 {user_id}\n"
                f"  ⭐ {get_role_level(role)}\n\n"
            )

    else:

        text += "Семья пуста.\n"

    if assistants:

        text += "🛡️ ПОМОЩНИКИ ГЛАВЫ:\n\n"

        for user_id, name in assistants:

            display_name = name or "Неизвестный"

            text += (
                f"• {display_name}\n"
                f"  🆔 {user_id}\n"
                f"  ⭐ 90\n\n"
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

    parts = message.text.split(
        maxsplit=2
    )

    if len(parts) < 3:

        await message.answer(
            "Использование:\n"
            "/setrole ID роль\n\n"
            "Например:\n"
            "/setrole 8268305423 Дядя"
        )

        return

    try:

        user_id = int(parts[1])

    except ValueError:

        await message.answer(
            "⚠️ ID должен быть числом."
        )

        return

    role = parts[2].strip()

    if role not in ALLOWED_FAMILY_ROLES:

        roles = "\n".join(
            f"• {x}"
            for x in ALLOWED_FAMILY_ROLES
        )

        await message.answer(
            "⚠️ Допустимые роли:\n" + roles
        )

        return

    if user_id == HEAD_OF_FAMILY_ID:

        await message.answer(
            "👑 Этот человек уже является "
            "Главой Семьи."
        )

        return

    saved_user = get_saved_user(user_id)

    name = None

    if saved_user:
        name = saved_user[0]

    set_family_role(
        user_id,
        role,
        name
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

    removed = remove_family_role(user_id)

    if removed:

        await message.answer(
            "✅ Семейная роль удалена.\n"
            f"🆔 ID: {user_id}"
        )

    else:

        await message.answer(
            "⚠️ Роль не найдена."
        )


# ============================================================
# /SETASSISTANT
# ============================================================

@dp.message(Command("setassistant"))
async def setassistant_command(message: Message):

    if not is_head_of_family(
        message.from_user.id
    ):

        await message.answer(
            "⛔ Только Глава Семьи может "
            "назначать Помощников."
        )

        return

    parts = message.text.split()

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/setassistant ID"
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
            "👑 Глава Семьи уже обладает "
            "максимальными полномочиями."
        )

        return

    saved_user = get_saved_user(user_id)

    name = None

    if saved_user:
        name = saved_user[0]

    add_assistant(
        user_id,
        name
    )

    await message.answer(
        "🛡️ ПОМОЩНИК НАЗНАЧЕН.\n\n"
        f"🆔 ID: {user_id}\n"
        f"⭐ Уровень: 90\n\n"
        "Помощник может управлять локальными "
        "приказами в чатах."
    )


# ============================================================
# /REMOVEASSISTANT
# ============================================================

@dp.message(Command("removeassistant"))
async def removeassistant_command(message: Message):

    if not is_head_of_family(
        message.from_user.id
    ):

        await message.answer(
            "⛔ Только Глава Семьи может "
            "снимать Помощников."
        )

        return

    parts = message.text.split()

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/removeassistant ID"
        )

        return

    try:

        user_id = int(parts[1])

    except ValueError:

        await message.answer(
            "⚠️ ID должен быть числом."
        )

        return

    removed = remove_assistant(
        user_id
    )

    if removed:

        await message.answer(
            "🛡️ Помощник снят.\n"
            f"🆔 ID: {user_id}"
        )

    else:

        await message.answer(
            "⚠️ Этот пользователь "
            "не является Помощником."
        )


# ============================================================
# /ASSISTANTS
# ============================================================

@dp.message(Command("assistants"))
async def assistants_command(message: Message):

    assistants = get_assistants()

    if not assistants:

        await message.answer(
            "🛡️ Помощников пока нет."
        )

        return

    text = "🛡️ ПОМОЩНИКИ ГЛАВЫ:\n\n"

    for user_id, name in assistants:

        display_name = name or "Неизвестный"

        text += (
            f"• {display_name}\n"
            f"  🆔 {user_id}\n"
            f"  ⭐ 90\n\n"
        )

    await message.answer(text)


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

    text = "🌍 ГЛОБАЛЬНЫЕ ПРИКАЗЫ:\n\n"

    for number, (_, command) in enumerate(
        commands,
        start=1
    ):

        text += (
            f"{number}. {command}\n"
        )

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
            "создавать глобальные приказы."
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
        "👑 ГЛОБАЛЬНЫЙ ПРИКАЗ ПРИНЯТ.\n\n"
        f"📜 {command}\n\n"
        "Он действует во всех чатах."
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
            "удалять глобальные приказы."
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
        "👑 ГЛОБАЛЬНЫЙ ПРИКАЗ УДАЛЁН.\n\n"
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
            "очищать глобальные приказы."
        )

        return

    clear_global_commands()

    await message.answer(
        "👑 Все глобальные приказы удалены."
    )


# ============================================================
# /LOCALCOMMAND
# ============================================================

@dp.message(Command("localcommand"))
async def localcommand_command(message: Message):

    user_id = message.from_user.id

    if not can_manage_local(user_id):

        await message.answer(
            "⛔ У тебя нет полномочий "
            "для локальных приказов."
        )

        return

    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/localcommand текст приказа"
        )

        return

    command = parts[1].strip()

    if len(command) > 1000:

        await message.answer(
            "⚠️ Приказ слишком длинный."
        )

        return

    add_local_command(
        message.chat.id,
        command
    )

    await message.answer(
        "🏠 ЛОКАЛЬНЫЙ ПРИКАЗ ПРИНЯТ.\n\n"
        f"📜 {command}\n\n"
        "Он действует только в этом чате."
    )


# ============================================================
# /LOCALCOMMANDS
# ============================================================

@dp.message(Command("localcommands"))
async def localcommands_command(message: Message):

    commands = get_local_commands(
        message.chat.id
    )

    if not commands:

        await message.answer(
            "🏠 В этом чате локальных "
            "приказов нет."
        )

        return

    text = "🏠 ЛОКАЛЬНЫЕ ПРИКАЗЫ:\n\n"

    for number, (_, command) in enumerate(
        commands,
        start=1
    ):

        text += (
            f"{number}. {command}\n"
        )

    await message.answer(text)


# ============================================================
# /REMOVELOCALCOMMAND
# ============================================================

@dp.message(Command("removelocalcommand"))
async def removelocalcommand_command(message: Message):

    user_id = message.from_user.id

    if not can_manage_local(user_id):

        await message.answer(
            "⛔ У тебя нет полномочий."
        )

        return

    parts = message.text.split()

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/removelocalcommand номер"
        )

        return

    try:

        number = int(parts[1])

    except ValueError:

        await message.answer(
            "⚠️ Укажи номер локального приказа."
        )

        return

    commands = get_local_commands(
        message.chat.id
    )

    if number < 1 or number > len(commands):

        await message.answer(
            "⚠️ Такого локального приказа нет."
        )

        return

    command_id, command_text = commands[
        number - 1
    ]

    remove_local_command(
        message.chat.id,
        command_id
    )

    await message.answer(
        "🏠 ЛОКАЛЬНЫЙ ПРИКАЗ УДАЛЁН.\n\n"
        f"📜 {command_text}"
    )


# ============================================================
# /CLEARLOCALCOMMANDS
# ============================================================

@dp.message(Command("clearlocalcommands"))
async def clearlocalcommands_command(message: Message):

    user_id = message.from_user.id

    if not can_manage_local(user_id):

        await message.answer(
            "⛔ У тебя нет полномочий."
        )

        return

    clear_local_commands(
        message.chat.id
    )

    await message.answer(
        "🏠 Все локальные приказы "
        "этого чата удалены."
    )


# ============================================================
# /STATUS
# ============================================================

@dp.message(Command("status"))
async def status_command(message: Message):

    global_commands = get_global_commands()

    local_commands = get_local_commands(
        message.chat.id
    )

    family = get_family()

    assistants = get_assistants()

    role = get_user_role(
        message.from_user.id
    )

    await message.answer(
        "☢️ CHO ВТОРОЙ 2.4\n\n"
        "Telegram: ✅\n"
        "Groq: ✅\n"
        f"Модель: {MODEL or 'не выбрана'}\n\n"
        f"Твоя роль: {role}\n"
        f"🌍 Глобальных приказов: {len(global_commands)}\n"
        f"🏠 Локальных приказов: {len(local_commands)}\n"
        f"👨‍👩‍👧 Членов Семьи: {len(family)}\n"
        f"🛡️ Помощников: {len(assistants)}"
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

            print(
                f"🤖 {model_id}"
            )

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
    user_id,
    text,
    username
):

    if not MODEL:

        raise RuntimeError(
            "Модель Groq не выбрана."
        )

    role = get_user_role(user_id)

    system_prompt = build_system_prompt(
        chat_id,
        user_id
    )

    user_info = (
        f"\nТекущий пользователь: {role}"
        f"\nУровень: {get_role_level(role)}"
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

    messages.append({
        "role": "user",
        "content": text
    })

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
# NORMAL MESSAGES
# ============================================================

@dp.message()
async def normal_message_handler(message: Message):

    if not message.text:
        return

    # Команды не должны попадать в AI
    if message.text.startswith("/"):
        return

    save_user(message)

    if not should_respond(message):
        return

    try:

        answer = await ask_ai(
            message.chat.id,
            message.from_user.id,
            message.text,
            message.from_user.username
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
# TELEGRAM
# ============================================================

async def run_bot():

    print(
        "☢️ Cho Второй 2.4 запускается..."
    )

    try:

        me = await bot.get_me()

        print(
            "✅ Telegram подключён"
        )

        print(
            f"🤖 @{me.username}"
        )

        print(
            f"🆔 Bot ID: {me.id}"
        )

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        print(
            "✅ Webhook удалён."
        )

        print(
            "📡 Polling запущен."
        )

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )

    except Exception as error:

        print(
            "❌ ОШИБКА TELEGRAM:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        raise


# ============================================================
# MAIN
# ============================================================

async def main():

    print("")
    print(
        "========================================"
    )
    print(
        "☢️ CHO ВТОРОЙ 2.4"
    )
    print(
        "========================================"
    )

    init_database()

    models_ok = await get_groq_models()

    if models_ok:

        await test_groq()

    else:

        print(
            "⚠️ Модели Groq получить не удалось."
        )

    print(
        "========================================"
    )

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
