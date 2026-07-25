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

# Инициализация базы данных
db.init_db()
print("⚠️ База данных успешно синхронизирована!")

next_contest_time = time.time() + 3600
current_contest_word = None
is_contest_active = False
WORDS_POOL = ["миллион", "баланс", "бонус", "крипта", "розыгрыш", "скорость", "приз", "работяга", "нищий", "кликер"]
ban_notified_users = {}
user_states = {}
pending_donations = {}
pending_withdrawals = {}
active_mines_games = {}

RIDDLES_POOL = [
    {"q": "Его не шьют, не кроят, а оно само на человеке растет. Что это?", "a": ["волосы", "волос"]},
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
            except ValueError:
                return None
    try:
        return int(float(text))
    except ValueError:
        return None

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
    if '://vk.com' in text:
        text = text.split('://vk.com')[-1].replace(']', '').replace('[', '').strip()
    if '@' in text:
        text = text.split('@')[-1].strip()
    if '[id' in text and '|' in text:
        try:
            return int(text.split('[id')[-1].split('|')[0])
        except:
            pass
    try:
        return int(text)
    except ValueError:
        try:
            res = vk.utils.resolveScreenName(screen_name=text)
            if res and res['type'] == 'user':
                return res['object_id']
        except:
            pass
    return None

def parse_target(parts, index, message_obj):
    if message_obj:
        if message_obj.get('reply_message'):
            return message_obj['reply_message']['from_id']
        if message_obj.get('fwd_messages') and isinstance(message_obj['fwd_messages'], list) and len(message_obj['fwd_messages']) > 0:
            return message_obj['fwd_messages'][0]['from_id']
    if len(parts) > index:
        return parse_user_id(parts[index])
    return None

USER_NAMES_CACHE = {}

def get_user_mention(user_id):
    if user_id in USER_NAMES_CACHE:
        return f"[id{user_id}|{USER_NAMES_CACHE[user_id]}]"
    u_data = db.get_user(user_id)
    if u_data and u_data.get('nickname') and u_data['nickname'] != 'Игрок':
        USER_NAMES_CACHE[user_id] = u_data['nickname']
        return f"[id{user_id}|{u_data['nickname']}]"
    try:
        vk_user = vk.users.get(user_ids=user_id)
        name = vk_user[0]['first_name']
        USER_NAMES_CACHE[user_id] = name
        return f"[id{user_id}|{name}]"
    except:
        return f"[id{user_id}|Игрок]"

def send_msg(chat_or_user_id, text, keyboard=None, template=None):
    params = {"random_id": random.getrandbits(31), "message": text, "peer_id": chat_or_user_id}
    if keyboard:
        params["keyboard"] = keyboard
    if template:
        params["template"] = json.dumps(template, ensure_ascii=False)
    try:
        vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка отправки сообщений: {e}")

def send_console_log(text_command, user_id, chat_peer):
    tz_moscow = timezone(timedelta(hours=3))
    time_str = datetime.now(tz_moscow).strftime("[%H:%M:%S]")
    log_message = f"{time_str} Использована команда: \"{text_command}\" в чате {chat_peer} от @id{user_id}"
    db.add_system_log(log_message)
    params = {"random_id": random.getrandbits(31), "message": log_message, "peer_id": CONSOLE_CHAT_ID}
    try:
        vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка отправки в консоль: {e}")

def get_main_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_button('👤 Профиль', color=VkKeyboardColor.PRIMARY, payload={"cmd": "профиль"})
    kb.add_button('🕹 Mini-игры', color=VkKeyboardColor.PRIMARY, payload={"cmd": "мини-игры"})
    kb.add_line()
    kb.add_button('🛍 Магазин', color=VkKeyboardColor.PRIMARY, payload={"cmd": "магазин"})
    kb.add_button('💰 Баланс', color=VkKeyboardColor.PRIMARY, payload={"cmd": "баланс"})
    kb.add_line()
    kb.add_button('🎁 Бонус', color=VkKeyboardColor.NEGATIVE, payload={"cmd": "бонус"})
    kb.add_button('🛠 Тех. поддержка', color=VkKeyboardColor.NEGATIVE, payload={"cmd": "тех_поддержка"})
    kb.add_line()
    kb.add_button('Пополнить', color=VkKeyboardColor.NEGATIVE, payload={"cmd": "пополнить"})
    return kb.get_keyboard()

def get_support_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_openlink_button(label="Francesco Papa", link="https://vk.me/dimo4kaenergy")
    kb.add_line()
    kb.add_button('⬅ Назад', color=VkKeyboardColor.SECONDARY, payload={"cmd": "назад"})
    return kb.get_keyboard()

def get_games_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_button('💣 Сапер', color=VkKeyboardColor.PRIMARY, payload={"cmd": "сапер"})
    kb.add_button('🕵 Загадки', color=VkKeyboardColor.PRIMARY, payload={"cmd": "загадки"})
    kb.add_line()
    kb.add_button('🧮 Математика', color=VkKeyboardColor.PRIMARY, payload={"cmd": "математика"})
    kb.add_button('📱 Кликер', color=VkKeyboardColor.PRIMARY, payload={"cmd": "кликер"})
    kb.add_line()
    kb.add_button('⬅ Назад', color=VkKeyboardColor.SECONDARY, payload={"cmd": "назад"})
    return kb.get_keyboard()

def get_mines_keyboard(game_state):
    kb = VkKeyboard(inline=True)
    opened = game_state.get("opened", [])
    for i in range(1, 10):
        idx = i - 1
        if idx in opened:
            kb.add_button("💎", color=VkKeyboardColor.POSITIVE, payload={"cmd": f"box_{i}"})
        else:
            kb.add_button(f"📦 {i}", color=VkKeyboardColor.PRIMARY, payload={"cmd": f"box_{i}"})
        if i % 3 == 0:
            kb.add_line()
    if len(opened) > 0 and len(opened) < 3:
        kb.add_button("💰 Забрать куш", color=VkKeyboardColor.POSITIVE, payload={"cmd": "куш"})
    else:
        kb.add_button("⬅ Назад", color=VkKeyboardColor.SECONDARY, payload={"cmd": "назад"})
    return kb.get_keyboard()

def get_shop_carousel():
    elements = []
    for item in SHOP_ITEMS:
        elements.append({
            "title": item["title"],
            "description": f"Стоимость: {item['cost_str']}\n{item['desc']}",
            "buttons": [{"action": {"type": "text", "label": f"Получить {item['title']}", "payload": json.dumps({"cmd": f"buy_{item['id']}"})}}]
        })
    return {"type": "carousel", "elements": elements}

def get_manual_deposit_keyboard():
    kb = VkKeyboard(inline=True)
    kb.add_button(label="🔄 Я перевел!", color=VkKeyboardColor.POSITIVE, payload={"cmd": "transfer_done"})
    return kb.get_keyboard()

def get_owner_confirm_keyboard(don_id):
    kb = VkKeyboard(inline=True)
    kb.add_button(label="✅ Подтвердить", color=VkKeyboardColor.POSITIVE, payload=json.dumps({"confirm_don_id": don_id}))
    kb.add_button(label="❌ Отказать", color=VkKeyboardColor.NEGATIVE, payload=json.dumps({"reject_don_id": don_id}))
    return kb.get_keyboard()

def get_owner_withdraw_keyboard(w_id):
    kb = VkKeyboard(inline=True)
    kb.add_button(label="✅ Вывод выполнен", color=VkKeyboardColor.POSITIVE, payload=json.dumps({"w_id": w_id}))
    return kb.get_keyboard()

print("✅ Бот запущен и слушает сообщения...")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        message_obj = event.obj.message
        uid = message_obj['from_id']
        if uid <= 0:
            continue
        
        msg = message_obj['text'].strip()
        msg_lower = msg.lower()
        peer = message_obj['peer_id']
        payload = event.obj.message.get('payload')
        parts = msg.split()
        is_dm = (peer == uid)
        
        # Очистка от упоминаний
        msg = re.sub(r'\[club\d+\|[^\]]+\]\s*', '', msg).strip()
        msg = re.sub(r'@\w+\s*', '', msg).strip()
        msg_lower = msg.lower()
        parts = msg.split()

        # Разбор Payload
        if payload:
            try:
                p_obj = json.loads(payload) if isinstance(payload, str) else payload
                if "cmd" in p_obj:
                    cmd_val = p_obj["cmd"]
                    if cmd_val == "профиль": msg, msg_lower = "профиль", "профиль"
                    elif cmd_val == "мини-игры": msg, msg_lower = "мини-игры", "мини-игры"
                    elif cmd_val == "магазин": msg, msg_lower = "магазин", "магазин"
                    elif cmd_val == "баланс": msg, msg_lower = "баланс", "баланс"
                    elif cmd_val == "бонус": msg, msg_lower = "бонус", "бонус"
                    elif cmd_val == "пополнить": msg, msg_lower = "пополнить", "пополнить"
                    elif cmd_val == "сапер": msg, msg_lower = "сапер", "сапер"
                    elif cmd_val == "загадки": msg, msg_lower = "загадки", "загадки"
                    elif cmd_val == "математика": msg, msg_lower = "математика", "математика"
                    elif cmd_val == "кликер": msg, msg_lower = "кликер", "кликер"
                    elif cmd_val == "тех_поддержка": msg, msg_lower = "тех. поддержка", "тех. поддержка"
                    elif cmd_val == "назад": msg, msg_lower = "назад", "назад"
                    elif cmd_val == "куш": msg, msg_lower = "💰 забрать куш", "💰 забрать куш"
                    elif cmd_val == "transfer_done": msg, msg_lower = "🔄 я перевел!", "🔄 я перевел!"
                    elif cmd_val.startswith("box_"): msg, msg_lower = f"📦 {cmd_val.split('_')[-1]}", f"📦 {cmd_val.split('_')[-1]}"
                    elif cmd_val.startswith("buy_"):
                        item_id = int(cmd_val.split("_")[-1])
                        if item_id == 0:
                            msg, msg_lower = "получить снятие кд", "получить снятие кд"
                        elif item_id == 1:
                            msg, msg_lower = "получить множитель", "получить множитель"
                    parts = msg.split()
            except:
                pass

        user = db.get_user(uid)
        if not user:
            continue

        # Логирование команд
        triggers = ["баланс", "профиль", "клик", "кликер", "мины", "сапер", "математика", "загадки", "топ", "рефка", "магазин", "пополнить", "уб", "bal", "исключить", "вывод", "бонус", "+ник", "помощь", "📦 ", "//"]
        if any(msg_lower.startswith(t) for t in triggers) or msg_lower in ["🕹 mini-игры", "🛍 магазин", "💰 баланс", "🎁 бонус", "🛠 тех. поддержка", "старт", "начать", "привет"]:
            send_console_log(msg, uid, peer)

        # Проверка банов
        if user.get('is_perm_banned', 0):
            continue
        if user.get('ban_until', 0) > time.time():
            now = time.time()
            if uid not in ban_notified_users or (now - ban_notified_users[uid]) > 300:
                ban_notified_users[uid] = now
                seconds_left = int(user['ban_until'] - now)
                b_hours, b_minutes, b_seconds = seconds_left // 3600, (seconds_left % 3600) // 60, seconds_left % 60
                tz_mos = timezone(timedelta(hours=3))
                exact_date = datetime.fromtimestamp(user['ban_until'], tz=tz_mos).strftime('%d.%m.%Y %H:%M:%S')
                send_msg(peer, f"⚠️ Вы заблокированы в боте!\n📅 Разблокировка: {exact_date} МСК\n⏳ Осталось: {b_hours:02d}ч {b_minutes:02d}м {b_seconds:02d}с\nПричина: {user.get('ban_reason', 'Нарушение правил')}")
            continue

        # САПЁР — ход
        if msg_lower.startswith("📦 ") and len(msg_lower.split()) > 1:
            if not is_dm:
                send_msg(peer, "❌ Сапер доступен только в ЛС!", get_main_keyboard())
                continue
            game = active_mines_games.get(uid)
            if not game:
                continue
            try:
                cell = int(msg_lower.split()[-1])
            except:
                continue
            idx = cell - 1
            if idx in game["opened"]:
                continue
            
            if game["field"][idx] == 1:  # Бомба
                bomb_map = ""
                for i, v in enumerate(game["field"], 1):
                    if v == 1:
                        bomb_map += "💥 "
                    else:
                        bomb_map += "💎 "
                    if i % 3 == 0:
                        bomb_map += "\n"
                send_msg(peer, f"💥 **БУМ! В коробке {cell} была мина!** 💀\n\nКуш {num_to_str(game['current_bank'])} сгорел!\n🔍 Карта:\n{bomb_map}", get_games_keyboard())
                active_mines_games.pop(uid, None)
            else:
                game["opened"].append(idx)
                game["current_bank"] += 40_000_000_000
                if len(game["opened"]) == 3:
                    db.add_balance(uid, game["current_bank"])
                    send_msg(peer, f"🏆 **ПОБЕДА!** Ты открыл все 3 алмаза! +{num_to_str(game['current_bank'])} на баланс!", get_games_keyboard())
                    active_mines_games.pop(uid, None)
                else:
                    send_msg(peer, f"💎 Коробка {cell} безопасна!\n💰 Куш: {num_to_str(game['current_bank'])}", keyboard=get_mines_keyboard(game))
            continue

        # Проверка ответов викторин
        state = user_states.get(uid)
        if state and state.get("action") in ["waiting_riddle_answer", "waiting_math_answer"]:
            if msg_lower in ["загадки", "математика", "🕹 mini-игры", "мини-игры", "назад", "⬅ назад", "сапер", "💣 сапер", "кликер", "тех. поддержка"]:
                user_states.pop(uid, None)
            elif msg_lower in state["answers"]:
                user_states.pop(uid, None)
                db.add_balance(uid, state["reward"])
                send_msg(peer, f"🎉 Верно, {get_user_mention(uid)}! Награда +{num_to_str(state['reward'])} на баланс! 🧠", get_games_keyboard())
                continue
            else:
                correct_answer = state['answers'][0]
                user_states.pop(uid, None)
                send_msg(peer, f"❌ Неверно! Правильный ответ: «{correct_answer}». Повезет в другой раз!", get_games_keyboard())
                continue

        # ОСНОВНЫЕ КОМАНДЫ
        if msg_lower in ["начать", "старт", "привет"]:
            if len(parts) > 1:
                try:
                    ref_id = int(parts[-1])
                    if ref_id != uid and user.get('referrer_id', 0) == 0:
                        db.update_user_field(uid, 'referrer_id', ref_id)
                except:
                    pass
            send_msg(peer, f"👋 Привет, {get_user_mention(uid)}! Я игровой автокликер. Пользуйся кнопками меню:", get_main_keyboard())
            continue

        elif msg_lower in ["💰 баланс", "баланс"]:
            send_msg(peer, f"👀 Ваш баланс: {num_to_str(db.get_user(uid)['balance'])}", get_main_keyboard())
            continue

        elif msg_lower in ["🕹 mini-игры", "мини-игры"]:
            send_msg(peer, "🕹 Доступные mini-игры:\n\n💣 Сапер\n🕵 Загадки\n🧮 Математика\n📱 Кликер", get_games_keyboard())
            continue

        elif msg_lower in ["📱 кликер", "клик", "кликер"]:
            user = db.get_user(uid)
            now = time.time()
            required_cd = 0.05 if user.get('no_cd_until', 0) > now else 3.0
            if (now - user.get('last_click', 0)) < required_cd:
                continue
            db.update_user_field(uid, 'last_click', now)
            db.update_user_field(uid, 'clicks_count', user.get('clicks_count', 0) + 1)
            reward = 30_000_000_000 if user.get('x2_until', 0) > now else 15_000_000_000
            new_bal = db.add_balance(uid, reward)
            send_msg(peer, f"🎯 Клик! +{num_to_str(reward)}\n💰 Баланс: {num_to_str(new_bal)}", get_games_keyboard())
            continue

        elif msg_lower in ["💣 мины", "мины", "сапер", "💣 сапер"]:
            if not is_dm:
                send_msg(peer, "❌ Сапер доступен только в Личных Сообщениях!", get_games_keyboard())
                continue
            f = [1, 1, 1, 1, 1, 1, 0, 0, 0]  # 6 бомб, 3 алмаза
            random.shuffle(f)
            active_mines_games[uid] = {"field": f, "opened": [], "current_bank": 0}
            send_msg(peer, "💣 **САПЕР (3х3)**\nНа поле 6 бомб и 3 алмаза. Каждая чистая коробка: **+40 мк** в куш!", keyboard=get_mines_keyboard(active_mines_games[uid]))
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
            if not is_dm:
                send_msg(peer, "❌ Только в ЛС!", get_games_keyboard())
                continue
            r = random.choice(RIDDLES_POOL)
            user_states[uid] = {"action": "waiting_riddle_answer", "answers": r["a"], "reward": 40_000_000_000}
            send_msg(peer, f"🕵️‍♂️ **ЗАГАДКА (+40 мк)**\n\n{r['q']}\n⚠️ 1 попытка!")
            continue

        elif msg_lower in ["🎁 бонус", "бонус"]:
            user = db.get_user(uid)
            now = time.time()
            if now - user.get('last_daily', 0) < 86400:
                left = int(86400 - (now - user.get('last_daily', 0)))
                send_msg(peer, f"❌ Бонус уже получен! Приходите через {left//3600}ч {(left%3600)//60}м.", get_main_keyboard())
            else:
                bonus_reward = 300_000_000_000
                db.add_balance(uid, bonus_reward)
                db.update_user_field(uid, 'last_daily', now)
                send_msg(peer, f"🎁 Ежедневный бонус получен! +{num_to_str(bonus_reward)} на баланс.", get_main_keyboard())
            continue

        elif msg_lower in ["🛠 тех. поддержка", "тех. поддержка", "техподдержка"]:
            send_msg(peer, "Тех администратор отвечает в течении 12 часов! Чтобы с ним связаться нажмите на кнопку ниже,", get_support_keyboard())
            continue

        elif msg_lower.startswith("вывод") and len(parts) > 1:
            amount = str_to_num(parts[1:])
            if not amount or amount <= 0:
                send_msg(peer, "❌ Укажите корректную сумму для вывода.")
                continue
            if user['balance'] < amount:
                send_msg(peer, "❌ Недостаточно средств на балансе бота.")
                continue
            
            db.add_balance(uid, -amount)
            db.update_user_field(uid, 'total_withdrawn', user.get('total_withdrawn', 0) + amount)
            db.add_withdraw_log(uid, amount)
            
            w_id = f"with_{uid}_{int(time.time())}"
            pending_withdrawals[w_id] = {"uid": uid, "amount": amount, "peer_id": peer}
            
            send_msg(peer, f"С вашего баланса списана *{num_to_str(amount)}*. Заявка отправлена на обработку. Ожидайте зачисления!")
            send_msg(OWNER_VK_ID, f"🔔 **ЗАЯВКА НА ВЫВОД!**\n\nПользователь: {get_user_mention(uid)} (ID: {uid})\nСумма вывода: **{num_to_str(amount)}**\n\nПроверьте баланс и нажмите кнопку ниже, когда переведёте.", keyboard=get_owner_withdraw_keyboard(w_id))
            continue

        elif msg_lower.startswith("+ник ") and len(parts) > 1:
            new_name = " ".join(parts[1:]).strip()
            if len(new_name) > 15:
                send_msg(peer, "❌ Максимальная длина имени — 15 символов!")
                continue
            db.update_user_field(uid, 'nickname', new_name)
            USER_NAMES_CACHE[uid] = new_name
            send_msg(peer, f"✅ Вы успешно изменили имя профиля на: **{new_name}**!")
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
                name = r['nickname'] if r['nickname'] and r['nickname'] != 'Игрок' else f"Игрок {r['user_id']}"
                txt += f"{i}. [id{r['user_id']}|{name}] — {r['clicks_count']}
