# HOWL — бот несчастий (Render / Webhook)

## Шаги деплоя
1) Залей в приватный GitHub этот репозиторий.
2) На render.com → New → Web Service → выбери репо.
3) Build: `pip install -r requirements.txt`, Start: `python bot.py`.
4) Env: `TELEGRAM_TOKEN=...` (токен от BotFather). `RENDER_EXTERNAL_URL` и `PORT` Render поставит сам.
5) Жди деплоя. Готово.

Локальный запуск:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:TELEGRAM_TOKEN="ТОКЕН"
python bot.py
```
