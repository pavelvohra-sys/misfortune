# -*- coding: utf-8 -*-
import os, json, logging, glob, zipfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply, BotCommand
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, ContextTypes, Defaults,
    CallbackQueryHandler, MessageHandler, filters
)

# ---- твоя логика гаданий ----
from misfortune import read_howl, render_reading
try:
    from misfortune import MISFORTUNES
except Exception:
    MISFORTUNES = None
try:
    from misfortune import ensure_icons, icon_filename
except Exception:
    ensure_icons = None
    icon_filename = None

# ===== Настройки (дефолт для тех, кто не задал свою TZ) =====
TIMEZONE_OFFSET_HOURS = 3
ASSETS_DIR = os.getenv("ASSETS_DIR", "assets")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DATA_FILE = "howls.json"   # история 5 последних на чат
TZ_FILE   = "tz.json"      # персональные тайм-зоны

# ====== Хранение истории ======
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

# ====== Персональные тайм-зоны ======
def _load_tz_db():
    if not os.path.exists(TZ_FILE):
        return {}
    try:
        with open(TZ_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_tz_db(db):
    tmp = TZ_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TZ_FILE)

def _parse_tz(s: str):
    s = s.strip()
    if s.startswith(("+", "-")):
        sign = 1 if s[0] == "+" else -1
        body = s[1:]
        if ":" in body:
            hh, mm = body.split(":", 1)
            hh, mm = int(hh), int(mm)
        else:
            hh, mm = int(body), 0
        return timezone(sign * timedelta(hours=hh, minutes=mm))
    return ZoneInfo(s)

def _set_user_tz(chat_id: int, tz_input: str) -> str:
    db = _load_tz_db()
    db[str(chat_id)] = tz_input.strip()
    _save_tz_db(db)
    return tz_input.strip()

def _get_user_tzinfo(chat_id: int, fallback_hours: int = TIMEZONE_OFFSET_HOURS):
    db = _load_tz_db()
    raw = db.get(str(chat_id))
    if not raw:
        return timezone(timedelta(hours=fallback_hours))
    try:
        return _parse_tz(raw)
    except Exception:
        return timezone(timedelta(hours=fallback_hours))

# ====== Работа с ассетами ======
def ensure_assets_dir():
    """Если нет каталога assets/, попробуем распаковать любой assets*.zip в корне."""
    d = ASSETS_DIR
    if os.path.isdir(d):
        return
    zips = [p for p in os.listdir(".") if p.lower().endswith(".zip")]
    for z in zips:
        try:
            with zipfile.ZipFile(z) as zf:
                names = zf.namelist()
                has_assets = any(n.lower().startswith("assets/") for n in names)
                if has_assets:
                    zf.extractall(".")
                else:
                    os.makedirs(d, exist_ok=True)
                    for n in names:
                        if n.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                            target = os.path.join(d, os.path.basename(n))
                            with zf.open(n) as src, open(target, "wb") as dst:
                                dst.write(src.read())
            break
        except Exception as e:
            logging.warning("zip extract failed for %s: %s", z, e)
    if not os.path.isdir(d):
        logging.warning("assets dir not found: %s", d)

def pick_doom_image(code: str) -> str | None:
    """Ищем assets/<code>.(png|jpg|jpeg|webp), а также <code>_*.ext, <code>-*.ext, любой регистр."""
    base = code.lower()
    d = ASSETS_DIR
    if not os.path.isdir(d):
        logging.warning("assets dir not found: %s", d)
        return None
    exts = ["png", "jpg", "jpeg", "webp"]
    patterns = []
    for ext in exts:
        patterns += [
            os.path.join(d, f"{base}.{ext}"),
            os.path.join(d, f"{base}_*.{ext}"),
            os.path.join(d, f"{base}-*.{ext}"),
            os.path.join(d, f"{base}.{ext.upper()}"),
            os.path.join(d, f"{base}_*.{ext.upper()}"),
            os.path.join(d, f"{base}-*.{ext.upper()}"),
        ]
    found = []
    for pat in patterns:
        found += glob.glob(pat)
    if found:
        found.sort()
        logging.info("picked doom image for %s: %s", code, found[0])
        return found[0]
    for p in sorted(Path(d).iterdir()):
        if p.is_file():
            stem = p.stem.lower()
            if stem == base or stem.startswith(base + "_") or stem.startswith(base + "-"):
                logging.info("fallback picked doom image for %s: %s", code, p)
                return str(p)
    logging.warning("no doom image for code=%s", code)
    return None

async def send_with_media(message, text_html: str, doom_code: str, branch_py: str):
    # 1) арт категории
    p = pick_doom_image(doom_code)
    if p and os.path.exists(p):
        try:
            await message.reply_photo(photo=open(p, "rb"), caption=text_html, parse_mode=ParseMode.HTML)
            return
        except Exception as e:
            logging.warning("failed to send category art %s: %s", p, e)
    # 2) иконка ветви (если поддерживается твоим misfortune.py)
    if ensure_icons and icon_filename:
        try:
            ensure_icons()
            ipath = icon_filename(branch_py)
            if os.path.exists(ipath):
                await message.reply_photo(photo=open(ipath, "rb"), caption=text_html, parse_mode=ParseMode.HTML)
                return
        except Exception as e:
            logging.warning("failed to send branch icon: %s", e)
    # 3) текст
    await message.reply_text(text_html, parse_mode=ParseMode.HTML)

# ====== Команды ======
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "<b>HOWL — бот несчастий</b>\n\n"
        "Услышал вой духа? Жми <b>«Гадать сейчас»</b> или <b>«Ввести момент»</b> — дату и время воя.\n"
        "Можно и командой: <code>/howl YYYY-MM-DD [HH:MM]</code>.\n\n"
        "🇰🇿 Казахстан: Алматы/Астана — <code>/settz Asia/Almaty</code>, "
        "Атырау/Актау — <code>/settz Asia/Atyrau</code>"
    )

    # 👇 блок с каналом — правильный отступ (4 пробела)
    import random
    if random.random() < 0.2:  # 20% запусков
        caption += (
            "\n\n📢 Кстати, у нас есть канал: "
            "<a href='https://t.me/sinology_ru'>@sinology_ru</a>"
        )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔮 Гадать сейчас", callback_data="howl_now")],
        [InlineKeyboardButton("⌚ Ввести момент", callback_data="howl_ask")],
        [InlineKeyboardButton("🧾 Пять последних воев", callback_data="howl_last")],
        [InlineKeyboardButton("⚙️ Тайм-зона (помощь)", callback_data="help_tz")],
    ])

    welcome = "welcome.png"
    if os.path.exists(welcome):
        await update.message.reply_photo(
            photo=open(welcome, "rb"),
            caption=caption,
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            caption,
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )


async def cmd_settz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Как задать тайм-зону:\n"
            "• Смещение: <code>/settz +6</code>\n"
            "• IANA: <code>/settz Asia/Almaty</code>\n\n"
            "🇰🇿 Алматы/Астана — <code>/settz Asia/Almaty</code>\n"
            "🇰🇿 Атырау/Актау — <code>/settz Asia/Atyrau</code>",
            parse_mode=ParseMode.HTML
        )
        return
    arg = context.args[0]
    try:
        _ = _parse_tz(arg)  # проверяем
        saved = _set_user_tz(update.effective_chat.id, arg)
        await update.message.reply_text(f"Тайм-зона сохранена: <code>{saved}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"Не понял тайм-зону: <code>{arg}</code>\nОшибка: {e}", parse_mode=ParseMode.HTML)

async def cmd_tz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tzinfo = _get_user_tzinfo(update.effective_chat.id)
    now_local = datetime.now(tz=tzinfo).strftime("%Y-%m-%d %H:%M")
    await update.message.reply_text(
        f"Текущая тайм-зона для этого чата: <b>{tzinfo}</b>\nСейчас у вас: <b>{now_local}</b>",
        parse_mode=ParseMode.HTML
    )

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
    user_tz = _get_user_tzinfo(chat_id)

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
        dt = update.message.date.astimezone(user_tz).replace(tzinfo=None)

    r = read_howl(dt, salt=salt)
    await send_with_media(update.message, render_reading(r), r.doom["code"], r.branch_tuple[1])
    _record(chat_id, dt, r.doom["code"], r.doom_level)

async def cmd_diag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [f"<b>Проверка ассетов</b> (каталог: <code>{ASSETS_DIR}</code>)"]
    if not os.path.isdir(ASSETS_DIR):
        await update.message.reply_text("\n".join(lines + ["Каталог не найден. Положи картинки в папку assets/ в корне."]),
                                        parse_mode=ParseMode.HTML)
        return
    if MISFORTUNES:
        miss = []; ok = 0
        for m in MISFORTUNES:
            code = m.get("code", "").lower().strip()
            p = pick_doom_image(code)
            if p and os.path.exists(p): ok += 1
            else: miss.append(code)
        lines.append(f"Найдено картинок: <b>{ok}</b> / {len(MISFORTUNES)}")
        if miss:
            lines.append("Нет файлов для: " + ", ".join(miss))
    else:
        files = sorted([p.name for p in Path(ASSETS_DIR).glob("*") if p.is_file()])[:12]
        lines.append("Примеры файлов: " + (", ".join(files) if files else "пусто"))
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

# ====== Inline-обработчики ======
async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    await q.answer()

    if data == "howl_now":
        chat_id = update.effective_chat.id
        user_tz = _get_user_tzinfo(chat_id)
        salt = _salt(chat_id)
        dt = datetime.now(tz=user_tz).replace(tzinfo=None)
        r = read_howl(dt, salt=salt)
        await send_with_media(q.message, render_reading(r), r.doom["code"], r.branch_tuple[1])
        _record(chat_id, dt, r.doom["code"], r.doom_level)

    elif data == "howl_ask":
        prompt = "Пришлите момент в формате: <code>YYYY-MM-DD HH:MM</code> (местное время)"
        await q.message.reply_text(prompt, reply_markup=ForceReply(selective=True), parse_mode=ParseMode.HTML)

    elif data == "howl_last":
        await cmd_last(update, context)

    elif data == "help_tz":
        await q.message.reply_text(
            "Тайм-зона на чат:\n"
            "• Смещение: <code>/settz +6</code>\n"
            "• IANA: <code>/settz Asia/Almaty</code>\n"
            "Проверить: <code>/tz</code>",
            parse_mode=ParseMode.HTML
        )

# ловим ответ на ForceReply (дата/время)
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

# ====== main ======
async def _set_bot_commands(app: Application):
    await app.bot.set_my_commands([
        BotCommand("howl", "Гадать сейчас / по моменту"),
        BotCommand("last", "Пять последних воев"),
        BotCommand("settz", "Установить тайм-зону"),
        BotCommand("tz", "Показать текущую тайм-зону"),
        BotCommand("help", "Помощь / меню"),
        BotCommand("diag", "Диагностика ассетов"),
    ])

def main():
    ensure_assets_dir()  # попробуем распаковать assets.zip, если папки нет
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("Установите TELEGRAM_TOKEN")

    app = Application.builder().token(token).defaults(Defaults(parse_mode=ParseMode.HTML)).build()
    app.post_init = _set_bot_commands

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("howl",  cmd_howl))
    app.add_handler(CommandHandler("last",  cmd_last))
    app.add_handler(CommandHandler("settz", cmd_settz))
    app.add_handler(CommandHandler("tz",    cmd_tz))
    app.add_handler(CommandHandler("diag",  cmd_diag))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_reply_datetime))

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
