import os
import sys

# Добавляем корневую директорию проекта в sys.path для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from config import BOT_TOKEN
from database import init_db
from handlers import router

app = FastAPI()

# Инициализация бота и диспетчера aiogram
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

# Инициализация базы данных при запуске
init_db()

@app.get("/")
async def root_status():
    return {
        "status": "ok",
        "message": "🚗 Telegram-бот автомойки успешно работает на Vercel!",
        "bot_token_set": bool(BOT_TOKEN and BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE")
    }

@app.post("/webhook")
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    """Обработчик входящих вебхуков от Telegram API"""
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/set_webhook")
@app.get("/api/set_webhook")
async def set_webhook(request: Request):
    """Эндпоинт для авто-регистрации вебхука в Telegram"""
    host = request.headers.get("host")
    scheme = request.headers.get("x-forwarded-proto", "https")
    webhook_url = f"{scheme}://{host}/webhook"
    
    try:
        success = await bot.set_webhook(webhook_url)
        return {
            "success": success,
            "webhook_url": webhook_url,
            "message": "Вебхук успешно зарегистрирован в Telegram!" if success else "Ошибка установки вебхука."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
