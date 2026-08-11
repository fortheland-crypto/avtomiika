import os
import sys
from datetime import datetime

# Подключаем модули проекта
from database import (
    init_db,
    add_wash_entry,
    complete_wash,
    get_active_washes,
    get_today_stats,
    generate_demo_shift,
    get_wash_by_id
)
from config import SERVICES

def test_carwash_logic():
    print("🧪 Начинаем тестирование бизнес-логики автомойки...")
    
    # 1. Инициализация базы
    init_db()
    print("  [1/5] База данных успешно инициализирована.")

    # 2. Проверка генерации демо-смены
    generate_demo_shift()
    stats = get_today_stats()
    
    print(f"  [2/5] Демо-смена сгенерирована:")
    print(f"        • Всего въехало авто: {stats['total_entries']}")
    print(f"        • Подтверждено моек (>1 мин): {stats['confirmed_count']}")
    print(f"        • Выручка за день: {stats['total_revenue']:,} ₸".replace(",", " "))
    print(f"        • Средний чек: {stats['avg_check']:,} ₸".replace(",", " "))
    
    assert stats['confirmed_count'] > 0, "Количество моек должно быть > 0"
    assert stats['total_revenue'] > 0, "Общая выручка должна быть > 0"

    # 3. Ручной заезд машины
    wash_id = add_wash_entry("Бокс №1", "light")
    print(f"  [3/5] Зафиксирован заезд в Бокс №1 (Легковая 3 000 ₸). ID записи: {wash_id}")
    
    active = get_active_washes()
    b1_washes = [w for w in active if w["box_name"] == "Бокс №1"]
    assert len(b1_washes) == 1, "В Боксе №1 должна быть 1 активная машина"
    assert b1_washes[0]["price"] == 3000, "Цена легковой должна быть 3000 ₸"

    # 4. Выезд машины и закрытие чека
    completed = complete_wash(wash_id)
    assert completed is True, "Выезд должен быть успешно оформлен"
    print("  [4/5] Выезд машины зафиксирован, чек закрыт.")

    # 5. Проверка финальной статистики
    new_stats = get_today_stats()
    print(f"  [5/5] Финальная статистика за день:")
    print(f"        • Подтвержденных моек: {new_stats['confirmed_count']}")
    print(f"        • Итоговая выручка: {new_stats['total_revenue']:,} ₸".replace(",", " "))
    
    print("\n✅ ВСЕ ТЕСТЫ БИЗНЕС-ЛОГИКИ УСПЕШНО ПРОЙДЕНЫ!")

if __name__ == "__main__":
    test_carwash_logic()
