import os
import sys
import tempfile
import traceback

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from config import BOT_TOKEN
from database import init_db
from handlers import router

app = FastAPI()

# Глобальный Dispatcher инициализируется один раз
dp = Dispatcher()
dp.include_router(router)

def get_telegram_bot():
    token = os.getenv("BOT_TOKEN", BOT_TOKEN)
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        raise ValueError("BOT_TOKEN не установлен в Environment Variables на Vercel")
    return Bot(token=token)

@app.get("/")
async def root_status():
    token = os.getenv("BOT_TOKEN", BOT_TOKEN)
    is_valid_token = bool(token and token != "YOUR_TELEGRAM_BOT_TOKEN_HERE")
    
    try:
        init_db()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "message": "🚗 Telegram-бот автомойки работает на Vercel!",
        "bot_token_configured": is_valid_token,
        "database_status": db_status
    }

@app.post("/webhook")
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    """Обработчик входящих вебхуков от Telegram API"""
    try:
        bot = get_telegram_bot()
        init_db()

        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }

@app.get("/set_webhook")
@app.get("/api/set_webhook")
async def set_webhook(request: Request):
    """Эндпоинт для авто-регистрации вебхука в Telegram"""
    try:
        bot = get_telegram_bot()
        host = request.headers.get("host")
        scheme = request.headers.get("x-forwarded-proto", "https")
        webhook_url = f"{scheme}://{host}/api/webhook"
        
        success = await bot.set_webhook(webhook_url)
        return {
            "success": success,
            "webhook_url": webhook_url,
            "message": "Вебхук успешно зарегистрирован в Telegram!" if success else "Ошибка установки вебхука."
        }
    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
