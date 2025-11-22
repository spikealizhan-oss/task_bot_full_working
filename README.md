# Telegram Task Manager Bot — Full Working Version (Variant A inline)
Полный рабочий проект с inline-меню, редактированием задач и быстрыми напоминаниями (30м/1ч/1д).
Файлы проекта (включён локальный PDF, который ты загружал): /mnt/data/проект КМ04 (1).pdf

## Быстрый старт (Windows)
1. Распакуй архив.
2. Создай `.env` рядом с `bot.py` и вставь туда:
   TELEGRAM_TOKEN=твой_новый_токен_бота
   OPENAI_API_KEY=твой_новый_openai_ключ
   REMINDER_CHECK_INTERVAL_SECONDS=60
3. Создай виртуальное окружение и активируй (PowerShell):
   python -m venv venv
   .\venv\Scripts\activate
4. Установи зависимости:
   pip install -r requirements.txt
5. Запусти:
   python bot.py

## Функции
- Создание задач: /new Текст | дедлайн (опционально)
- Список задач: /list, /active, /done
- Inline-кнопки под каждой задачей: редактирование, дедлайн, напоминание (30м/1ч/1д), приоритет, категория, выполнить, удалить
- Классификация задачи: через OpenAI (при наличии ключа) + fallback rule-based
- Напоминания сохраняются в ISO (UTC) и отправляются APScheduler'ом
