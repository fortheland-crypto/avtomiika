import os
import sys
import tempfile
import traceback

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from aiogram import Bot, Dispatcher, types
from config import BOT_TOKEN
from database import (
    init_db,
    add_wash_entry,
    complete_wash,
    get_active_washes,
    get_today_stats
)
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

@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/api/dashboard", response_class=HTMLResponse)
async def get_dashboard_html():
    """Эндпоинт отдачи красивого HTML5 Telegram Web App Дашборда"""
    html_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "dashboard.html")
    if os.path.exists(html_file_path):
        with open(html_file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Дашборд загружается...</h1>"

@app.get("/api/washes")
async def get_dashboard_washes():
    """REST API для дашборда: активные боксы и статистика за день"""
    init_db()
    active = get_active_washes()
    stats = get_today_stats()
    return {
        "status": "ok",
        "active": active,
        "stats": stats
    }

@app.post("/api/add_wash")
async def api_add_wash(request: Request):
    """REST API для создания заезда с дашборда"""
    init_db()
    data = await request.json()
    box_name = data.get("box_name")
    service_key = data.get("service_key")
    car_number = data.get("car_number", "—")
    
    wash_id = add_wash_entry(box_name, service_key, car_number=car_number)
    return {"status": "ok", "wash_id": wash_id}

@app.post("/api/complete_wash")
async def api_complete_wash(request: Request):
    """REST API для оформления выезда авто с дашборда"""
    init_db()
    data = await request.json()
    wash_id = int(data.get("wash_id"))
    success = complete_wash(wash_id)
    return {"status": "ok", "completed": success}

@app.post("/webhook")
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    """Обработчик входящих вебхуков от Telegram API"""
    bot = None
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
    finally:
        if bot:
            await bot.session.close()

@app.get("/set_webhook")
@app.get("/api/set_webhook")
async def set_webhook(request: Request):
    """Эндпоинт для авто-регистрации вебхука в Telegram"""
    bot = None
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
    finally:
        if bot:
            await bot.session.close()
