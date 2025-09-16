# -*- coding: utf-8 -*-
import os, json, logging, glob
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, ContextTypes, Defaults,
    CallbackQueryHandler, MessageHandler, filters
)

# импортируем только то, что точно есть
from misfortune import read_howl, render_reading

# пробуем мягко использовать иконки ветвей, если функции есть
try:
    from misfortune import ensure_icons, icon_filename
except Exception:
    ensure_icons = None
    icon_filename = None

# ===== Настройки =====
TIMEZONE_OFFSET_HOURS = 3   # поправь под свой пояс
LOCAL_TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DATA_FILE = "howls.json"

def _load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_data(db):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def _record(chat_id: int, dt: datetime, doom_code: str, level: int):
    db = _load_data()
    key = str(chat_id)
    db.setdefault(key, []).append({"ts": dt.isoformat(timespec="minutes"), "doom": doom_code, "lvl": level})
    db[key] = db[key][-5:]
    _save_data(db)

def _salt(chat_id: int) -> int:
    return abs(chat_id) % 97

# ===== Медиа-помощники =====
def pick_doom_image(code: str) -> str | None:
    """Ищем assets/<code>_*.png или assets/<code>.png"""
    candidates = sorted(glob.glob(os.path.join("assets", f"{code}_*.png")))
    if not candidates:
        one = os.path.join("assets", f"{code}.png")
        return one if os.path.exists(one) else None
    return candidates[0]

async def send_with_media(message, text_html: str, doom_code: str, branch_py: str):
    """Пробуем: арт категории -> иконка ветви -> просто текст"""
    # 1) арт категории
    p = pick_doom_image(doom_code)
    if p and os.path.exists(p):
        try:
            await message.reply_photo(photo=open(p, "rb"), caption=text_html, parse_mode=ParseMode.HTML)
            return
        except Exception as e:
            logging.warning("failed to send category art %s: %s", p, e)

    # 2) иконка ветви (если misfortune умеет)
    if ensure_icons and icon_filename:
        try:
            ensure_icons()
            ipath = icon_filename(branch_py)
            if os.path.exists(ipath):
                await message.reply_photo(photo=open(ipath, "rb"), caption=text_html, parse_mode=ParseMode.HTML)
                return
        except Exception as e:
            logging.warning("failed to send branch icon: %s", e)

    # 3) fallback: текст
    await message.reply_text(text_html, parse_mode=ParseMode.HTML)

# ===== Команды =====
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "<b>HOWL — бот несчастий</b>\n\n"
        "Услышал вой духа? Жми <b>«Гадать сейчас»</b> или <b>«Ввести момент»</b> — дату и время воя.\n"
        "Можно и командой: <code>/howl YYYY-MM-DD [HH:MM]</code>."
        f"\n\n<i>Часовой пояс бота:</i> UTC{TIMEZONE_OFFSET_HOURS:+d}:00"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔮 Гадать сейчас", callback_data="howl_now")],
        [InlineKeyboardButton("⌚ Ввести момент", callback_data="howl_ask")],
        [InlineKeyboardButton("🧾 Пять последних воев", callback_data="howl_last")],
    ])
    # приветственная картинка (если есть)
    welcome = "welcome.png"
    if os.path.exists(welcome):
        await update.message.reply_photo(photo=open(welcome, "rb"), caption=caption, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(caption, reply_markup=kb, parse_mode=ParseMode.HTML)

async def cmd_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    items = _load_data().get(str(chat_id), [])
    if not items:
        await update.message.reply_text("Пока пусто. Нажми «Гадать сейчас» или пришли момент.")
        return
    lines = [f"#{len(items)-i}. {it['ts']} — {it['doom']} (ур. {it['lvl']})" for i, it in enumerate(reversed(items))]
    await update.message.reply_text("<b>Пять последних воев</b>\n" + "\n".join(lines), parse_mode=ParseMode.HTML)

async def cmd_howl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    salt = _salt(chat_id)
    if context.args:
        try:
            if len(context.args) == 1:
                dt = datetime.strptime(context.args[0], "%Y-%m-%d")
            else:
                dt = datetime.strptime(context.args[0] + " " + context.args[1], "%Y-%m-%d %H:%M")
        except Exception:
            await update.message.reply_text("Формат: /howl YYYY-MM-DD [HH:MM]")
            return
    else:
        dt = update.message.date.astimezone(LOCAL_TZ).replace(tzinfo=None)

    r = read_howl(dt, salt=salt)
    await send_with_media(update.message, render_reading(r), r.doom["code"], r.branch_tuple[1])
    _record(chat_id, dt, r.doom["code"], r.doom_level)

# ===== Inline-поток =====
async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    await q.answer()

    if data == "howl_now":
        dt = datetime.now(tz=LOCAL_TZ).replace(tzinfo=None)
        chat_id = update.effective_chat.id
        salt = _salt(chat_id)
        r = read_howl(dt, salt=salt)
        await send_with_media(q.message, render_reading(r), r.doom["code"], r.branch_tuple[1])
        _record(chat_id, dt, r.doom["code"], r.doom_level)

    elif data == "howl_ask":
        prompt = "Пришлите момент в формате: <code>YYYY-MM-DD HH:MM</code> (местное время)"
        await q.message.reply_text(prompt, reply_markup=ForceReply(selective=True), parse_mode=ParseMode.HTML)

    elif data == "howl_last":
        await cmd_last(update, context)

# ловим ответ на ForceReply
async def on_reply_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.reply_to_message:
        return
    if "Пришлите момент в формате" not in (update.message.reply_to_message.text or ""):
        return
    chat_id = update.effective_chat.id
    salt = _salt(chat_id)
    txt = (update.message.text or "").strip()
    try:
        if " " in txt:
            dt = datetime.strptime(txt, "%Y-%m-%d %H:%M")
        else:
            dt = datetime.strptime(txt, "%Y-%m-%d")
    except Exception:
        await update.message.reply_text("Не понял формат. Пример: <code>2025-10-01 14:30</code>", parse_mode=ParseMode.HTML)
        return
    r = read_howl(dt, salt=salt)
    await send_with_media(update.message, render_reading(r), r.doom["code"], r.branch_tuple[1])
    _record(chat_id, dt, r.doom["code"], r.doom_level)

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("Установите TELEGRAM_TOKEN")

    app = Application.builder().token(token).defaults(Defaults(parse_mode=ParseMode.HTML)).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("howl", cmd_howl))
    app.add_handler(CommandHandler("last", cmd_last))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_reply_datetime))

    # Webhook (Render подставляет RENDER_EXTERNAL_URL)
    webhook_base = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL")
    port = int(os.getenv("PORT", "8080"))
    if webhook_base:
        webhook_url = webhook_base.rstrip("/") + "/" + token
        logging.info("Starting webhook at %s", webhook_url)
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=webhook_url,
        )
    else:
        logging.info("Starting long polling")
        app.run_polling()

if __name__ == "__main__":
    main()
