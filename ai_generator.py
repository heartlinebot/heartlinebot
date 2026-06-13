import os
import random
from datetime import datetime

# Якщо є OpenAI ключ — використовуємо GPT, інакше — шаблони
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

RELATION_MAP = {
    "mama":     "мамі",
    "tato":     "татові",
    "druzhyna": "коханій людині",
    "brat":     "брату або сестрі",
    "druh":     "другу або подрузі",
    "babusya":  "бабусі або дідусеві",
}

TONE_PROMPTS = {
    "warm":     "теплим, турботливим, від серця",
    "funny":    "веселим, з легким гумором",
    "romantic": "романтичним, ніжним",
    "calm":     "спокійним, заспокійливим",
    "neutral":  "нейтральним, але щирим",
}

# Шаблонні повідомлення для кожної комбінації (fallback без OpenAI)
TEMPLATES = {
    ("mama", "warm"): [
        "Мамо, привіт! Просто хотів нагадати, що думаю про тебе щодня. У мене все добре. Люблю тебе ❤️",
        "Мамусю, як ти там? Я в порядку, не хвилюйся. Скучаю за тобою 💙",
        "Привіт, мамо! Маленький знак того, що ти завжди в моїх думках. Все добре 🌸",
    ],
    ("mama", "funny"): [
        "Мамо, привіт! Ти в моїх думках — навіть коли я роблю щось, за що ти б посварила 😄 Люблю тебе!",
        "Привіт, мамо! Я живий, здоровий і навіть поїв сьогодні. Знаю, знаю — це твоя найбільша турбота 😂",
        "Мамо, хорошу новину: я ще не забув чистити зуби. Погана новина: забув зателефонувати раніше 😅 Люблю!",
    ],
    ("mama", "romantic"): [
        "Мамо, ти — найважливіша людина в моєму житті. Дякую, що ти є 🌷",
        "Мамусю, іноді я закриваю очі і чую твій голос. Це найкращий звук у світі ❤️",
    ],
    ("mama", "calm"): [
        "Мамо, привіт. Просто хочу, щоб ти знала — у мене все добре. Не хвилюйся 🕊",
        "Мамусю, все спокійно. Я в порядку і думаю про тебе. Бережи себе 💙",
    ],
    ("mama", "neutral"): [
        "Мамо, привіт! Все нормально з мого боку. Як ти?",
        "Привіт, мамо. Пишу, щоб ти знала — у мене все добре.",
    ],
    ("tato", "warm"): [
        "Тату, привіт! Думаю про тебе. Все добре, тримаюся 💪",
        "Привіт, тату! Хотів просто нагадати, що ти завжди в моїх думках ❤️",
    ],
    ("tato", "funny"): [
        "Тату, привіт! Я в порядку — поради, які ти давав, ще діють 😄",
        "Привіт, тату! Живий, здоровий, твій характер успадкував — тримаюся 😂",
    ],
    ("druzhyna", "romantic"): [
        "Кохана, думаю про тебе кожну хвилину 💕 Скучаю.",
        "Привіт, моя рідна. Просто хотів сказати — люблю тебе. Завжди ❤️",
        "Ти — моє найкраще, що є. Скучаю і думаю про тебе 🌹",
    ],
    ("druzhyna", "warm"): [
        "Привіт, кохана! Все добре з мого боку. Думаю про тебе і скучаю 💙",
        "Рідна, як ти там? У мене все нормально. Дуже жду зустрічі ❤️",
    ],
    ("brat", "funny"): [
        "Бро, живий! Як сам? 😄",
        "Привіт! Нагадую про своє існування 😂 Все ок, тримаюся!",
    ],
    ("brat", "warm"): [
        "Привіт! Думаю про тебе. Все добре, тримаємося 💪",
        "Хей! Просто хотів написати — у мене все ок. Як ти? ❤️",
    ],
    ("druh", "funny"): [
        "Хей! Ще живий і не забув про тебе 😄 Як справи?",
        "Бро/подруго, привіт! Нагадую, що існую 😂 Все ок!",
    ],
    ("druh", "warm"): [
        "Привіт! Думаю про тебе. Все добре ❤️",
        "Хей! Просто написати — у мене все добре. Як ти? 😊",
    ],
    ("babusya", "warm"): [
        "Бабусю, привіт! Я в порядку, не хвилюйся. Думаю про тебе і дуже люблю 🌸",
        "Привіт, рідна! Все добре зі мною. Бережи себе 💙",
    ],
    ("babusya", "calm"): [
        "Бабусю, все спокійно. Я здоровий і думаю про тебе 🕊",
        "Привіт! Все добре, не переживай. Люблю тебе ❤️",
    ],
}


async def generate_message(recipient_name: str, relation: str, tone: str,
                            city: str = "", weather: str = "") -> str:
    weather_line = ""
    if city and weather:
        weather_line = f"Сьогодні в {city}: {weather}. "

    # Спробувати OpenAI якщо є ключ
    if OPENAI_API_KEY:
        try:
            return await _generate_with_gpt(
                recipient_name, relation, tone, city, weather_line
            )
        except Exception:
            pass

    # Fallback — шаблони
    return _generate_from_template(recipient_name, relation, tone, weather_line)


async def _generate_with_gpt(name, relation, tone, city, weather_line):
    import httpx
    relation_ua = RELATION_MAP.get(relation, "близькій людині")
    tone_ua = TONE_PROMPTS.get(tone, "щирим")

    prompt = (
        f"Напиши коротке особисте повідомлення від першої особи для {relation_ua} на ім'я {name}. "
        f"Тон: {tone_ua}. "
        f"{'Додай інформацію: ' + weather_line if weather_line else ''}"
        f"Повідомлення має бути не більше 3 речень, живим, щирим. "
        f"Не використовуй шаблонні фрази типу 'Дорога мамо'. "
        f"Писати українською мовою."
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.85,
            },
            timeout=15
        )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


def _generate_from_template(name, relation, tone, weather_line):
    key = (relation, tone)
    fallback_key = (relation, "warm")

    templates = TEMPLATES.get(key) or TEMPLATES.get(fallback_key) or [
        f"Привіт, {name}! У мене все добре. Думаю про тебе ❤️"
    ]

    text = random.choice(templates)

    # Вставити ім'я якщо немає звертання
    if name and name.lower() not in text.lower():
        text = text  # ім'я вже у шаблонах через звертання

    # Додати погоду
    if weather_line:
        text = weather_line + text

    return text
