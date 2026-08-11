import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import router

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("\n" + "=" * 60)
        print("❌ ОШИБКА: BOT_TOKEN не указан в файле .env!")
        print("1. Создайте бота через @BotFather в Telegram")
        print("2. Скопируйте токен бота")
        print("3. Вставьте его в файл .env (BOT_TOKEN=ваш_токен)")
        print("=" * 60 + "\n")
        sys.exit(1)
        
    print("🚀 Инициализация базы данных SQLite...")
    init_db()
    
    print("🤖 Запуск Telegram-бота автомойки...")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен.")
