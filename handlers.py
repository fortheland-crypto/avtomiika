from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from keyboards import (
    get_main_keyboard,
    get_boxes_inline_keyboard,
    get_services_inline_keyboard,
    get_active_washes_keyboard
)
from database import (
    add_wash_entry,
    complete_wash,
    get_active_washes,
    get_today_stats,
    generate_demo_shift,
    get_wash_by_id
)
from config import SERVICES, MIN_WASH_DURATION_SECONDS

router = Router()

class WashForm(StatesGroup):
    waiting_for_car_number = State()

def format_currency(amount: int) -> str:
    """Форматирование суммы в тенге ₸ (например, 3 000 ₸)"""
    return f"{amount:,} ₸".replace(",", " ")

def format_seconds(seconds: int) -> str:
    """Форматирование секунд в минуты и секунды"""
    mins = seconds // 60
    secs = seconds % 60
    if mins > 0:
        return f"{mins} мин {secs} сек"
    return f"{secs} сек"

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    text = (
        "👋 **Добро пожаловать в Telegram-бот системы автомойки!**\n\n"
        "Данный бот фиксирует въезд машин с 3-значным номером по боксам, ведёт автоматический подсчёт "
        "вымытых автомобилей и рассчитывает выручку по прейскуранту (в ₸).\n\n"
        "📌 **Прейскурант:**\n"
        "• 🚗 **Легковая машина**: 3 000 ₸\n"
        "• 🚙 **Джип / Большая машина**: 5 000 ₸\n"
        "• 🚗✨ **Легковая (Комплекс)**: 4 500 ₸\n"
        "• 🚙✨ **Джип (Комплекс)**: 7 000 ₸\n\n"
        "💡 *Для демонстрации нажимайте «⚡ Демо-смена», чтобы мгновенно наполнить базу за сегодняшний день!*"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@router.message(F.text == "🚗 Зафиксировать въезд")
async def start_entry_process(message: Message, state: FSMContext):
    """Начало фиксации заезда: выбор бокса"""
    await state.clear()
    text = "🚗 **Выберите свободный бокс для заезда автомобиля:**"
    await message.answer(text, reply_markup=get_boxes_inline_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "back_to_boxes")
async def back_to_boxes_callback(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору бокса"""
    await state.clear()
    text = "🚗 **Выберите свободный бокс для заезда автомобиля:**"
    await callback.message.edit_text(text, reply_markup=get_boxes_inline_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("select_box:"))
async def select_box_callback(callback: CallbackQuery):
    """Выбор бокса: показ прейскуранта категорий авто"""
    box_name = callback.data.split(":")[1]
    text = (
        f"📍 **Выбран: {box_name}**\n\n"
        f"Укажите категорию автомобиля или услугу по прейскуранту:"
    )
    await callback.message.edit_text(
        text, 
        reply_markup=get_services_inline_keyboard(box_name),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("add_wash:"))
async def add_wash_callback(callback: CallbackQuery, state: FSMContext):
    """Запрос 3-значного номера авто после выбора услуги"""
    parts = callback.data.split(":")
    box_name = parts[1]
    service_key = parts[2]
    service_info = SERVICES[service_key]
    
    # Сохраняем данные во временном состоянии FSM
    await state.update_data(box_name=box_name, service_key=service_key)
    await state.set_state(WashForm.waiting_for_car_number)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Без номера (пропустить)", callback_data="skip_car_number")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])
    
    text = (
        f"📍 **{box_name}** | {service_info['title']} ({format_currency(service_info['price'])})\n\n"
        f"🔢 **Введите 3-значный номер автомобиля:**\n"
        f"*(Например, отправьте в чат: `542` или `123`)*"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.message(WashForm.waiting_for_car_number)
async def process_car_number_input(message: Message, state: FSMContext):
    """Обработка введённого пользователем 3-значного номера машины"""
    car_num_raw = message.text.strip()
    
    data = await state.get_data()
    box_name = data.get("box_name")
    service_key = data.get("service_key")
    
    if not box_name or not service_key:
        await message.answer("Сессия истекла. Начните заново нажав «🚗 Зафиксировать въезд».", reply_markup=get_main_keyboard())
        await state.clear()
        return

    service_info = SERVICES[service_key]
    formatted_num = f"№{car_num_raw}" if car_num_raw else "—"
    
    add_wash_entry(box_name, service_key, car_number=formatted_num)
    await state.clear()
    
    now_time = datetime.now().strftime("%H:%M:%S")
    text = (
        f"✅ **Въезд зафиксирован!**\n\n"
        f"📍 **Бокс**: {box_name}\n"
        f"🔢 **Номер авто**: **{formatted_num}**\n"
        f"🚗 **Категория**: {service_info['title']}\n"
        f"🧾 **Чек**: **{format_currency(service_info['price'])}**\n"
        f"⏱ **Время въезда**: {now_time}\n\n"
        f"📌 *Автомобиль учитывается в статистике при нахождении в боксе >1 минуты.*"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "skip_car_number")
async def skip_car_number_callback(callback: CallbackQuery, state: FSMContext):
    """Фиксация заезда без номера"""
    data = await state.get_data()
    box_name = data.get("box_name")
    service_key = data.get("service_key")
    
    if not box_name or not service_key:
        await callback.answer("Сессия истекла.", show_alert=True)
        await state.clear()
        return

    service_info = SERVICES[service_key]
    add_wash_entry(box_name, service_key, car_number="—")
    await state.clear()
    
    now_time = datetime.now().strftime("%H:%M:%S")
    text = (
        f"✅ **Въезд зафиксирован!**\n\n"
        f"📍 **Бокс**: {box_name}\n"
        f"🔢 **Номер авто**: **—**\n"
        f"🚗 **Категория**: {service_info['title']}\n"
        f"🧾 **Чек**: **{format_currency(service_info['price'])}**\n"
        f"⏱ **Время въезда**: {now_time}\n\n"
        f"📌 *Автомобиль учитывается в статистике при нахождении в боксе >1 минуты.*"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer("Заезд успешно зафиксирован!")

@router.message(F.text == "⏱ Машины в боксах")
async def show_active_washes(message: Message, state: FSMContext):
    """Просмотр машин, находящихся в боксах в данный момент"""
    await state.clear()
    active = get_active_washes()
    
    if not active:
        await message.answer(
            "🟢 **В данный момент все боксы свободны.**",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    text_lines = ["⏱ **МАШИНЫ В БОКСАХ ПРЯМО СЕЙЧАС:**\n"]
    for w in active:
        duration_str = format_seconds(w["duration_seconds"])
        status_icon = "✅ Подтверждена" if w["is_qualified"] else "⏳ Ожидание (>1 мин)"
        num_str = f" (**{w.get('car_number', '—')}**)" if w.get('car_number') and w.get('car_number') != '—' else ""
        
        text_lines.append(
            f"🔴 **{w['box_name']}**{num_str}: {w['service_name']}\n"
            f"   🧾 Чек: {format_currency(w['price'])}\n"
            f"   ⏱ В боксе: **{duration_str}** ({status_icon})\n"
        )
        
    await message.answer(
        "\n".join(text_lines),
        reply_markup=get_active_washes_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "refresh_active")
async def refresh_active_callback(callback: CallbackQuery):
    """Обновление списка машин в боксах"""
    active = get_active_washes()
    
    if not active:
        await callback.message.edit_text(
            "🟢 **В данный момент все боксы свободны.**",
            parse_mode="Markdown"
        )
        await callback.answer("Список обновлён")
        return

    text_lines = ["⏱ **МАШИНЫ В БОКСАХ ПРЯМО СЕЙЧАС:**\n"]
    for w in active:
        duration_str = format_seconds(w["duration_seconds"])
        status_icon = "✅ Подтверждена" if w["is_qualified"] else "⏳ Ожидание (>1 мин)"
        num_str = f" (**{w.get('car_number', '—')}**)" if w.get('car_number') and w.get('car_number') != '—' else ""
        
        text_lines.append(
            f"🔴 **{w['box_name']}**{num_str}: {w['service_name']}\n"
            f"   🧾 Чек: {format_currency(w['price'])}\n"
            f"   ⏱ В боксе: **{duration_str}** ({status_icon})\n"
        )
        
    await callback.message.edit_text(
        "\n".join(text_lines),
        reply_markup=get_active_washes_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("Список обновлён")

@router.callback_query(F.data.startswith("finish_wash:"))
async def finish_wash_callback(callback: CallbackQuery):
    """Отметка о выезде машины из бокса и закрытие чека"""
    wash_id = int(callback.data.split(":")[1])
    wash_data = get_wash_by_id(wash_id)
    
    if not wash_data:
        await callback.answer("Запись не найдена", show_alert=True)
        return
        
    completed = complete_wash(wash_id)
    
    if completed:
        now_time = datetime.now().strftime("%H:%M:%S")
        try:
            entry_dt = datetime.strptime(wash_data["entry_time"], "%Y-%m-%d %H:%M:%S")
            total_seconds = int((datetime.now() - entry_dt).total_seconds())
            dur_str = format_seconds(total_seconds)
        except Exception:
            dur_str = "15 мин"
            
        num_str = f" ({wash_data['car_number']})" if wash_data.get('car_number') and wash_data.get('car_number') != '—' else ""
        
        text = (
            f"🧾 **ЧЕК ЗАКРЫТ (ВЫЕЗД)**\n\n"
            f"📍 **Бокс**: {wash_data['box_name']}\n"
            f"🔢 **Номер авто**: **{wash_data.get('car_number', '—')}**\n"
            f"🚗 **Категория**: {wash_data['service_name']}\n"
            f"💰 **К оплате**: **{format_currency(wash_data['price'])}**\n"
            f"⏱ **Общее время в боксе**: {dur_str}\n"
            f"🕒 **Время выезда**: {now_time}"
        )
        await callback.message.answer(text, parse_mode="Markdown")
        await callback.answer("Бокс освобождён! Чек закрыт.")
        
        await refresh_active_callback(callback)
    else:
        await callback.answer("Машина уже выехала из бокса.")

@router.message(F.text == "📊 Статистика за сегодня")
async def show_today_stats(message: Message, state: FSMContext):
    """Формирование и вывод статистики автомойки за сегодняшний день"""
    await state.clear()
    stats = get_today_stats()
    
    text = (
        f"📊 **ОТЧЁТ ПО АВТОМОЙКЕ ЗА СЕГОДНЯ** ({stats['today_date']})\n"
        f"═════════════════════════════\n"
        f"🚗 **Всего заехало автомобилей**: **{stats['total_entries']}**\n"
        f"✅ **Подтверждённых моек (>1 мин)**: **{stats['confirmed_count']}**\n"
        f"💰 **Общая выручка за день**: **{format_currency(stats['total_revenue'])}**\n"
        f"🧾 **Средний чек**: **{format_currency(stats['avg_check'])}**\n\n"
        f"📈 **РАЗБИВКА ПО КАТЕГОРИЯМ:**\n"
    )
    
    for s_title, s_data in stats["service_stats"].items():
        if s_data["count"] > 0:
            text += f"• {s_title}: **{s_data['count']}** авто — {format_currency(s_data['sum'])}\n"
            
    text += f"\n🏢 **ЗАГРУЗКА БОКСОВ:**\n"
    for b_name, b_data in stats["box_stats"].items():
        text += f"• {b_name}: **{b_data['count']}** авто — {format_currency(b_data['sum'])}\n"
        
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📋 Журнал смены")
async def show_shift_log(message: Message, state: FSMContext):
    """Детализированный журнал заездов за сегодняшний день"""
    await state.clear()
    stats = get_today_stats()
    rows = stats["all_rows"]
    
    if not rows:
        await message.answer("📋 **Журнал за сегодня пуст.**", parse_mode="Markdown")
        return
        
    lines = [f"📋 **ЖУРНАЛ ЗАЕЗДОВ ЗА СЕГОДНЯ ({stats['today_date']}):**\n"]
    for idx, r in enumerate(rows, 1):
        entry_time_str = r["entry_time"].split()[1][:5] if " " in r["entry_time"] else "12:00"
        status_str = "🟢 Выехала" if r["status"] == "completed" else "🔴 В боксе"
        car_num = r.get("car_number", "—")
        num_str = f" | **{car_num}**" if car_num and car_num != "—" else ""
        
        lines.append(
            f"{idx}. `[{entry_time_str}]` **{r['box_name']}**{num_str} | {r['service_name']} — **{format_currency(r['price'])}** ({status_str})"
        )
        
    await message.answer("\n".join(lines), parse_mode="Markdown")

@router.message(F.text == "⚡ Демо-смена")
@router.message(Command("demo"))
async def setup_demo_shift(message: Message, state: FSMContext):
    """Генерация демо-данных смены с 3-значными номерами для презентации"""
    await state.clear()
    generate_demo_shift()
    
    text_notice = (
        "⚡ **Демо-смена успешно сгенерирована!**\n\n"
        "В базу добавлено 14 прошедших заездов авто за сегодня с 3-значными номерами "
        "(например: №542, №109, №777) + 2 активные машины (№307 и №542) в Боксе №3 и Боксе №4!\n\n"
        "Ниже сформирован готовый аналитический отчёт:"
    )
    await message.answer(text_notice, parse_mode="Markdown")
    await show_today_stats(message, state)

@router.callback_query(F.data == "cancel_action")
async def cancel_action_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена действия / закрытие сообщения"""
    await state.clear()
    await callback.message.delete()
    await callback.answer("Действие отменено")
