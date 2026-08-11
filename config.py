import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")

# Перечень боксов автомойки
BOXES = [
    "Бокс №1",
    "Бокс №2",
    "Бокс №3",
    "Бокс №4"
]

# Прейскурант услуг и категорий автомобилей (в тенге ₸)
SERVICES = {
    "light": {
        "title": "🚗 Легковая машина",
        "price": 3000,
        "description": "Стандартная мойка легкового авто"
    },
    "suv": {
        "title": "🚙 Джип / Большая машина",
        "price": 5000,
        "description": "Мойка внедорожника, кроссовера или минивэна"
    },
    "light_complex": {
        "title": "🚗✨ Легковая (Комплекс)",
        "price": 4500,
        "description": "Кузов + салон + сушка"
    },
    "suv_complex": {
        "title": "🚙✨ Джип (Комплекс)",
        "price": 7000,
        "description": "Кузов + салон + сушка для больших авто"
    }
}

# Минимальное время нахождения в боксе (в секундах) для автоподтверждения (1 минута = 60 сек)
MIN_WASH_DURATION_SECONDS = 60
