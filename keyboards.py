from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import BOXES, SERVICES
from database import get_active_washes

DASHBOARD_URL = "https://avtomiika.vercel.app/dashboard"

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура бота: 4 чистые понятные кнопки"""
    kb = [
        [KeyboardButton(text="🚗 Зафиксировать въезд"), KeyboardButton(text="🏁 Зафиксировать выезд")],
        [KeyboardButton(text="📊 Статистика за сегодня"), KeyboardButton(text="📋 Журнал смены")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_boxes_inline_keyboard() -> InlineKeyboardMarkup:
    """Инлайн клавиатура выбора боксов с отметкой занятости"""
    active_washes = get_active_washes()
    occupied_boxes = {w["box_name"]: w for w in active_washes}
    
    inline_keyboard = []
    for box in BOXES:
        if box in occupied_boxes:
            w = occupied_boxes[box]
            car_num = w.get("car_number", "—")
            num_str = f" ({car_num})" if car_num and car_num != "—" else ""
            status_str = f"🔴 {box}{num_str} (Занят)"
        else:
            status_str = f"🟢 {box} (Свободен)"
            
        inline_keyboard.append([
            InlineKeyboardButton(text=status_str, callback_data=f"select_box:{box}")
        ])
        
    inline_keyboard.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_services_inline_keyboard(box_name: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора типа авто и услуги по прейскуранту (в тенге ₸)"""
    inline_keyboard = []
    
    for s_key, s_data in SERVICES.items():
        button_text = f"{s_data['title']} — {s_data['price']:,} ₸".replace(",", " ")
        inline_keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"add_wash:{box_name}:{s_key}")
        ])
        
    inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад к выбору бокса", callback_data="back_to_boxes"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_active_washes_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура прямого оформления выезда из занятых боксов"""
    active = get_active_washes()
    inline_keyboard = [
        [InlineKeyboardButton(text="📱 Открыть Графический Дашборд", web_app=WebAppInfo(url=DASHBOARD_URL))]
    ]
    
    for w in active:
        b_name = w["box_name"]
        price = f"{w['price']:,} ₸".replace(",", " ")
        car_num = w.get("car_number", "—")
        num_str = f" ({car_num})" if car_num and car_num != "—" else ""
        btn_text = f"🏁 Выехал: {b_name}{num_str} — {price}"
        inline_keyboard.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"direct_finish_wash:{w['id']}")
        ])
        
    inline_keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить список боксов", callback_data="refresh_active"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="cancel_action")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_shift_log_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для журнала смены с кнопкой очистки"""
    inline_keyboard = [
        [InlineKeyboardButton(text="📱 Открыть Графический Дашборд", web_app=WebAppInfo(url=DASHBOARD_URL))],
        [InlineKeyboardButton(text="🗑 Очистить журнал смены", callback_data="ask_clear_shift")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_confirm_clear_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения очистки журнала"""
    inline_keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, очистить всё", callback_data="confirm_clear_shift"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
