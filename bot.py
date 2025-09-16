# -*- coding: utf-8 -*-
import os, logging
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, ContextTypes, Defaults,
    CallbackQueryHandler, MessageHandler, filters
)

# ===== Настройки =====
TIMEZONE_OFFSET_HOURS = 3   # поправь под свой пояс
LOCAL_TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ===== Временный "оракул" =====
def fake_reading(dt: datetime) -> str:
    return f"Вой духов от {dt.strftime('%Y-%m-%d %H:%M')} предвещает несчастье. 💀"

# ===== Команды =====
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "<b>HOWL — бот несчастий</b>\n\n"
        "Услышал вой духа? Жми <b>«Гадать сейчас»</b> или <b>«Ввести момент»</b>.\n"
        "Можно и командой: <code>/howl YYYY-MM-DD [HH:MM]</code>."
        f"\n\n<i>Часовой пояс бота:</i> UTC{TIMEZONE_OFFSET_HOURS:+d}:00"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Гадать сейчас", callback_data="howl_now")],
        [InlineKeyboardButton("Ввести момент", callback_data="howl_ask")],
    ])
    await update.message.reply_text(caption, reply_markup=kb)

async def cmd_howl(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    await update.message.reply_text(fake_reading(dt))

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "howl_now":
        dt = datetime.now(tz=LOCAL_TZ).replace(tzinfo=None)
        await q.message.reply_text(fake_reading(dt))
    elif q.data == "howl_ask":
        prompt = "Пришлите момент в формате: <code>YYYY-MM-DD HH:MM</code>"
        await q.message.reply_text(prompt, reply_markup=ForceReply(selective=True))

async def on_reply_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    try:
        if " " in txt:
            dt = datetime.strptime(txt, "%Y-%m-%d %H:%M")
        else:
            dt = datetime.strptime(txt, "%Y-%m-%d")
    except Exception:
        await update.message.reply_text("Не понял формат. Пример: <code>2025-10-01 14:30</code>")
        return
    await update.message.reply_text(fake_reading(dt))

# ===== main =====
def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("Установите TELEGRAM_TOKEN")

    app = Application.builder().token(token).defaults(Defaults(parse_mode=ParseMode.HTML)).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("howl", cmd_howl))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_reply_datetime))

    port = int(os.getenv("PORT", "8080"))
    webhook_base = os.getenv("RENDER_EXTERNAL_URL")
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
