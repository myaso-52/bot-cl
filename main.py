import sys
import os
import random
import sqlite3
import json
import re
from datetime import datetime, timedelta, timezone
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
TOKEN = "vk1.a.4NLW0LW3cobhYjBFzUQ1uvIF8Zn93a7G9W--YJ-URTkk9tf9Qt7TCXYFGv1pQ-o17M_1oRUhJMEV53edLMcBKwIB9F3JIRJl-Vi0YXAAT26pOvv3_XY5Yc6wj6PQmt8p2BVheWDb4GKoIsjBkTT9pyVWWTK3qv0LZwZJv7FOFqczW5BAc7X9Hub2eaYgeWt9txSLeBYlbB-MiTG47JBKkQ"
GROUP_ID = 240438650          # Цифровой ID вашей группы ВК
CONSOLE_PEER_ID = 2000000003  # ID чата для вывода логов консоли
OWNER_ID = 827888215         # Ваш личный цифровой ID ВКонтакте

vk_session = VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)
conn = sqlite3.connect("game_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    nickname TEXT DEFAULT 'Игрок',
    balance INTEGER DEFAULT 5000,
    clicks INTEGER DEFAULT 0,
    role INTEGER DEFAULT 0,
    reg_date TEXT DEFAULT '24.07.2026',
    withdrawals INTEGER DEFAULT 0,
    banned_until TEXT DEFAULT '0'
)
""")

cursor.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT)")
conn.commit()
def get_moscow_time():
    tz_moscow = timezone(timedelta(hours=3))
    return datetime.now(tz_moscow).strftime("[%H:%M:%S]")

def get_user(user_id):
    cursor.execute("SELECT nickname, balance, clicks, role, reg_date, withdrawals, banned_until FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        current_day = datetime.now(timezone(timedelta(hours=3))).strftime("%d.%m.%Y")
        cursor.execute("INSERT INTO users (user_id, reg_date) VALUES (?, ?)", (user_id, current_day))
        conn.commit()
        return ('Игрок', 5000, 0, 0, current_day, 0, '0')
    return res

def update_user(user_id, field, value):
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
def parse_mention(text):
    match = re.search(r'\[id(\d+)\|', text)
    if match: return int(match.group(1))
    match_url = re.search(r'vk\.com/id(\d+)', text)
    if match_url: return int(match_url.group(1))
    match_screen = re.search(r'vk\.com/([\w.]+)', text)
    if match_screen:
        try:
            res = vk.utils.resolveScreenName(screen_name=match_screen.group(1))
            if res and res['type'] == 'user': return res['object_id']
        except: return None
    return None

def send_msg(peer_id, text, keyboard=None, template=None):
    params = {"peer_id": peer_id, "message": text, "random_id": get_random_id()}
    if keyboard: params["keyboard"] = keyboard
    if template: params["template"] = template
    try: vk.messages.send(**params)
    except: pass

def log_to_console(text_command, user_id, chat_peer):
    time_str = get_moscow_time()
    log_message = f"{time_str} Использована команда: \"{text_command}\" в чате {chat_peer} от @id{user_id}"
    cursor.execute("INSERT INTO logs (text) VALUES (?)", (log_message,))
    conn.commit()
    send_msg(CONSOLE_PEER_ID, log_message)
def get_main_keyboard():
    keyboard = {
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": "Профиль"}, "color": "primary"},
             {"action": {"type": "text", "label": "Баланс"}, "color": "primary"}],
            [{"action": {"type": "text", "label": "кликер"}, "color": "positive"},
             {"action": {"type": "text", "label": "магазин"}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "Игры меню"}, "color": "secondary"}]
        ]
    }
    return json.dumps(keyboard, ensure_ascii=False)

def get_games_carousel():
    carousel = {
        "type": "carousel",
        "elements": [
            {"title": "Мини-игра Сапер", "description": "Угадай коробку!", "buttons": [{"action": {"type": "text", "label": "сапер"}, "color": "positive"}]},
            {"title": "Математика", "description": "Решай примеры за деньги", "buttons": [{"action": {"type": "text", "label": "математика"}, "color": "positive"}]},
            {"title": "Загадки", "description": "Мини-игра", "buttons": [{"action": {"type": "text", "label": "загадки"}, "color": "positive"}]}
        ]
    }
    return json.dumps(carousel, ensure_ascii=False)

print("Бот успешно инициализирован. Ожидание сообщений...")
for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        msg = event.obj.message
        peer_id = msg['peer_id']
        from_id = msg['from_id']
        text = msg['text'].strip()
        text_lower = text.lower()
        
        if from_id < 0: continue

        nickname, balance, clicks, role, reg_date, withdrawals, banned_until = get_user(from_id)
        if from_id == OWNER_ID and role != 5:
            role = 5
            update_user(from_id, "role", 5)

        if banned_until != '0':
            if banned_until == '-1':
                send_msg(peer_id, "❌ Вы заблокированы в боте НАВСЕГДА.")
                continue
            else:
                try:
                    unban_time = datetime.fromisoformat(banned_until)
                    if datetime.now(timezone(timedelta(hours=3))) < unban_time:
                        send_msg(peer_id, f"❌ Вы заблокированы в боте до {unban_time.strftime('%d.%m.%Y %H:%M')}.")
                        continue
                    else:
                        update_user(from_id, "banned_until", "0")
                except: pass

        roles_map = {0: "Игрок", 1: "Модератор", 2: "Администратор", 3: "Главный Администратор", 4: "Зам. Владельца", 5: "Владелец"}

        commands_triggers = [
            "баланс", "профиль", "топ клик", "рефка", "пополнить", "магазин", "сапер", "кликер", 
            "математика", "загадки", "игры меню", "bal", "исключить", "//logs", "//giveaward", 
            "//ban", "//moder", "//set0", "//update", "//chatid", "уб"
        ]
        if any(text_lower.startswith(trigger) for trigger in commands_triggers):
            log_to_console(text, from_id, peer_id)
        if text_lower == "баланс":
            send_msg(peer_id, f"💰 Ваш баланс: {balance} коинов.")
            
        elif text_lower == "профиль":
            profile_text = (
                f"👤 Профиль: {nickname}\n"
                f"🪐 Статус: {roles_map.get(role, 'Игрок')}\n"
                f"💰 Баланс: {balance} коинов\n"
                f"🖱️ Кликов: {clicks}\n"
                f"📅 Регистрация: {reg_date}"
            )
            send_msg(peer_id, profile_text, keyboard=get_main_keyboard())
            
        elif text_lower == "топ клик":
            cursor.execute("SELECT nickname, clicks FROM users ORDER BY clicks DESC LIMIT 5")
            top = cursor.fetchall()
            top_text = "🏆 ТОП ПО КЛИКАМ:\n"
            for i, user in enumerate(top, 1):
                top_text += f"{i}. {user[0]} — {user[1]} кликов\n"
            send_msg(peer_id, top_text)
            
        elif text_lower == "рефка":
            send_msg(peer_id, f"🔗 Ваша реферальная система:\nПриглашайте друзей по ссылке: ://vk.com{GROUP_ID}?ref={from_id}")
        elif text_lower.startswith("пополнить") and len(text.split()) == 2 and text.split()[1].isdigit():
            amount = int(text.split()[1])
            send_msg(peer_id, f"💳 Заявка на пополнение {amount} руб. в автокликер отправлена Владельцу в ЛС!")
            send_msg(OWNER_ID, f"🔔 Игрок @id{from_id} хочет пополнить баланс на {amount} руб.")
            
        elif text_lower == "магазин":
            send_msg(peer_id, "🏪 Магазин услуг мини-игр:\n1. Удвоение клика — 5000 коинов\n2. Иммунитет в Сапере — 10000 коинов")
            
        elif text_lower == "кликер":
            new_clicks = clicks + 1
            new_balance = balance + 50
            update_user(from_id, "clicks", new_clicks)
            update_user(from_id, "balance", new_balance)
            send_msg(peer_id, f"🖱️ Клик! Получено +50 коинов.\nВсего кликов: {new_clicks} | Баланс: {new_balance}")
            
        elif text_lower == "игры меню":
            send_msg(peer_id, "🎡 Открываю карусель мини-игр:", template=get_games_carousel())
            
        elif text_lower == "сапер":
            if random.choice([True, False]):
                update_user(from_id, "balance", balance + 1000)
                send_msg(peer_id, "📦 Вы открыли коробку и нашли +1000 коинов!")
            else:
                update_user(from_id, "balance", max(0, balance - 500))
                send_msg(peer_id, "💥 Бомба! Вы потеряли 500 коинов.")
                
        elif text_lower == "математика":
            n1, n2 = random.randint(10, 99), random.randint(10, 99)
            update_user(from_id, "balance", balance + 300)
            send_msg(peer_id, f"🧮 Пример повышенной сложности:\n{n1} + {n2} = ?\nВам начислено 300 коинов.")
            
        elif text_lower == "загадки":
            send_msg(peer_id, "❓ Загадка: Не лает, не кусает, а в дом не пускает? (Ответ: Замок)")
        elif text_lower.startswith("bal"):
            if role >= 1:
                target_id = parse_mention(text)
                if target_id:
                    t_nick, t_bal, _, _, _, _, _ = get_user(target_id)
                    send_msg(peer_id, f"💰 Баланс игрока {t_nick} (id{target_id}): {t_bal} коинов.")
                else:
                    send_msg(peer_id, "❌ Укажите пользователя ссылкой или упоминанием.")
                
        elif text_lower.startswith("исключить"):
            if role >= 1:
                target_id = parse_mention(text)
                if target_id:
                    try:
                        chat_id = peer_id - 2000000000
                        vk.messages.removeChatUser(chat_id=chat_id, user_id=target_id)
                        send_msg(peer_id, "✅ Пользователь успешно исключен из беседы.")
                    except Exception as e:
                        send_msg(peer_id, f"❌ Ошибка исключения. Проверьте права бота.\nДетали: {e}")
        elif text_lower == "//logs":
            if role >= 2:
                cursor.execute("SELECT text FROM logs ORDER BY id DESC LIMIT 10")
                logs_db = cursor.fetchall()
                logs_text = "📋 ПОСЛЕДНИЕ 10 ДЕЙСТВИЙ/ВЫВОДОВ:\n" + "\n".join([row[0] for row in logs_db])
                send_msg(peer_id, logs_text)
            
        elif text_lower.startswith("//giveaward"):
            if role >= 2:
                target_id = parse_mention(text)
                if target_id:
                    update_user(target_id, "nickname", "♠️ THE LEGENDARY")
                    send_msg(peer_id, f"✅ Игроку id{target_id} успешно установлена метка ♠️ THE LEGENDARY")
        elif text_lower.startswith("//ban"):
            if role >= 3:
                parts = text.split()
                if len(parts) >= 3:
                    try:
                        days = int(parts[1])
                        target_id = parse_mention(text)
                        if target_id:
                          if days == -1:
                            update_user(target_id, "banned_until", "-1")
                            send_msg(peer_id, f"⛔ Пользователь id{target_id} заблокирован НАВСЕГДА.")
                          elif days == 0:
                            update_user(target_id, "banned_until", "0")
                            send_msg(peer_id, f"✅ Пользователь id{target_id} успешно РАЗБЛОКИРОВАН.")
                          else:
                            end_time = datetime.now(timezone(timedelta(hours=3))) + timedelta(days=days)
                            update_user(target_id, "banned_until", end_time.isoformat())
                            send_msg(peer_id, f"⛔ Пользователь id{target_id} заблокирован на {days} дней.")
                    except Exception as e:
                        send_msg(peer_id, f"❌ Ошибка бана. Проверьте синтаксис. {e}")
                    
        elif text_lower.startswith("//moder") and role == 3:
            parts = text.split()
            if len(parts) >= 3:
                try:
                    target_role = int(parts[1])
                    target_id = parse_mention(text)
                    if target_id and -1 <= target_role <= 2:
                        final_role = 0 if target_role == -1 else target_role
                        update_user(target_id, "role", final_role)
                        send_msg(peer_id, f"✅ Ранг пользователя id{target_id} изменен на {final_role}.")
                except: pass
        if role >= 4:
            if text_lower.startswith("//moder") and role == 4:
                parts = text.split()
                try:
                    target_role = int(parts[1])
                    target_id = parse_mention(text)
                    if target_id and -1 <= target_role <= 3:
                        final_role = 0 if target_role == -1 else target_role
                        update_user(target_id, "role", final_role)
                        send_msg(peer_id, f"✅ Заместитель изменил ранг id{target_id} на {final_role}.")
                except: pass

            elif text_lower.startswith("//set0"):
                parts = text.split()
                if len(parts) >= 3:
                    mode = parts[1].lower()
                    target_id = parse_mention(text)
                    if target_id:
                        if mode == "nk": update_user(target_id, "nickname", "Игрок")
                        elif mode == "cl": update_user(target_id, "clicks", 0)
                        elif mode == "bl": update_user(target_id, "balance", 0)
                        elif mode == "rg": 
                            current_day = datetime.now(timezone(timedelta(hours=3))).strftime("%d.%m.%Y")
                            update_user(target_id, "reg_date", current_day)
                        elif mode == "vv": update_user(target_id, "withdrawals", 0)
                        elif mode == "all":
                            current_day = datetime.now(timezone(timedelta(hours=3))).strftime("%d.%m.%Y")
                            cursor.execute("UPDATE users SET nickname='Игрок', clicks=0, balance=0, reg_date=?, withdrawals=0 WHERE user_id=?", (current_day, target_id))
                            conn.commit()
                        send_msg(peer_id, f"⚙️ Параметр [{mode}] пользователя id{target_id} успешно обнулен.")

        if role == 5:
            if text_lower.startswith("//moder"):
                parts = text.split()
                try:
                    target_role = int(parts[1])
                    target_id = parse_mention(text)
                    if target_id and -1 <= target_role <= 5:
                        final_role = 0 if target_role == -1 else target_role
                        update_user(target_id, "role", final_role)
                        send_msg(peer_id, f"👑 Владелец изменил ранг id{target_id} на {final_role}.")
                except: pass

            elif text_lower == "//update":
                send_msg(peer_id, "🔄 Файлы обновляются. Перезапуск бота...")
                os.execv(sys.executable, ['python'] + sys.argv)
                
            elif text_lower == "//chatid":
                send_msg(peer_id, f"🆔 ID этого чата (peer_id): {peer_id}")
                
            elif text_lower.startswith("пополнить") or text_lower.startswith("уб"):
                parts = text.split()
                target_id = parse_mention(text)
                if target_id and parts[-1].isdigit():
                    money = int(parts[-1])
                    _, t_bal, _, _, _, _, _ = get_user(target_id)
                    update_user(target_id, "balance", t_bal + money)
                    send_msg(peer_id, f"✅ Баланс пользователя id{target_id} успешно пополнен на {money} коинов!")
