# utils.py
from datetime import datetime, timezone
import dateutil.parser

def parse_datetime(text: str):
    """Попытка распарсить дату/время. Возвращает ISO string in UTC или None."""
    if not text:
        return None
    try:
        dt = dateutil.parser.parse(text, dayfirst=True)
        # convert to UTC ISO
        if dt.tzinfo is None:
            # assume local, convert to UTC
            dt = dt.replace(tzinfo=timezone.utc)
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.isoformat()
    except Exception:
        return None

def format_task(t: dict) -> str:
    reminder = t.get('reminder_at') or '—'
    deadline = t.get('deadline') or '—'
    return (
        f"🆔 ID: {t['id']}\n"
        f"📌 Текст: {t['text']}\n"
        f"📅 Дедлайн: {deadline}\n"
        f"⏰ Напоминание: {reminder}\n"
        f"⭐ Приоритет: {t.get('priority','—')}\n"
        f"🗂 Категория: {t.get('category','—')}\n"
        f"Статус: {t.get('status','active')}\n"
    )
