import os


BOT_TOKEN = os.getenv("BOT_TOKEN")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

PORT = int(
    os.getenv("PORT", "10000")
)
