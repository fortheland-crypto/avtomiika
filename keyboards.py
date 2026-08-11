from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import BOXES, SERVICES
from database import get_active_washes

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура бота"""
    kb = [
        [KeyboardButton(text="🚗 Зафиксировать въезд"), KeyboardButton(text="⏱ Машины в боксах")],
        [KeyboardButton(text="📊 Статистика за сегодня"), KeyboardButton(text="📋 Журнал смены")],
        [KeyboardButton(text="⚡ Демо-смена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_boxes_inline_keyboard() -> InlineKeyboardMarkup:
    """Инлайн клавиатура выбора боксов с отметкой занятости"""
    active_washes = get_active_washes()
    occupied_boxes = {w["box_name"]: w for w in active_washes}
    
    inline_keyboard = []
    for box in BOXES:
        if box in occupied_boxes:
            status_str = f"🔴 {box} (Занят)"
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
    """Клавиатура для отметки завершения мойки / выписки чека"""
    active = get_active_washes()
    inline_keyboard = []
    
    for w in active:
        b_name = w["box_name"]
        price = f"{w['price']:,} ₸".replace(",", " ")
        btn_text = f"🏁 Выехал: {b_name} ({price})"
        inline_keyboard.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"finish_wash:{w['id']}")
        ])
        
    inline_keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить статус", callback_data="refresh_active"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="cancel_action")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
