import os
import sys

from database import (
    init_db,
    clear_shift_history,
    add_wash_entry,
    complete_wash,
    get_active_washes,
    get_today_stats,
    get_wash_by_id
)
from config import SERVICES

def test_carwash_logic():
    print("🧪 Начинаем тестирование бизнес-логики автомойки...")
    
    # 1. Инициализация и очистка базы
    init_db()
    clear_shift_history()
    print("  [1/5] База данных успешно очищена.")

    stats_empty = get_today_stats()
    assert stats_empty["total_revenue"] == 0, "После очистки выручка должна быть 0"
    assert stats_empty["confirmed_count"] == 0, "После очистки вымытых авто должно быть 0"
    assert len(get_active_washes()) == 0, "После очистки все боксы должны быть свободны"
    print("  [2/5] Проверка пустой базы: Все боксы свободны, выручка = 0 ₸.")

    # 2. Ручной заезд машины №542 в Бокс №1
    wash_id = add_wash_entry("Бокс №1", "light", car_number="№542")
    print(f"  [3/5] Зафиксирован заезд в Бокс №1 (Легковая №542 3 000 ₸). ID записи: {wash_id}")
    
    active = get_active_washes()
    b1_washes = [w for w in active if w["box_name"] == "Бокс №1"]
    assert len(b1_washes) == 1, "В Боксе №1 должна быть 1 активная машина"
    assert b1_washes[0]["price"] == 3000, "Цена легковой должна быть 3000 ₸"
    assert b1_washes[0]["car_number"] == "№542", "Номер авто должен быть №542"

    # 3. Выезд машины и закрытие чека
    completed = complete_wash(wash_id)
    assert completed is True, "Выезд должен быть успешно оформлен"
    print("  [4/5] Выезд машины зафиксирован, чек закрыт.")

    # 4. Проверка статистики за день
    stats = get_today_stats()
    print(f"  [5/5] Статистика за день:")
    print(f"        • Подтвержденных моек: {stats['confirmed_count']}")
    print(f"        • Итоговая выручка: {stats['total_revenue']:,} ₸".replace(",", " "))
    
    assert stats["confirmed_count"] == 1, "Должна быть 1 подтвержденная мойка"
    assert stats["total_revenue"] == 3000, "Выручка должна составлять 3000 ₸"

    print("\n✅ ВСЕ ТЕСТЫ БИЗНЕС-ЛОГИКИ И ОЧИСТКИ ДАННЫХ УСПЕШНО ПРОЙДЕНЫ!")

if __name__ == "__main__":
    test_carwash_logic()
