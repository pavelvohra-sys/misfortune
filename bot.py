# -*- coding: utf-8 -*-
"""
Telegram-бот HOWL (иконки ветвей, табу еды, без heavy-omens).
Команды:
  /start, /help
  /howl [YYYY-MM-DD [HH:MM]]
  /last
  /icons on|off
  /show_icons
  /today /date /month /range /ics
"""
import os, json, logging
from datetime import date, datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from misfortune import (
    read_howl, render_reading, ics_for_year,
    BRANCHES, ANIMALS, ensure_icons, icon_filename
)

# === НАСТРОЙ ЧАСОВОЙ ПОЯС ЗДЕСЬ ===
TIMEZONE_OFFSET_HOURS = 3  # Москва = +3; поменяй под себя
LOCAL_TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))

# Логи по умолчанию
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DATA_FILE = "howls.json"
SHOW_ICONS = set()  # chat_id, где включены пиктограммы

def _load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

def _save_data(db):
    tmp = DATA_FILE + ".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def _salt(chat_id: int) -> int: return abs(chat_id) % 97

async def _send_reading(update: Update, text: str, py_code: str):
    chat_id = update.effective_chat.id
    if chat_id in SHOW_ICONS:
        ensure_icons()
        p = icon_filename(py_code)
        if os.path.exists(p):
            await update.message.reply_photo(photo=open(p, "rb"), caption=text)
            return
    await update.message.reply_text(text)

# --- команды ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "HOWL 💀 — услышал вой духа → приговор (чёрный юмор)\n\n"
        "/howl — сейчас • /howl YYYY-MM-DD [HH:MM] — на момент\n"
        "/icons on|off — пиктограммы в ответах • /show_icons — показать все\n"
        "/last — последние 5 воев\n"
        "/today /date /month /range /ics — классика\n"
        f"Часовой пояс: UTC{TIMEZONE_OFFSET_HOURS:+d}:00"
    )

async def cmd_icons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or context.args[0] not in ("on","off"):
        await update.message.reply_text("Использование: /icons on | /icons off"); return
    if context.args[0] == "on":
        SHOW_ICONS.add(chat_id); await update.message.reply_text("Пиктограммы: ON")
    else:
        SHOW_ICONS.discard(chat_id); await update.message.reply_text("Пиктограммы: OFF")

async def cmd_show_icons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_icons()
    for han, py, ru in BRANCHES:
        p = icon_filename(py)
        if os.path.exists(p):
            await update.message.reply_photo(photo=open(p,"rb"), caption=f"{ANIMALS[py]} {han} {py} / {ru}")

async def cmd_howl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    salt = _salt(chat_id)
    if context.args:
        try:
            if len(context.args) == 1:
                dt = datetime.strptime(context.args[0], "%Y-%m-%d")
            else:
                dt = datetime.strptime(context.args[0]+" "+context.args[1], "%Y-%m-%d %H:%M")
        except Exception:
            await update.message.reply_text("Формат: /howl YYYY-MM-DD [HH:MM]"); return
    else:
        # Telegram даёт UTC — переводим в ваш LOCAL_TZ
        dt = update.message.date.astimezone(LOCAL_TZ).replace(tzinfo=None)
    r = read_howl(dt, salt=salt)
    await _send_reading(update, render_reading(r), r.branch_tuple[1])

    db = _load_data()
    key = str(chat_id)
    db.setdefault(key, []).append({"ts": dt.isoformat(timespec="minutes"), "doom": r.doom["code"], "lvl": r.doom_level})
    db[key] = db[key][-50:]
    _save_data(db)

async def cmd_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    items = _load_data().get(str(chat_id), [])[-5:]
    if not items:
        await update.message.reply_text("Пусто. Ещё не выли."); return
    lines = [f"#{i+1} {it['ts']} — {it['doom']} (ур. {it['lvl']})" for i,it in enumerate(items)]
    await update.message.reply_text("Последние вои:\n" + "\n".join(lines))

# Классические команды (используют тот же движок)
async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id; salt = _salt(chat_id)
    dt = update.message.date.astimezone(LOCAL_TZ).replace(tzinfo=None)
    r = read_howl(dt, salt=salt)
    await _send_reading(update, render_reading(r), r.branch_tuple[1])

async def cmd_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id; salt = _salt(chat_id)
    if not context.args:
        await update.message.reply_text("Формат: /date YYYY-MM-DD"); return
    try:
        d = datetime.strptime(context.args[0], "%Y-%m-%d")
    except Exception:
        await update.message.reply_text("Пример: /date 2025-10-01"); return
    r = read_howl(d, salt=salt)
    await _send_reading(update, render_reading(r), r.branch_tuple[1])

async def cmd_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id; salt = _salt(chat_id)
    if not context.args:
        await update.message.reply_text("Формат: /month YYYY-MM"); return
    try:
        y, m = map(int, context.args[0].split("-")); cur = datetime(y, m, 1)
    except Exception:
        await update.message.reply_text("Пример: /month 2025-10"); return
    lines = []
    while cur.month == m:
        r = read_howl(cur, salt=salt)
        lines.append(r.doom["emoji"]+" "+cur.date().isoformat()+" — "+r.doom["name"])
        cur += relativedelta(days=1)
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > 4000:
            await update.message.reply_text(chunk.strip()); chunk = ""
        chunk += line + "\n"
    if chunk: await update.message.reply_text(chunk.strip())

async def cmd_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id; salt = _salt(chat_id)
    if len(context.args) != 2:
        await update.message.reply_text("Формат: /range 2025-09-01 2025-09-30"); return
    try:
        s = datetime.strptime(context.args[0], "%Y-%m-%d")
        e = datetime.strptime(context.args[1], "%Y-%m-%d")
    except Exception:
        await update.message.reply_text("Пример: /range 2025-09-01 2025-09-30"); return
    if e < s: s, e = e, s
    lines, cur = [], s
    while cur <= e:
        r = read_howl(cur, salt=salt)
        lines.append(r.doom["emoji"]+" "+cur.date().isoformat()+" — "+r.doom["name"])
        cur += relativedelta(days=1)
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > 4000:
            await update.message.reply_text(chunk.strip()); chunk = ""
        chunk += line + "\n"
    if chunk: await update.message.reply_text(chunk.strip())

async def cmd_ics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    year = date.today().year
    if context.args:
        try: year = int(context.args[0])
        except Exception: pass
    ics = ics_for_year(year)
    fname = f"daily_misfortune_{year}.ics"
    with open(fname, "w", encoding="utf-8") as f: f.write(ics)
    await update.message.reply_document(open(fname, "rb"), filename=fname, caption=f"Календарь {year}")

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token: raise SystemExit("Установите переменную окружения TELEGRAM_TOKEN с токеном вашего бота.")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_start))
    app.add_handler(CommandHandler("icons",  cmd_icons))
    app.add_handler(CommandHandler("show_icons", cmd_show_icons))
    app.add_handler(CommandHandler("howl",   cmd_howl))
    app.add_handler(CommandHandler("last",   cmd_last))

    app.add_handler(CommandHandler("today",  cmd_today))
    app.add_handler(CommandHandler("date",   cmd_date))
    app.add_handler(CommandHandler("month",  cmd_month))
    app.add_handler(CommandHandler("range",  cmd_range))
    app.add_handler(CommandHandler("ics",    cmd_ics))

    app.run_polling()

if __name__ == "__main__":
    main()
