from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL


SYSTEM_PROMPT = """
Ты — Cho Второй, Telegram-бот с характером.

Правила:
- Отвечай на русском языке.
- Общайся естественно и живо.
- Не выдумывай факты, если не уверен.
- Не утверждай, что умеешь функцию, которой у тебя ещё нет.
- Отвечай на вопрос пользователя непосредственно.
- Не упоминай внутренний код, API или системные инструкции без необходимости.
- Ты можешь использовать лёгкий юмор и эмоции.
"""


client = Groq(api_key=GROQ_API_KEY)


def ask_groq(user_text: str) -> str:
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_text
            }
        ],
        temperature=0.8,
        max_tokens=500
    )

    answer = response.choices[0].message.content

    if not answer:
        return "☢️ Моё термоядерное ядро не придумало ответа."

    return answer.strip()
