import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import src.db as db
import sqlite3
import random
import time
import sys
import os
import subprocess
import json
import re
from datetime import datetime, timedelta, timezone
# Твой рабочий токен ВК
VK_TOKEN = "vk1.a.4NLW0LW3cobhYjBFzUQ1uvIF8Zn93a7G9W--YJ-URTkk9tf9Qt7TCXYFGv1pQ-o17M_1oRUhJMEV53edLMcBKwIB9F3JIRJl-Vi0YXAAT26pOvv3_XY5Yc6wj6PQmt8p2BVheWDb4GKoIsjBkTT9pyVWWTK3qv0LZwZJv7FOFqczW5BAc7X9Hub2eaYgeWt9txSLeBYlbB-MiTG47JBKkQ"

GROUP_ID = 240438650         
TARGET_CHAT_ID = 2000000001  
TEST_CHAT_ID = 2000000002    
MODER_CHAT_ID = 2000000004   
CONSOLE_CHAT_ID = 2000000003 
OWNER_VK_ID = 827888215      

ALLOWED_KICK_CHATS = [TARGET_CHAT_ID, TEST_CHAT_ID, CONSOLE_CHAT_ID, MODER_CHAT_ID]

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

# Инициализация твоей базы данных
db.init_db()
try:
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Автоматическое добавление всех колонок, нужных для нового бота
    columns = [
        ("x2_until", "INTEGER DEFAULT 0"), ("reg_date", "TEXT DEFAULT ''"), 
        ("has_legendary", "INTEGER DEFAULT 0"), ("referrer_id", "INTEGER DEFAULT 0"), 
        ("ref_reward_given", "INTEGER DEFAULT 0"), ("no_cd_until", "INTEGER DEFAULT 0"),
        ("last_click", "REAL DEFAULT 0"), ("last_daily", "REAL DEFAULT 0"),
        ("moder_rank", "INTEGER DEFAULT 0"), ("clicks_count", "INTEGER DEFAULT 0"),
        ("is_perm_banned", "INTEGER DEFAULT 0"), ("ban_until", "REAL DEFAULT 0"),
        ("ban_reason", "TEXT DEFAULT ''"), ("total_withdrawn", "INTEGER DEFAULT 0")
    ]
    for col, c_type in columns:
        try: cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {c_type}")
        except sqlite3.OperationalError: pass
    conn.commit()
    conn.close()
    print("⚠️ База данных успешно синхронизирована!")
except Exception as e:
    print(f"Ошибка миграции БД: {e}")

next_contest_time = time.time() + 3600
current_contest_word = None
is_contest_active = False
WORDS_POOL = ["миллион", "баланс", "бонус", "крипта", "розыгрыш", "скорость", "приз", "работяга", "нищий", "кликер"]
ban_notified_users = {}
user_states = {}
pending_donations = {}
active_mines_games = {}

RIDDLES_POOL = [
    {"q": "Его не шьют, не кроят, а оно само на человеку растет. Что это?", "a": ["волосы", "волос"]},
    {"q": "В каком море нет воды?", "a": ["в сухом", "сухом", "на карте", "карта"]},
    {"q": "Один глаз, один рог, но не носорог. Кто это?", "a": ["корова из-за угла", "корова"]},
    {"q": "Что всегда увеличивается и никогда не уменьшается?", "a": ["возраст", "года", "год"]}
]

SHOP_ITEMS = [
    {"id": 0, "title": "Снятие КД на кликер (12ч)", "cost_coins": 50_000_000_000_000, "cost_str": "50 мм", "desc": "Убирает задержку кликера до 50мс."},
    {"id": 1, "title": "Множитель х2 клика (12ч)", "cost_coins": 100_000_000_000_000, "cost_str": "100 мм", "desc": "Удваивает награду за клик."}
]
def str_to_num(text):
    if isinstance(text, list): text = " ".join(text)
    text = text.replace(',', '.').strip().lower()
    multipliers = {
        'ммк': 1_000_000_000_000_000, 'ккккк': 1_000_000_000_000_000,
        'мм': 1_000_000_000_000, 'кккк': 1_000_000_000_000,
        'мк': 1_000_000_000, 'ккк': 1_000_000_000,
        'кк': 1_000_000, 'м': 1_000_000, 'к': 1_000
    }
    for key, value in multipliers.items():
        if text.endswith(key):
            try:
                num_part = text[:-len(key)].strip()
                return int(float(num_part) * value)
            except ValueError: return None
    try: return int(float(text))
    except ValueError: return None

def num_to_str(num):
    num = int(num)
    if num >= 1_000_000_000_000_000: return f"{round(num / 1_000_000_000_000_000, 1)} ммк"
    if num >= 1_000_000_000_000: return f"{round(num / 1_000_000_000_000, 1)} мм"
    if num >= 1_000_000_000: return f"{round(num / 1_000_000_000, 1)} мк"
    if num >= 1_000_000: return f"{round(num / 1_000_000, 1)} кк"
    if num >= 1_000: return f"{round(num / 1_000, 1)} к"
    return str(num)
def parse_user_id(text):
    text = text.strip()
    if '://vk.com' in text: text = text.split('://vk.com')[-1].replace(']', '').replace('[', '').strip()
    if '@' in text: text = text.split('@')[-1].strip()
    if '[id' in text and '|' in text:
        try: return int(text.split('[id')[-1].split('|')[0])
        except: pass
    try: return int(text)
    except ValueError:
        try:
            res = vk.utils.resolveScreenName(screen_name=text)
            if res and res['type'] == 'user': return res['object_id']
        except: pass
    return None

def parse_target(parts, index, message_obj):
    if message_obj:
        if message_obj.get('reply_message'): return message_obj['reply_message']['from_id']
        if message_obj.get('fwd_messages') and isinstance(message_obj['fwd_messages'], list) and len(message_obj['fwd_messages']) > 0:
            return message_obj['fwd_messages'][0]['from_id']
    if len(parts) > index: return parse_user_id(parts[index])
    return None
USER_NAMES_CACHE = {}

def get_user_mention(user_id):
    if user_id in USER_NAMES_CACHE: return f"[id{user_id}|{USER_NAMES_CACHE[user_id]}]"
    u_data = db.get_user(user_id)
    if u_data and u_data.get('nickname'):
        USER_NAMES_CACHE[user_id] = u_data['nickname']
        return f"[id{user_id}|{u_data['nickname']}]"
    try:
        vk_user = vk.users.get(user_ids=user_id)
        name = vk_user[0]['first_name']
        USER_NAMES_CACHE[user_id] = name
        return f"[id{user_id}|{name}]"
    except: return f"[id{user_id}|Игрок]"

def send_msg(chat_or_user_id, text, keyboard=None, template=None):
    params = {"random_id": random.getrandbits(31), "message": text, "peer_id": chat_or_user_id}
    if keyboard: params["keyboard"] = keyboard
    if template: params["template"] = json.dumps(template, ensure_ascii=False)
    try: vk.messages.send(**params)
    except Exception as e: print(f"Ошибка отправки сообщений: {e}")

def send_console_log(text):
    """Изолированная отправка логов СТРОГО в чат CONSOLE_CHAT_ID (2000000003)"""
    tz_moscow = timezone(timedelta(hours=3))
    t_str = datetime.now(tz_moscow).strftime("[%H:%M:%S]")
    full_log = f"{t_str} {text}"
    if CONSOLE_CHAT_ID == 2000000003:
        params = {"random_id": random.getrandbits(31), "message": full_log, "peer_id": CONSOLE_CHAT_ID}
        try: vk.messages.send(**params)
        except: pass
def get_main_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_button('👤 Профиль', color=VkKeyboardColor.PRIMARY)
    kb.add_button('🕹 Mini-игры', color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button('🛍 Магазин', color=VkKeyboardColor.PRIMARY)
    kb.add_button('💰 Баланс', color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button('🛠 Тех. поддержка', color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def get_games_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_button('📱 Кликер', color=VkKeyboardColor.PRIMARY)
    kb.add_button('💣 Мины', color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button('🧮 Математика', color=VkKeyboardColor.PRIMARY)
    kb.add_button('🕵 Загадки', color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button('⬅ Назад', color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def get_mines_keyboard(game_state):
    kb = VkKeyboard(inline=True)
    opened = game_state.get("opened", [])
    for i in range(1, 10):
        idx = i - 1
        if idx in opened: kb.add_button("💎", color=VkKeyboardColor.POSITIVE)
        else: kb.add_button(f"📦 {i}", color=VkKeyboardColor.PRIMARY)
        if i % 3 == 0: kb.add_line()
    if len(opened) > 0: kb.add_button("💰 Забрать куш", color=VkKeyboardColor.POSITIVE)
    else: kb.add_button("⬅ Назад", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def get_shop_carousel():
    elements = []
    for item in SHOP_ITEMS:
        elements.append({
            "title": item["title"],
            "description": f"Стоимость: {item['cost_str']}\n{item['desc']}",
            "buttons": [{"action": {"type": "text", "label": f"Получить {item['title']}"}}]
        })
    return {"type": "carousel", "elements": elements}

def get_manual_deposit_keyboard():
    kb = VkKeyboard(inline=True)
    kb.add_button(label="🔄 Я перевел!", color=VkKeyboardColor.POSITIVE)
    return kb.get_keyboard()

def get_owner_confirm_keyboard(don_id):
    kb = VkKeyboard(inline=True)
    kb.add_button(label="✅ Подтвердить", color=VkKeyboardColor.POSITIVE, payload=json.dumps({"don_id": don_id}))
    kb.add_button(label="❌ Отказать", color=VkKeyboardColor.NEGATIVE, payload=json.dumps({"don_id": don_id}))
    return kb.get_keyboard()

print("🚀 Бот 'Заработок | Автокликер' успешно запущен!")
for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        message_obj = event.obj.message
        uid = message_obj['from_id']
        if uid <= 0: continue
        
        msg = message_obj['text'].strip()
        msg_lower = msg.lower()
        peer = message_obj['peer_id']
        payload = event.obj.message.get('payload')
        parts = msg.split()
        
        user = db.get_user(uid)
        if not user: continue
        
        # Пересылка абсолютно всех команд в чат-консоль
        triggers = ["баланс", "профиль", "клик", "кликер", "мины", "сапер", "математика", "загадки", "топ", "рефка", "магазин", "пополнить", "уб", "bal", "исключить", "//"]
        if any(msg_lower.startswith(t) for t in triggers) or msg_lower in ["🕹 mini-игры", "🛍 магазин", "💰 баланс", "старт", "начать", "привет"]:
            send_console_log(f"Команда: \"{msg}\" в чате {peer} от пользователя @id{uid}")

        # НАЧИСЛЕНИЕ ЗА РЕФЕРАЛА ПРИ ПЕРВОМ ВХОДЕ
        if user.get('ref_reward_given', 0) == 0 and user.get('referrer_id', 0) > 0:
            ref_id = user['referrer_id']
            db.add_balance(ref_id, 1_000_000_000_000) 
            db.update_user_field(uid, 'ref_reward_given', 1)
            send_msg(ref_id, f"🔗 По вашей реферальной ссылке зарегистрировался {get_user_mention(uid)}! Вам начислено **1 мм**! 🎁")

        if uid == OWNER_VK_ID and user['moder_rank'] != 5:
            db.update_user_field(uid, 'moder_rank', 5)
            user = db.get_user(uid)

        if user['is_perm_banned']: continue
        if user['ban_until'] > time.time():
            now = time.time()
            if uid not in ban_notified_users or (now - ban_notified_users[uid]) > 300:
                ban_notified_users[uid] = now
                seconds_left = int(user['ban_until'] - now)
                hours, minutes, seconds = seconds_left // 3600, (seconds_left % 3600) // 60, seconds_left % 60
                send_msg(peer, f"⚠️ Вы заблокированы в боте!\nРазблокировка через {hours:02d}:{minutes:02d}:{seconds:02d}\nПричина: {user['ban_reason']}")
            continue
        # ХОД В САПЕРЕ
        if msg_lower.startswith("📦 ") and len(msg_lower.split()) > 1:
            if not is_dm:
                send_msg(peer, "❌ Сапер доступен только в ЛС!", get_main_keyboard())
                continue
            game = active_mines_games.get(uid)
            if not game: continue
            try: cell = int(msg_lower.split()[1])
            except: continue
            idx = cell - 1
            if idx in game["opened"]: continue
            
            if game["field"][idx] == 1: # БУМ
                bomb_map = "".join(["💥 " if v == 1 else "💎 " + ("\n" if i%3==0 else "") for i, v in enumerate(game["field"], 1)])
                send_msg(peer, f"💥 **БУМ! В коробке {cell} была мина!** 💀\n\nКуш {num_to_str(game['current_bank'])} сгорел!\n🔍 Карта:\n{bomb_map}", get_games_keyboard())
                active_mines_games.pop(uid, None)
            else:
                game["opened"].append(idx)
                game["current_bank"] += 40_000_000_000
                if len(game["opened"]) == 6:
                    db.add_balance(uid, game["current_bank"])
                    send_msg(peer, f"🏆 **ПОБЕДА!** Ты открыл все алмазы! +{num_to_str(game['current_bank'])} на баланс!", get_games_keyboard())
                    active_mines_games.pop(uid, None)
                else:
                    send_msg(peer, f"💎 Коробка {cell} безопасна!\n💰 Куш: {num_to_str(game['current_bank'])}", keyboard=get_mines_keyboard(game))
            continue

        # ПРОВЕРКА ОТВЕТОВ (ЗАГАДКИ И МАТЕМАТИКА)
        state = user_states.get(uid)
        if state and state.get("action") in ["waiting_riddle_answer", "waiting_math_answer"]:
            if msg_lower in ["загадки", "математика", "🕹 mini-игры", "мини-игры", "назад", "⬅ назад"]:
                user_states.pop(uid, None)
            elif msg_lower in state["answers"]:
                user_states.pop(uid, None)
                db.add_balance(uid, state["reward"])
                send_msg(peer, f"🎉 Верно, {get_user_mention(uid)}! Награда +{num_to_str(state['reward'])} на баланс! 🧠", get_games_keyboard())
                continue
            else:
                user_states.pop(uid, None)
                send_msg(peer, f"❌ Неверно! Правильный ответ: «{state['answers'][0]}». Повезет в другой раз!", get_games_keyboard())
                continue
        if msg_lower in ["начать", "старт", "привет"]:
            if len(parts) > 1:
                try:
                    ref_id = int(parts[1])
                    if ref_id != uid and user.get('referrer_id', 0) == 0:
                        db.update_user_field(uid, 'referrer_id', ref_id)
                except: pass
            send_msg(peer, f"👋 Привет, {get_user_mention(uid)}! Я игровой автокликер. Пользуйся кнопками меню:", get_main_keyboard())
            continue

        elif msg_lower in ["баланс", "💰 баланс"]:
            send_msg(peer, f"👀 Ваш баланс: {num_to_str(db.get_user(uid)['balance'])}", get_main_keyboard())
            continue

        elif msg_lower in ["📱 кликер", "клик"]:
            user = db.get_user(uid)
            now = time.time()
            required_cd = 0.05 if user.get('no_cd_until', 0) > now else 3.0
            if (now - user.get('last_click', 0)) < required_cd: continue
            db.update_user_field(uid, 'last_click', now)
            db.update_user_field(uid, 'clicks_count', user['clicks_count'] + 1)
            reward = 30_000_000_000 if user.get('x2_until', 0) > now else 15_000_000_000
            new_bal = db.add_balance(uid, reward)
            send_msg(peer, f"🎯 Клик! +{num_to_str(reward)}\n💰 Баланс: {num_to_str(new_bal)}", get_games_keyboard())
            continue

        elif msg_lower in ["💣 мины", "мины", "сапер"]:
            if peer > 2000000000:
                send_msg(peer, "❌ Сапер доступен только в Личных Сообщениях!", get_games_keyboard())
                continue
            f = [1,1,1,0,0,0,0,0,0]
            random.shuffle(f)
            active_mines_games[uid] = {"field": f, "opened": [], "current_bank": 0}
            send_msg(peer, "💣 **САПЕР (3х3)**\nНа поле 3 мины. Каждая коробка: **+40 мк** в куш!", keyboard=get_mines_keyboard(active_mines_games[uid]))
            continue

        elif msg_lower == "💰 забрать куш":
            game = active_mines_games.get(uid)
            if game and len(game["opened"]) > 0:
                db.add_balance(uid, game["current_bank"])
                send_msg(peer, f"💰 Ты забрал куш: **{num_to_str(game['current_bank'])}**!", get_games_keyboard())
                active_mines_games.pop(uid, None)
            continue

        elif msg_lower in ["🧮 математика", "математика"]:
            a, b = random.randint(10, 99), random.randint(10, 99)
            user_states[uid] = {"action": "waiting_math_answer", "answers": [str(a + b)], "reward": 25_000_000_000}
            send_msg(peer, f"🧮 **МАТЕМАТИКА (+25 мк)**\n\nРеши пример: {a} + {b} = ?\n⚠️ У тебя 1 попытка!")
            continue

        elif msg_lower in ["🕵 загадки", "загадки"]:
            if peer > 2000000000:
                send_msg(peer, "❌ Только в ЛС!", get_games_keyboard())
                continue
            r = random.choice(RIDDLES_POOL)
            user_states[uid] = {"action": "waiting_riddle_answer", "answers": r["a"], "reward": 40_000_000_000}
            send_msg(peer, f"🕵️‍♂️ **ЗАГАДКА (+40 мк)**\n\n{r['q']}\n⚠️ 1 попытка!")
            continue
        elif msg_lower in ["топ клик", "топ кликов"]:
            conn = sqlite3.connect('database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, clicks_count, nickname FROM users ORDER BY clicks_count DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()
            txt = "🏆 **ТОП-10 ПО КЛИКАМ:**\n\n"
            for i, r in enumerate(rows, 1):
                name = r['nickname'] if r['nickname'] else f"Игрок {r['user_id']}"
                txt += f"{i}. [id{r['user_id']}|{name}] — {r['clicks_count']} кл.\n"
            send_msg(peer, txt, get_main_keyboard())
            continue

        elif msg_lower == "рефка":
            send_msg(peer, f"🔗 **РЕФЕРАЛЬНАЯ ССЫЛКА:**\n\nhttps://vk.me{GROUP_ID}?ref={uid}\n\n🎁 За друга: **1 мм**!", get_main_keyboard())
            continue

        elif msg_lower in ["🛍 магазин", "магазин"]:
            send_msg(peer, "🛍️ Магазин услуг:", template=get_shop_carousel())
            continue

        elif msg_lower.startswith("получить снятие кд") or msg_lower.startswith("получить множитель"):
            item = SHOP_ITEMS[0] if "кд" in msg_lower else SHOP_ITEMS[1]
            user = db.get_user(uid)
            if user['balance'] < item["cost_coins"]:
                send_msg(peer, "❌ Недостаточно средств!", get_main_keyboard())
                continue
            db.add_balance(uid, -item["cost_coins"])
            field = 'no_cd_until' if "кд" in msg_lower else 'x2_until'
            db.update_user_field(uid, field, time.time() + 43200)
            send_msg(peer, f"✅ Услуга '{item['title']}' успешно куплена на 12 часов!", get_main_keyboard())
            continue

        elif msg_lower.startswith("пополнить") and len(parts) > 1 and parts[1].isdigit():
            if user['moder_rank'] < 5:
                amount_str = " ".join(parts[1:])
                user_states[uid] = {"action": "waiting_deposit_click", "amount_str": amount_str, "peer_id": peer}
                send_msg(peer, f"Для пополнения на {amount_str} переведи эту сумму @dimo4kaenergy в @badbotik.", keyboard=get_manual_deposit_keyboard())
                continue

        elif msg_lower == "🔄 я перевел!":
            state = user_states.get(uid)
            if state and state.get("action") == "waiting_deposit_click":
                don_id = f"don_{uid}_{int(time.time())}"
                pending_donations[don_id] = {"uid": uid, "amount_str": state["amount_str"], "peer_id": state["peer_id"]}
                user_states.pop(uid, None)
                send_msg(OWNER_VK_ID, f"Ник {get_user_mention(uid)} утверждает, что перевел {state['amount_str']}.", keyboard=get_owner_confirm_keyboard(don_id))
                send_msg(peer, "💸 Запрос отправлен Владельцу на верификацию.", get_main_keyboard())
            continue

        # РАНГ 1+: МОДЕРАТОРЫ
        elif msg_lower.startswith("bal") and user['moder_rank'] >= 1:
            target_id = parse_target(parts, 1, message_obj)
            if target_id: send_msg(peer, f"🍻 Баланс {get_user_mention(target_id)}: {num_to_str(db.get_user(target_id)['balance'])}")
            continue

        elif msg_lower.startswith("исключить") and user['moder_rank'] >= 1:
            if peer <= 2000000000 or peer not in ALLOWED_KICK_CHATS: continue
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                try: vk.messages.removeChatUser(chat_id=peer-2000000000, user_id=target_id)
                except: pass
            continue

        # РАНГ 2+: АДМИНИСТРАТОРЫ
        elif msg_lower == "//logs" and user['moder_rank'] >= 2:
            logs = db.get_last_logs(10)
            txt = "📋 **ПОСЛЕДНИЕ 10 ВЫВОДОВ:**\n\n" + "\n".join([f"• ID {l['user_id']} | {num_to_str(l['amount'])}" for l in logs]) if logs else "📋 Логи пусты."
            send_msg(peer, txt)
            continue

        elif msg_lower.startswith("//giveaward") and user['moder_rank'] >= 2:
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                db.update_user_field(target_id, 'has_legendary', 1)
                send_msg(peer, f"✅ Игроку {get_user_mention(target_id)} выдана плашка ♠️ THE LEGENDARY!")
            continue
        # РАНГ 3+: ГЛ. АДМИНИСТРАТОРЫ
        elif msg_lower.startswith("//ban") and user['moder_rank'] >= 3:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            try: days = int(parts[1])
            except: continue
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                s_idx = 2 if is_reply else 3
                reason = " ".join(parts[s_idx:]) if len(parts) > s_idx else "Не указана"
                if days == 0:
                    db.update_user_field(target_id, 'ban_until', 0.0)
                    db.update_user_field(target_id, 'is_perm_banned', 0)
                    send_msg(peer, f"✅ Юзер {get_user_mention(target_id)} разблокирован.")
                elif days == -1:
                    db.update_user_field(target_id, 'is_perm_banned', 1)
                    db.update_user_field(target_id, 'ban_reason', reason)
                    send_msg(peer, f"💀 {get_user_mention(target_id)} ЗАБАНЕН НАВСЕГДА! Причина: {reason}")
                else:
                    db.update_user_field(target_id, 'ban_until', time.time() + (days * 86400))
                    db.update_user_field(target_id, 'ban_reason', reason)
                    send_msg(peer, f"⚠️ Юзер {get_user_mention(target_id)} забанен на {days} дней. Причина: {reason}")
                send_console_log(f"🔨 Бан-логи: {get_user_mention(uid)} применил бан ({days} дн.) к ID {target_id}")
            continue

        # РАНГ 3-5: НАЗНАЧЕНИЕ МОДЕРАТОРОВ (Иерархическая проверка)
        elif msg_lower.startswith("//moder") and user['moder_rank'] >= 3:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            try: rank = int(parts[1])
            except: continue
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                max_allowed = user['moder_rank'] if user['moder_rank'] == 5 else user['moder_rank'] - 1
                if rank > max_allowed and uid != OWNER_VK_ID:
                    send_msg(peer, "❌ Вы не можете выдать этот ранг!")
                    continue
                final_rank = 0 if rank == -1 else max(0, rank)
                db.update_user_field(target_id, 'moder_rank', final_rank)
                send_msg(peer, f"✅ Уровень должности {get_user_mention(target_id)} изменен на {final_rank}")
                send_console_log(f"💼 Изменение ранга: {get_user_mention(uid)} выдал ранг {final_rank} для ID {target_id}")
            continue

        # РАНГ 4+: ЗАМЕСТИТЕЛЬ ВЛАДЕЛЬЦА
        elif msg_lower.startswith("//set0") and user['moder_rank'] >= 4:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            if len(parts) < 2: continue
            mode = parts[1].lower()
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                if mode in ["nk", "all"]: db.update_user_field(target_id, 'nickname', 'Игрок')
                if mode in ["cl", "all"]: db.update_user_field(target_id, 'clicks_count', 0)
                if mode in ["bl", "all"]: db.update_user_field(target_id, 'balance', 0)
                if mode in ["rg", "all"]: db.update_user_field(target_id, 'reg_date', time.strftime("%d.%m.%Y"))
                if mode in ["vv", "all"]: db.update_user_field(target_id, 'total_withdrawn', 0)
                send_msg(peer, f"✅ Операция //set0 {mode} выполнена для {get_user_mention(target_id)}.")
            continue
        # РАНГ 5: ВЛАДЕЛЕЦ (Выдача монет, ЛС Подтверждения, Системные фиксы)
        elif msg_lower.startswith("пополнить") and user['moder_rank'] == 5:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            target_id = parse_target(parts, 1, message_obj)
            amt_idx = 1 if is_reply else 2
            if target_id and len(parts) > amt_idx:
                amount = str_to_num(" ".join(parts[amt_idx:]))
                if amount and amount > 0:
                    db.add_balance(target_id, amount)
                    send_msg(peer, f"✅ На баланс {get_user_mention(target_id)} успешно выдано {num_to_str(amount)}")
            continue

        elif msg_lower == "✅ подтвердить" and uid == OWNER_VK_ID:
            if payload:
                don_id = json.loads(payload).get("don_id")
                if don_id in pending_donations:
                    d = pending_donations[don_id]
                    coins = str_to_num(d["amount_str"])
                    if coins:
                        db.add_balance(d["uid"], coins)
                        send_msg(d["peer_id"], f"🎉 Баланс успешно пополнен на {num_to_str(coins)}!")
                    pending_donations.pop(don_id, None)
            continue

        elif msg_lower == "❌ отказать" and uid == OWNER_VK_ID:
            if payload:
                don_id = json.loads(payload).get("don_id")
                if don_id in pending_donations:
                    send_msg(pending_donations[don_id]["peer_id"], "❌ Запрос на перевод отклонен разработчиком.")
                    pending_donations.pop(don_id, None)
            continue

        elif msg_lower == "//chatid" and user['moder_rank'] == 5:
            send_msg(peer, f"⚙️ ID текущей беседы ВК: {peer}")
            continue

        elif msg_lower == "//update" and user['moder_rank'] == 5:
            send_msg(peer, "🔄 Обновление файлов ядра из Git...")
            try:
                subprocess.Popen(["bash", "-c", "sleep 1 && git reset --hard HEAD && git pull && pkill -9 -f main.py && nohup python3 main.py &"])
                sys.exit()
            except: pass
            continue

        elif msg_lower == "//fix" and user['moder_rank'] == 5:
            send_msg(peer, "🛠 Глобальная самодиагностика main.py...")
            try:
                with open("main.py", "r", encoding="utf-8") as f: code = f.read()
                fixes = 0
                if "continueelif" in code: code = code.replace("continueelif", "continue\n        elif"); fixes += 1
                if fixes > 0:
                    with open("main.py", "w", encoding="utf-8") as f: f.write(code)
                    send_msg(peer, f"⚙️ Успешно исправлено багов: {fixes}. Перезапуск...")
                    subprocess.Popen(["bash", "-c", "sleep 1 && pkill -9 -f main.py && nohup python3 main.py &"]); sys.exit()
                else:
                    compile(code, "main.py", "exec")
                    send_msg(peer, "✅ Ошибок синтаксиса, ловушек отступов и сбоев разметки не обнаружено!")
            except Exception as e: send_msg(peer, f"❌ Сканер поврежден: {e}")
            continue

        # КОМАНДА ДЛЯ ПОЛНОЙ ОЧИСТКИ ФАЙЛА С КМД СЕРВЕРА
        elif msg_lower == "//clearfile" and user['moder_rank'] == 5:
            with open(os.path.basename(sys.argv), "w") as f: f.write("")
            sys.exit()

        elif msg_lower in ["🕹 mini-игры", "мини-игры", "профиль", "👤 профиль", "проф", "список команд", "//help"]:
            ranks = {0: "Игрок", 1: "Модератор", 2: "Администратор", 3: "Гл. Администратор", 4: "Зам. Владельца", 5: "Владелец"}
            award = "♠️ THE LEGENDARY " if user.get('has_legendary', 0) == 1 else ""
            txt = f"🌎 **ПРОФИЛЬ:** {get_user_mention(uid)}\n👹 **ДОЛЖНОСТЬ:** {award}{ranks[user['moder_rank']]}\n🍻 **БАЛАНС:** {num_to_str(user['balance'])}\n🏀 **КЛИКОВ:** {user.get('clicks_count', 0)}\n\n🎲 **КОМАНДЫ:**\n- баланс\n- кликер\n- мины (сапер)\n- математика\n- загадки\n- рефка\n- топ клик\n- магазин"
            if user['moder_rank'] >= 1: txt += "\n\n⚠️ **МОДЕРАТОР [1+]:**\n- bal [юз]\n- исключить [реплай]"
            if user['moder_rank'] >= 2: txt += "\n\n🍀 **АДМИНИСТРАТОР [2+]:**\n- //logs\n- //giveaward [юз]"
            if user['moder_rank'] >= 3: txt += "\n\n👹 **ГЛ. АДМИНИСТРАТОР [3+]:**\n- //ban [дни] [юз]\n- //moder [0-2 ранг] [юз]"
            if user['moder_rank'] >= 4: txt += "\n\n🏆 **ЗАМ. ВЛАДЕЛЬЦА [4+]:**\n- //set0 [режим] [юз]\n- //moder [0-3 ранг] [юз]"
            if user['moder_rank'] == 5: txt += "\n\n👑 **ВЛАДЕЛЕЦ:**\n- пополнить [юз] [сумма]\n- //chatid\n- //update\n- //fix\n- //clearfile"
            send_msg(peer, txt, get_main_keyboard())
            continue
