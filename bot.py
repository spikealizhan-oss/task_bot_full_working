# bot.py
import os
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

from db import init_db, add_task, get_tasks, get_task, update_task, delete_task
from ai import classify_task
from utils import parse_datetime, format_task
from scheduler import start_scheduler

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not TELEGRAM_TOKEN:
    print('Set TELEGRAM_TOKEN in .env or environment')
    raise SystemExit(1)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

init_db()

# simple in-memory pending states
pending_edit = {}       # user_id -> task_id
pending_deadline = {}   # user_id -> task_id

def task_kb(task_id: int):
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton('📝 Редактировать', callback_data=f'edit:{task_id}'),
        InlineKeyboardButton('📅 Дедлайн', callback_data=f'deadline_menu:{task_id}'),
        InlineKeyboardButton('⏰ Напоминание', callback_data=f'reminder_menu:{task_id}')
    )
    kb.add(
        InlineKeyboardButton('⭐ Приоритет', callback_data=f'priority_menu:{task_id}'),
        InlineKeyboardButton('🗂 Категория', callback_data=f'category_menu:{task_id}'),
        InlineKeyboardButton('✔ Выполнено', callback_data=f'done:{task_id}'),
    )
    kb.add(InlineKeyboardButton('❌ Удалить', callback_data=f'delete:{task_id}'))
    return kb

@dp.message_handler(commands=['start','help'])
async def cmd_start(message: types.Message):
    await message.reply(
        'Привет! Я — менеджер задач с inline-меню.\n'
        'Создать: /new Текст задачи | дедлайн (опционально)\n'
        'Показать: /list'
    )

@dp.message_handler(commands=['new'])
async def cmd_new(message: types.Message):
    payload = message.get_args()
    if not payload:
        await message.reply('Использование: /new Текст задачи | дедлайн (опционально)')
        return
    parts = payload.split('|')
    text = parts[0].strip()
    deadline = None
    if len(parts) >= 2:
        d = parse_datetime(parts[1].strip())
        if d:
            deadline = d
    ai = classify_task(text)
    priority = ai.get('priority')
    category = ai.get('category')
    task_id = add_task(message.from_user.id, text, deadline=deadline, priority=priority, category=category)
    await message.reply(f'Задача создана #{task_id}\nПриоритет: {priority}\nКатегория: {category}')

@dp.message_handler(commands=['list','active','done'])
async def cmd_list(message: types.Message):
    cmd = message.text.split()[0].lstrip('/')
    status = None
    if cmd == 'active': status = 'active'
    if cmd == 'done': status = 'done'
    tasks = get_tasks(message.from_user.id, status=status)
    if not tasks:
        await message.reply('Задач нет.')
        return
    for t in tasks:
        txt = format_task(t)
        await message.reply(txt, reply_markup=task_kb(t['id']))

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('edit:'))
async def cb_edit(query: types.CallbackQuery):
    uid = query.from_user.id
    tid = int(query.data.split(':')[1])
    pending_edit[uid] = tid
    await query.answer()
    await bot.send_message(uid, f'Отправь новый текст для задачи #{tid}')

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('deadline_menu:'))
async def cb_deadline_menu(query: types.CallbackQuery):
    tid = int(query.data.split(':')[1])
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton('Установить дедлайн (ввести дату)', callback_data=f'deadline_set:{tid}'))
    kb.add(InlineKeyboardButton('Удалить дедлайн', callback_data=f'deadline_clear:{tid}'))
    await query.answer()
    await bot.send_message(query.from_user.id, 'Меню дедлайна:', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('deadline_set:'))
async def cb_deadline_set(query: types.CallbackQuery):
    uid = query.from_user.id
    tid = int(query.data.split(':')[1])
    pending_deadline[uid] = tid
    await query.answer()
    await bot.send_message(uid, f'Отправь дату/время для дедлайна задачи #{tid} (например: 25 Nov 2025 18:00)')

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('deadline_clear:'))
async def cb_deadline_clear(query: types.CallbackQuery):
    tid = int(query.data.split(':')[1])
    update_task(query.from_user.id, tid, deadline=None)
    await query.answer('Дедлайн удалён')
    await bot.send_message(query.from_user.id, f'Дедлайн для #{tid} удалён')

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('reminder_menu:'))
async def cb_reminder_menu(query: types.CallbackQuery):
    tid = int(query.data.split(':')[1])
    kb = InlineKeyboardMarkup(row_width=3)
    # buttons: rem:minutes:taskid
    kb.add(InlineKeyboardButton('30 мин', callback_data=f'rem:30:{tid}'),
           InlineKeyboardButton('1 час', callback_data=f'rem:60:{tid}'),
           InlineKeyboardButton('1 день', callback_data=f'rem:1440:{tid}'))
    kb.add(InlineKeyboardButton('Удалить напоминание', callback_data=f'rem:clear:{tid}'))
    await query.answer()
    await bot.send_message(query.from_user.id, 'Выбери быстрый вариант напоминания:', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('rem:'))
async def cb_rem_fast(query: types.CallbackQuery):
    uid = query.from_user.id
    parts = query.data.split(':')  # ['rem','30','12'] or ['rem','clear','12']
    action = parts[1]
    tid = int(parts[2])
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    task = get_task(uid, tid)
    if action == 'clear':
        update_task(uid, tid, reminder_at=None)
        await query.answer('Напоминание удалено')
        await bot.send_message(uid, f'Напоминание для #{tid} удалено')
        return
    try:
        minutes = int(action)
    except:
        await query.answer('Ошибка формата')
        return
    rem_time = now + timedelta(minutes=minutes)
    if task and task.get('deadline'):
        try:
            dl = datetime.fromisoformat(task['deadline'])
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=timezone.utc)
            # if deadline earlier than desired reminder, shift reminder to before deadline by same minutes
            if dl < rem_time:
                rem_time = dl - timedelta(minutes=minutes)
        except Exception:
            pass
    reminder_iso = rem_time.astimezone(timezone.utc).isoformat()
    update_task(uid, tid, reminder_at=reminder_iso)
    await query.answer('Напоминание установлено')
    await bot.send_message(uid, f'Напоминание для задачи #{tid} установлено на {reminder_iso}')

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('priority_menu:'))
async def cb_priority_menu(query: types.CallbackQuery):
    tid = int(query.data.split(':')[1])
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(InlineKeyboardButton('низкий', callback_data=f'set_pr:низкий:{tid}'),
           InlineKeyboardButton('средний', callback_data=f'set_pr:средний:{tid}'),
           InlineKeyboardButton('высокий', callback_data=f'set_pr:высокий:{tid}'))
    await query.answer()
    await bot.send_message(query.from_user.id, 'Выбери приоритет:', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('set_pr:'))
async def cb_set_pr(query: types.CallbackQuery):
    parts = query.data.split(':')
    pr = parts[1]
    tid = int(parts[2])
    update_task(query.from_user.id, tid, priority=pr)
    await query.answer('Приоритет обновлён')
    await bot.send_message(query.from_user.id, f'Приоритет для #{tid} установлен: {pr}')

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('category_menu:'))
async def cb_category_menu(query: types.CallbackQuery):
    tid = int(query.data.split(':')[1])
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton('учёба', callback_data=f'set_cat:учёба:{tid}'),
           InlineKeyboardButton('работа', callback_data=f'set_cat:работа:{tid}'),
           InlineKeyboardButton('дом', callback_data=f'set_cat:дом:{tid}'),
           InlineKeyboardButton('личное', callback_data=f'set_cat:личное:{tid}'),
           InlineKeyboardButton('другое', callback_data=f'set_cat:другое:{tid}'))
    await query.answer()
    await bot.send_message(query.from_user.id, 'Выбери категорию:', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('set_cat:'))
async def cb_set_cat(query: types.CallbackQuery):
    parts = query.data.split(':')
    cat = parts[1]
    tid = int(parts[2])
    update_task(query.from_user.id, tid, category=cat)
    await query.answer('Категория обновлена')
    await bot.send_message(query.from_user.id, f'Категория для #{tid} установлена: {cat}')

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('done:'))
async def cb_done(query: types.CallbackQuery):
    tid = int(query.data.split(':')[1])
    update_task(query.from_user.id, tid, status='done')
    await query.answer('Отмечено как выполнено')
    await bot.send_message(query.from_user.id, f'Задача #{tid} помечена как выполненная')

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('delete:'))
async def cb_delete(query: types.CallbackQuery):
    tid = int(query.data.split(':')[1])
    delete_task(query.from_user.id, tid)
    await query.answer('Удалено')
    await bot.send_message(query.from_user.id, f'Задача #{tid} удалена')

@dp.message_handler(lambda m: m.from_user.id in pending_edit)
async def handle_edit_message(message: types.Message):
    uid = message.from_user.id
    tid = pending_edit.pop(uid)
    update_task(uid, tid, text=message.text)
    await message.reply(f'Текст задачи #{tid} обновлён.')

@dp.message_handler(lambda m: m.from_user.id in pending_deadline)
async def handle_deadline_message(message: types.Message):
    uid = message.from_user.id
    tid = pending_deadline.pop(uid)
    dt = parse_datetime(message.text)
    if not dt:
        await message.reply('Не удалось распознать дату. Попробуйте формат \"25 Nov 2025 18:00\" или ISO.')
        return
    update_task(uid, tid, deadline=dt)
    await message.reply(f'Дедлайн для #{tid} установлен: {dt}')

if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()
    interval = int(os.getenv('REMINDER_CHECK_INTERVAL_SECONDS','60'))
    start_scheduler(bot, interval_seconds=interval)
    print('Scheduler started...')
    executor.start_polling(dp, skip_updates=True)
