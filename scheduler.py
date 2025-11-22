# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from db import tasks_with_upcoming_reminder, update_task

scheduler = AsyncIOScheduler()

async def send_reminders(bot):
    now = datetime.now(timezone.utc).isoformat()
    tasks = tasks_with_upcoming_reminder(now)
    for t in tasks:
        user_id = t['user_id']
        text = t['text']
        deadline = t.get('deadline')
        msg = f"🔔 Напоминание по задаче #{t['id']}:\n{text}"
        if deadline:
            msg += f"\nДедлайн: {deadline}"
        try:
            await bot.send_message(user_id, msg)
            # clear reminder to avoid repeats
            update_task(user_id, t['id'], reminder_at=None)
        except Exception as e:
            print('Failed to send reminder:', e)

def start_scheduler(bot, interval_seconds=60):
    scheduler.add_job(send_reminders, 'interval', seconds=interval_seconds, args=[bot], max_instances=1)
    scheduler.start()
