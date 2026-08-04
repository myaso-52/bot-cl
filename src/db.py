import sqlite3
import time

DB_PATH = "database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            moder_rank INTEGER DEFAULT 0,
            clicks_count INTEGER DEFAULT 0,
            last_click REAL DEFAULT 0.0,
            last_daily REAL DEFAULT 0.0,
            total_withdrawn INTEGER DEFAULT 0,
            is_perm_banned INTEGER DEFAULT 0,
            ban_until REAL DEFAULT 0.0,
            ban_reason TEXT DEFAULT '',
            nickname TEXT DEFAULT 'Игрок',
            no_cd_until REAL DEFAULT 0.0,
            x2_until INTEGER DEFAULT 0,
            reg_date TEXT DEFAULT '',
            has_legendary INTEGER DEFAULT 0,
            referrer_id INTEGER DEFAULT 0,
            ref_reward_given INTEGER DEFAULT 0,
            last_withdraw REAL DEFAULT 0.0,
            vip_until REAL DEFAULT 0.0,
            game_boost_until REAL DEFAULT 0.0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            timestamp REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT
        )
    ''')
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_withdraw REAL DEFAULT 0.0")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN vip_until REAL DEFAULT 0.0")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN game_boost_until REAL DEFAULT 0.0")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT 0")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN ref_reward_given INTEGER DEFAULT 0")
    except:
        pass
    conn.commit()
    conn.close()

def get_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row is None:
            current_date = time.strftime("%d.%m.%Y")
            cursor.execute('''
                INSERT INTO users (
                    user_id, balance, moder_rank, clicks_count, last_click, 
                    last_daily, total_withdrawn, is_perm_banned, ban_until, 
                    ban_reason, nickname, no_cd_until, x2_until, reg_date, 
                    has_legendary, referrer_id, ref_reward_given, last_withdraw,
                    vip_until, game_boost_until
                ) VALUES (?, 0, 0, 0, 0.0, 0.0, 0, 0, 0.0, '', 'Игрок', 0.0, 0, ?, 0, 0, 0, 0.0, 0.0, 0.0)
            ''', (user_id, current_date))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        return dict(row)

def update_user_field(user_id, field_name, value):
    allowed_fields = [
        'balance', 'moder_rank', 'clicks_count', 'last_click', 
        'last_daily', 'total_withdrawn', 'is_perm_banned', 
        'ban_until', 'ban_reason', 'nickname', 'no_cd_until', 
        'x2_until', 'reg_date', 'has_legendary', 'referrer_id', 
        'ref_reward_given', 'last_withdraw', 'vip_until', 'game_boost_until',
        'elite_until', 'fav_game', 'fav_artist', 'aura', 'last_aura', 'total_deposited', 'extra_beds'
    ]
    if field_name not in allowed_fields:
        return
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {field_name} = ? WHERE user_id = ?", (value, user_id))
        conn.commit()

def add_balance(user_id, amount):
    if abs(amount) > 1000000000000000000:
        return 0
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        new_balance = cursor.fetchone()
        return new_balance[0] if new_balance else 0

def add_withdraw_log(user_id, amount):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO withdraw_logs (user_id, amount, timestamp) VALUES (?, ?, ?)", 
                       (user_id, amount, time.time()))
        conn.commit()

def add_system_log(text):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO system_logs (text) VALUES (?)", (text,))
        conn.commit()

def get_last_logs(limit=10):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM withdraw_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_all_users():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
