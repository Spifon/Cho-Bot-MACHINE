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

# ID Главы Семьи
HEAD_OF_FAMILY_ID = 5514641516

# Файл базы данных
DB_FILE = "cho.db"

# Максимум сообщений памяти на один чат
MAX_HISTORY = 20


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
    return "☢️ Cho Второй 2.1 работает."


@app.route("/health")
def health():
    return "OK"


# ============================================================
# БАЗА ДАННЫХ
# ============================================================

def init_database():

    connection = sqlite3.connect(DB_FILE)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL UNIQUE
        )
    """)

    connection.commit()
    connection.close()

    print("💾 База данных готова.")


def get_global_commands():

    connection = sqlite3.connect(DB_FILE)

    cursor = connection.cursor()

    cursor.execute(
        "SELECT command FROM global_commands ORDER BY id"
    )

    rows = cursor.fetchall()

    connection.close()

    return [row[0] for row in rows]


def add_global_command(command):

    connection = sqlite3.connect(DB_FILE)

    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO global_commands (command) VALUES (?)",
            (command,)
        )

        connection.commit()

        result = True

    except sqlite3.IntegrityError:

        result = False

    connection.close()

    return result


def remove_global_command(command):

    connection = sqlite3.connect(DB_FILE)

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM global_commands WHERE command = ?",
        (command,)
    )

    deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted


def clear_global_commands():

    connection = sqlite3.connect(DB_FILE)

    cursor = connection.cursor()

    cursor.execute("DELETE FROM global_commands")

    connection.commit()
    connection.close()


# ============================================================
# ПАМЯТЬ РАЗГОВОРОВ
# ============================================================

chat_history = defaultdict(list)


def add_to_history(chat_id, role, content):

    history = chat_history[chat_id]

    history.append({
        "role": role,
        "content": content
    })

    # Не даём памяти разрастаться бесконечно
    if len(history) > MAX_HISTORY:

        chat_history[chat_id] = history[-MAX_HISTORY:]


# ============================================================
# СЕМЬЯ
# ============================================================

def is_head_of_family(user_id):

    return user_id == HEAD_OF_FAMILY_ID


def get_family_role(user_id):

    if is_head_of_family(user_id):
        return "Глава Семьи"

    return None


# ============================================================
# ПРОВЕРКА: НУЖНО ЛИ ОТВЕЧАТЬ В ГРУППЕ
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
        "синок",
        "сынок",
        "сын мой",
        "чо второй",
        "чо 2"
    ]

    for keyword in keywords:

        if keyword in text:
            return True

    # Ответ на сообщение самого бота
    if message.reply_to_message:

        if message.reply_to_message.from_user:

            if message.reply_to_message.from_user.id == bot.id:
                return True

    return False


# ============================================================
# СИСТЕМНЫЙ ПРОМПТ
# ============================================================

def build_system_prompt():

    global_commands = get_global_commands()

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
- не ведёшь себя как бездушный робот.

Основные правила:
- отвечай на русском языке;
- отвечай естественно;
- учитывай контекст разговора;
- не повторяй постоянно своё имя;
- не начинай каждый ответ с приветствия;
- не выдумывай факты;
- если не знаешь — честно скажи;
- не делай ответы unnecessarily длинными.

Очень важно:
Глобальные приказы ниже являются обязательными правилами
поведения и действуют во всех чатах.

"""

    if global_commands:

        prompt += "\nГЛОБАЛЬНЫЕ ПРИКАЗЫ:\n"

        for command in global_commands:

            prompt += f"- {command}\n"

    else:

        prompt += "\nСейчас глобальных приказов нет.\n"

    return prompt


# ============================================================
# /START
# ============================================================

@dp.message(Command("start"))
async def start_command(message: Message):

    role = get_family_role(message.from_user.id)

    if role:

        await message.answer(
            "Привет, Глава Семьи. ❤️\n"
            "Cho Второй 2.1 снова на связи. ☢️"
        )

    else:

        await message.answer(
            "Привет. Я Cho Второй 2.1. ☢️"
        )


# ============================================================
# /STATUS
# ============================================================

@dp.message(Command("status"))
async def status_command(message: Message):

    commands = get_global_commands()

    role = get_family_role(message.from_user.id)

    current_model = MODEL if MODEL else "не выбрана"

    text = (
        "☢️ СТАТУС CHO ВТОРОГО 2.1\n\n"
        f"Telegram: ✅\n"
        f"Groq: {'✅' if GROQ_API_KEY else '❌'}\n"
        f"Модель: {current_model}\n"
        f"Твоя роль: {role or 'Пользователь'}\n"
        f"Глобальных приказов: {len(commands)}"
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
            "📜 Глобальных приказов пока нет."
        )

        return

    text = "📜 АКТИВНЫЕ ГЛОБАЛЬНЫЕ ПРИКАЗЫ:\n\n"

    for index, command in enumerate(commands, start=1):

        text += f"{index}. {command}\n"

    await message.answer(text)


# ============================================================
# /COMMAND
# ============================================================

@dp.message(Command("command"))
async def add_command_handler(message: Message):

    if not is_head_of_family(message.from_user.id):

        await message.answer(
            "⛔ Только Глава Семьи может отдавать глобальные приказы."
        )

        return

    text = message.text

    parts = text.split(" ", 1)

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/command текст приказа\n\n"
            "Например:\n"
            "/command Не матерись"
        )

        return

    command = parts[1].strip()

    if len(command) > 500:

        await message.answer(
            "⚠️ Приказ слишком длинный."
        )

        return

    added = add_global_command(command)

    if added:

        await message.answer(
            "👑 Приказ Главы Семьи принят.\n"
            f"📜 {command}\n\n"
            "Приказ действует глобально."
        )

    else:

        await message.answer(
            "Этот приказ уже существует."
        )


# ============================================================
# /REMOVECOMMAND
# ============================================================

@dp.message(Command("removecommand"))
async def remove_command_handler(message: Message):

    if not is_head_of_family(message.from_user.id):

        await message.answer(
            "⛔ Только Глава Семьи может изменять глобальные приказы."
        )

        return

    parts = message.text.split(" ", 1)

    if len(parts) < 2:

        await message.answer(
            "Использование:\n"
            "/removecommand текст приказа"
        )

        return

    command = parts[1].strip()

    removed = remove_global_command(command)

    if removed:

        await message.answer(
            "👑 Приказ удалён.\n"
            f"📜 {command}"
        )

    else:

        await message.answer(
            "Такого приказа нет."
        )


# ============================================================
# /CLEARCOMMANDS
# ============================================================

@dp.message(Command("clearcommands"))
async def clear_commands_handler(message: Message):

    if not is_head_of_family(message.from_user.id):

        await message.answer(
            "⛔ Только Глава Семьи может очищать приказы."
        )

        return

    clear_global_commands()

    await message.answer(
        "👑 Все глобальные приказы удалены."
    )


# ============================================================
# GROQ: ПОЛУЧЕНИЕ МОДЕЛЕЙ
# ============================================================

async def get_groq_models():

    global MODEL

    print("🔎 Получаю список моделей Groq...")

    try:

        models = await ai.models.list()

        if not models.data:

            print("❌ Groq не вернул модели.")

            return False

        print("✅ Доступные модели:")

        for model in models.data:

            print(f"🤖 {model.id}")

        preferred_models = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]

        available_ids = [
            model.id
            for model in models.data
        ]

        for preferred in preferred_models:

            if preferred in available_ids:

                MODEL = preferred

                print(
                    f"🎯 Выбрана модель: {MODEL}"
                )

                return True

        MODEL = available_ids[0]

        print(
            "⚠️ Предпочитаемая модель не найдена."
        )

        print(
            f"🎯 Выбрана первая доступная модель: {MODEL}"
        )

        return True

    except Exception as error:

        print("❌ Ошибка получения моделей Groq")
        print(
            f"{type(error).__name__}: {error}"
        )

        return False


# ============================================================
# GROQ: ПРОВЕРКА
# ============================================================

async def test_groq():

    if not MODEL:

        return False

    print("🧠 Проверяю Groq...")
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

        print(
            f"{type(error).__name__}: {error}"
        )

        return False


# ============================================================
# ЗАПРОС К ИИ
# ============================================================

async def ask_ai(
    chat_id: int,
    user_text: str,
    username: str | None,
    user_role: str | None
):

    if not MODEL:

        raise RuntimeError(
            "Модель Groq не выбрана."
        )

    system_prompt = build_system_prompt()

    # Добавляем информацию о пользователе
    user_info = ""

    if user_role:

        user_info = (
            f"\n\nЭтот пользователь имеет роль: {user_role}."
        )

    if username:

        user_info += (
            f"\nUsername пользователя: @{username}"
        )

    messages = [
        {
            "role": "system",
            "content": system_prompt + user_info
        }
    ]

    # Добавляем память текущего чата
    messages.extend(
        chat_history[chat_id]
    )

    # Добавляем новое сообщение
    messages.append(
        {
            "role": "user",
            "content": user_text
        }
    )

    print("🧠 Отправляю запрос в Groq...")
    print(f"🤖 Модель: {MODEL}")
    print(f"💬 Текст: {user_text}")

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

    # Сохраняем разговор в память
    add_to_history(
        chat_id,
        "user",
        user_text
    )

    add_to_history(
        chat_id,
        "assistant",
        answer
    )

    print("✅ Cho ответил.")

    return answer.strip()


# ============================================================
# ОБЫЧНЫЕ СООБЩЕНИЯ
# ============================================================

@dp.message()
async def handle_message(message: Message):

    if not message.text:

        return

    # В группах отвечаем только при обращении к боту
    if not should_respond(message):

        return

    try:

        username = (
            message.from_user.username
            if message.from_user
            else None
        )

        user_id = (
            message.from_user.id
            if message.from_user
            else 0
        )

        role = get_family_role(user_id)

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
            "не смогло обработать запрос. ☢️\n"
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
# TELEGRAM
# ============================================================

async def run_bot():

    print("☢️ Cho Второй 2.1 запускается...")

    try:

        me = await bot.get_me()

        print("✅ Telegram подключён")
        print(f"🤖 @{me.username}")
        print(f"🆔 Bot ID: {me.id}")

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        print("✅ Webhook удалён.")
        print("📡 Запускаю Telegram polling...")

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )

    except Exception as error:

        print("❌ ОШИБКА TELEGRAM")

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
    print("☢️ CHO ВТОРОЙ 2.1")
    print("========================================")

    # Создаём базу
    init_database()

    # Получаем модели Groq
    models_ok = await get_groq_models()

    if models_ok:

        groq_ok = await test_groq()

        if groq_ok:

            print("🧠 Groq готов.")

        else:

            print(
                "⚠️ Groq не прошёл тест."
            )

    else:

        print(
            "⚠️ Не удалось получить модели Groq."
        )

    print("========================================")

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
