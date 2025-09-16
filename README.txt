# «Несчастье на каждый день» — Telegram-бот

## Состав
- **bot.py** — бот
- **misfortune.py** — логика (12-дневный цикл и тексты несчастий)
- **requirements.txt** — зависимости

## Что нужно
- Python 3.9+
- Токен бота от @BotFather

## Установка и запуск

### Windows (PowerShell)
1. Создать папку и положить туда файлы `bot.py`, `misfortune.py`, `requirements.txt`.
2. Открыть PowerShell в этой папке и выполнить:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   $env:TELEGRAM_TOKEN="ВАШ_ТОКЕН_ОТ_BOTFATHER"
   python bot.py
   ```
   > Если команда `python` не найдена — попробуйте `py`.

### macOS / Linux
1. Открыть терминал в папке с файлами и выполнить:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   export TELEGRAM_TOKEN="ВАШ_ТОКЕН_ОТ_BOTFATHER"
   python3 bot.py
   ```

## Команды бота
- `/start`, `/help` — помощь
- `/today` — несчастье на сегодня
- `/date YYYY-MM-DD` — на дату
- `/month YYYY-MM` — весь месяц
- `/range YYYY-MM-DD YYYY-MM-DD` — диапазон
- `/ics [YEAR]` — пришлёт .ics на год (можно импортировать в календарь)

## Примечания
- Бот использует **шуточный** 12‑дневный цикл (не «настоящий» 60‑дневный). 
- Для ветви 亥: «Возможны кража и утрата имущества — берегитесь воров и потерянных вещей.»
- Бот берёт текущую дату по часовому поясу сервера, где запущен.
