# ai.py
import os
import openai
import json

openai.api_key = os.getenv("OPENAI_API_KEY") or None

CATEGORY_CHOICES = ["учёба", "работа", "дом", "личное", "другое"]
PRIORITY_CHOICES = ["низкий", "средний", "высокий"]

SYSTEM_PROMPT = f"""    Ты — классификатор задач. На вход приходит краткое описание задачи.
Верни строго JSON в формате:
{{"category": "<одна из: {', '.join(CATEGORY_CHOICES)}>","priority":"<одна из: {', '.join(PRIORITY_CHOICES)}>"}}.
Если не уверен, используй "другое" для category и "низкий" для priority.
Ничего больше, только валидный JSON.
"""

def classify_task(text: str) -> dict:
    # Если ключ OpenAI не задан — fallback на rule-based
    if not openai.api_key:
        return rule_based(text)
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role":"system", "content": SYSTEM_PROMPT},
                {"role":"user", "content": text}
            ],
            temperature=0
        )
        content = resp["choices"][0]["message"]["content"].strip()
        try:
            data = json.loads(content)
            category = data.get("category") if data.get("category") in CATEGORY_CHOICES else "другое"
            priority = data.get("priority") if data.get("priority") in PRIORITY_CHOICES else "низкий"
            return {"category": category, "priority": priority}
        except Exception:
            return rule_based(text)
    except Exception:
        return rule_based(text)

def rule_based(text: str) -> dict:
    t = text.lower()
    category = "другое"
    if any(w in t for w in ["дз","контрольн","семинар","лаб","учеб","урок","задач","экзамен","курсов"]):
        category = "учёба"
    elif any(w in t for w in ["работ","заказ","встреч","дедлайн","проект","клиент","заплат"]):
        category = "работа"
    elif any(w in t for w in ["убор","посуд","магазин","ремонт","домаш","купить","прач"]):
        category = "дом"
    elif any(w in t for w in ["себя","спорт","хобби","отдых","звонок маме","позвон","личн"]):
        category = "личное"

    priority = "низкий"
    if any(w in t for w in ["срочно","как можно скорее","немедлен","очень важно","вчера"]):
        priority = "высокий"
    elif any(w in t for w in ["важн","в приоритете","нужно"]):
        priority = "средний"
    return {"category": category, "priority": priority}
