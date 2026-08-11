import sqlite3
import os
import tempfile
from datetime import datetime, timedelta, date, timezone
from config import SERVICES, MIN_WASH_DURATION_SECONDS, BOXES

# Локальный часовой пояс автомойки (UTC+5)
TZ_OFFSET = timezone(timedelta(hours=5))

def get_now() -> datetime:
    """Текущее время в локальном часовом поясе (UTC+5)"""
    return datetime.now(timezone.utc).astimezone(TZ_OFFSET)

if os.getenv("VERCEL") or not os.access(os.path.dirname(__file__), os.W_OK):
    DB_PATH = os.path.join(tempfile.gettempdir(), "carwash.db")
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "carwash.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация таблиц БД SQLite"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS washes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_name TEXT NOT NULL,
                service_key TEXT NOT NULL,
                service_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                car_number TEXT DEFAULT '—',
                entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exit_time TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'in_box'
            )
        """)
        try:
            cursor.execute("ALTER TABLE washes ADD COLUMN car_number TEXT DEFAULT '—'")
        except sqlite3.OperationalError:
            pass
        conn.commit()

def add_wash_entry(box_name: str, service_key: str, car_number: str = "—") -> int:
    """Фиксация заезда машины с 3-значным номером в бокс по локальному времени UTC+5"""
    if service_key not in SERVICES:
        raise ValueError("Неизвестная услуга")
    
    service = SERVICES[service_key]
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Если в боксе уже есть активная машина, завершаем её
        now_str = get_now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE washes 
            SET status = 'completed', exit_time = ? 
            WHERE box_name = ? AND status = 'in_box'
        """, (now_str, box_name))
        
        # Создаём новую запись о заезде с локальным временем
        cursor.execute("""
            INSERT INTO washes (box_name, service_key, service_name, price, car_number, entry_time, status)
            VALUES (?, ?, ?, ?, ?, ?, 'in_box')
        """, (box_name, service_key, service["title"], service["price"], car_number, now_str))
        
        conn.commit()
        return cursor.lastrowid

def complete_wash(wash_id: int) -> bool:
    """Отметка о выезде машины из бокса (выписка чека) по времени UTC+5"""
    with get_connection() as conn:
        cursor = conn.cursor()
        now_str = get_now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE washes
            SET status = 'completed', exit_time = ?
            WHERE id = ? AND status = 'in_box'
        """, (now_str, wash_id))
        conn.commit()
        return cursor.rowcount > 0

def get_wash_by_id(wash_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM washes WHERE id = ?", (wash_id,))
        return cursor.fetchone()

def get_active_washes():
    """Получение всех машин, которые прямо сейчас стоят в боксах"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM washes 
            WHERE status = 'in_box' 
            ORDER BY entry_time DESC
        """)
        rows = cursor.fetchall()
        
        active_list = []
        now = get_now()
        for r in rows:
            row_dict = dict(r)
            try:
                # Отрезаем возможные смещения часового пояса для парсинга
                clean_time = row_dict["entry_time"].split(".")[0].split("+")[0]
                entry_dt = datetime.strptime(clean_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ_OFFSET)
                duration_seconds = int((now - entry_dt).total_seconds())
            except Exception:
                duration_seconds = 65
                
            row_dict["duration_seconds"] = max(0, duration_seconds)
            row_dict["is_qualified"] = duration_seconds >= MIN_WASH_DURATION_SECONDS
            active_list.append(row_dict)
            
        return active_list

def get_today_stats():
    """
    Расчёт статистики автомойки за текущую смену / день с локальной датой UTC+5.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM washes ORDER BY entry_time ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        
    now = get_now()
    
    total_entries = len(rows)
    confirmed_washes = []
    
    for r in rows:
        if r["status"] == "completed":
            confirmed_washes.append(r)
        elif r["status"] == "in_box":
            try:
                clean_time = r["entry_time"].split(".")[0].split("+")[0]
                entry_dt = datetime.strptime(clean_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ_OFFSET)
                duration = (now - entry_dt).total_seconds()
                if duration >= MIN_WASH_DURATION_SECONDS:
                    confirmed_washes.append(r)
            except Exception:
                confirmed_washes.append(r)
                
    confirmed_count = len(confirmed_washes)
    total_revenue = sum(w["price"] for w in confirmed_washes)
    avg_check = round(total_revenue / confirmed_count) if confirmed_count > 0 else 0
    
    # Разбивка по услугам
    service_stats = {}
    for s_key, s_val in SERVICES.items():
        service_stats[s_val["title"]] = {"count": 0, "sum": 0}
        
    for w in confirmed_washes:
        title = w["service_name"]
        if title not in service_stats:
            service_stats[title] = {"count": 0, "sum": 0}
        service_stats[title]["count"] += 1
        service_stats[title]["sum"] += w["price"]
        
    # Разбивка по боксам
    box_stats = {box: {"count": 0, "sum": 0} for box in BOXES}
    for w in confirmed_washes:
        b_name = w["box_name"]
        if b_name not in box_stats:
            box_stats[b_name] = {"count": 0, "sum": 0}
        box_stats[b_name]["count"] += 1
        box_stats[b_name]["sum"] += w["price"]
        
    return {
        "today_date": get_now().strftime("%d.%m.%Y"),
        "total_entries": total_entries,
        "confirmed_count": confirmed_count,
        "total_revenue": total_revenue,
        "avg_check": avg_check,
        "service_stats": service_stats,
        "box_stats": box_stats,
        "all_rows": rows
    }

def generate_demo_shift():
    """
    Генерация смены по локальному времени (UTC+5) с 3-значными номерами.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM washes")
        
        now = get_now()
        
        demo_offsets = [
            ("Бокс №1", "light", "542", 360, 20),
            ("Бокс №2", "suv", "109", 330, 25),
            ("Бокс №3", "light_complex", "777", 300, 35),
            ("Бокс №4", "light", "341", 270, 18),
            ("Бокс №1", "suv_complex", "812", 240, 40),
            ("Бокс №2", "light", "405", 210, 22),
            ("Бокс №3", "suv", "923", 180, 28),
            ("Бокс №4", "light_complex", "618", 150, 30),
            ("Бокс №1", "light", "254", 120, 19),
            ("Бокс №2", "suv_complex", "730", 90, 45),
            ("Бокс №3", "light", "189", 75, 21),
            ("Бокс №4", "suv", "650", 60, 26),
            ("Бокс №1", "light_complex", "432", 45, 32),
            ("Бокс №2", "light", "891", 30, 20),
        ]
        
        for box, serv_key, num, offset_m, duration_m in demo_offsets:
            serv = SERVICES[serv_key]
            entry_dt = now - timedelta(minutes=offset_m)
            exit_dt = entry_dt + timedelta(minutes=duration_m)
            
            cursor.execute("""
                INSERT INTO washes (box_name, service_key, service_name, price, car_number, entry_time, exit_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'completed')
            """, (
                box, 
                serv_key, 
                serv["title"], 
                serv["price"], 
                num,
                entry_dt.strftime("%Y-%m-%d %H:%M:%S"), 
                exit_dt.strftime("%Y-%m-%d %H:%M:%S")
            ))
            
        # Добавляем 2 активные машины с номерами (№307 и №542) в Бокс №3 и Бокс №4
        entry_active1 = (now - timedelta(minutes=14)).strftime("%Y-%m-%d %H:%M:%S")
        entry_active2 = (now - timedelta(minutes=4)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO washes (box_name, service_key, service_name, price, car_number, entry_time, status)
            VALUES (?, ?, ?, ?, ?, ?, 'in_box')
        """, ("Бокс №3", "suv", SERVICES["suv"]["title"], SERVICES["suv"]["price"], "307", entry_active1))
        
        cursor.execute("""
            INSERT INTO washes (box_name, service_key, service_name, price, car_number, entry_time, status)
            VALUES (?, ?, ?, ?, ?, ?, 'in_box')
        """, ("Бокс №4", "light_complex", SERVICES["light_complex"]["title"], SERVICES["light_complex"]["price"], "542", entry_active2))

        conn.commit()
