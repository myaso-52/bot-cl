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

db.init_db()
print("⚠️ База данных успешно синхронизирована!")

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
    {"id": 0, "title": "Снятие КД на кликер (12ч)", "cost_coins": 50000000000000, "cost_str": "50 мм", "desc": "Убирает задержку кликера до 50мс."},
    {"id": 1, "title": "Множитель х2 клика (12ч)", "cost_coins": 100000000000000, "cost_str": "100 мм", "desc": "Удваивает награду за клик."}
]

def str_to_num(text):
    if isinstance(text, list):
        text = " ".join(text)
    text = text.replace(',', '.').strip().lower()
    multipliers = {'ммк': 1000000000000000, 'мм': 1000000000000, 'мк': 1000000000, 'кк': 1000000, 'к': 1000}
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
    if num >= 1000000000000000:
        return f"{round(num / 1000000000000000, 1)} ммк"
    if num >= 1000000000000:
        return f"{round(num / 1000000000000, 1)} мм"
    if num >= 1000000000:
        return f"{round(num / 1000000000, 1)} мк"
    if num >= 1000000:
        return f"{round(num / 1000000, 1)} кк"
    if num >= 1000:
        return f"{round(num / 1000, 1)} к"
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
        msg = re.sub(r'\[club\d+\|[^\]]+\]\s*', '', msg).strip()
        msg = re.sub(r'@\w+\s*', '', msg).strip()
        msg_lower = msg.lower()
        parts = msg.split()

        if payload:
            try:
                p_obj = json.loads(payload) if isinstance(payload, str) else payload
                if "cmd" in p_obj:
                    cmd_val = p_obj["cmd"]
                    cmd_map = {
                        "профиль": "профиль", "мини-игры": "мини-игры", "магазин": "магазин",
                        "баланс": "баланс", "бонус": "бонус", "пополнить": "пополнить",
                        "сапер": "сапер", "загадки": "загадки", "математика": "математика",
                        "кликер": "кликер", "тех_поддержка": "тех. поддержка", "назад": "назад",
                        "куш": "💰 забрать куш", "transfer_done": "🔄 я перевел!"
                    }
                    if cmd_val in cmd_map:
                        msg = cmd_map[cmd_val]
                        msg_lower = msg.lower()
                    elif cmd_val.startswith("box_"):
                        box_num = cmd_val.split('_')[-1]
                        msg = f"📦 {box_num}"
                        msg_lower = msg.lower()
                    elif cmd_val.startswith("buy_"):
                        item_id = int(cmd_val.split("_")[-1])
                        msg = "получить снятие кд" if item_id == 0 else "получить множитель"
                        msg_lower = msg.lower()
                    parts = msg.split()
            except:
                pass

        user = db.get_user(uid)
        if not user:
            continue

        triggers = ["баланс", "профиль", "клик", "кликер", "мины", "сапер", "математика", "загадки", "топ", "рефка", "магазин", "пополнить", "уб", "bal", "исключить", "вывод", "бонус", "+ник", "помощь", "📦 ", "//"]
        if any(msg_lower.startswith(t) for t in triggers) or msg_lower in ["🕹 mini-игры", "🛍 магазин", "💰 баланс", "🎁 бонус", "🛠 тех. поддержка", "старт", "начать", "привет"]:
            send_console_log(msg, uid, peer)

        if user.get('is_perm_banned', 0):
            continue
        if user.get('ban_until', 0) > time.time():
            now = time.time()
            if uid not in ban_notified_users or (now - ban_notified_users[uid]) > 300:
                ban_notified_users[uid] = now
                seconds_left = int(user['ban_until'] - now)
                b_hours = seconds_left // 3600
                b_minutes = (seconds_left % 3600) // 60
                b_seconds = seconds_left % 60
                tz_mos = timezone(timedelta(hours=3))
                exact_date = datetime.fromtimestamp(user['ban_until'], tz=tz_mos).strftime('%d.%m.%Y %H:%M:%S')
                send_msg(peer, f"⚠️ Вы заблокированы в боте!\n📅 Разблокировка: {exact_date} МСК\n⏳ Осталось: {b_hours:02d}ч {b_minutes:02d}м {b_seconds:02d}с\nПричина: {user.get('ban_reason', 'Нарушение правил')}")
            continue

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
            if game["field"][idx] == 1:
                bomb_map = ""
                for i, v in enumerate(game["field"], 1):
                    bomb_map += "💥 " if v == 1 else "💎 "
                    if i % 3 == 0:
                        bomb_map += "\n"
                send_msg(peer, f"💥 **БУМ! В коробке {cell} была мина!** 💀\n\nКуш {num_to_str(game['current_bank'])} сгорел!\n🔍 Карта:\n{bomb_map}", get_games_keyboard())
                active_mines_games.pop(uid, None)
            else:
                game["opened"].append(idx)
                game["current_bank"] += 40000000000
                if len(game["opened"]) == 3:
                    db.add_balance(uid, game["current_bank"])
                    send_msg(peer, f"🏆 **ПОБЕДА!** Ты открыл все 3 алмаза! +{num_to_str(game['current_bank'])} на баланс!", get_games_keyboard())
                    active_mines_games.pop(uid, None)
                else:
                    send_msg(peer, f"💎 Коробка {cell} безопасна!\n💰 Куш: {num_to_str(game['current_bank'])}", keyboard=get_mines_keyboard(game))
            continue

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
            reward = 30000000000 if user.get('x2_until', 0) > now else 15000000000
            new_bal = db.add_balance(uid, reward)
            send_msg(peer, f"🎯 Клик! +{num_to_str(reward)}\n💰 Баланс: {num_to_str(new_bal)}", get_games_keyboard())
            continue
        elif msg_lower in ["💣 мины", "мины", "сапер", "💣 сапер"]:
            if not is_dm:
                send_msg(peer, "❌ Сапер доступен только в Личных Сообщениях!", get_games_keyboard())
                continue
            f = [1, 1, 1, 1, 1, 1, 0, 0, 0]
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
            a = random.randint(10, 99)
            b = random.randint(10, 99)
            user_states[uid] = {"action": "waiting_math_answer", "answers": [str(a + b)], "reward": 25000000000}
            send_msg(peer, f"🧮 **МАТЕМАТИКА (+25 мк)**\n\nРеши пример: {a} + {b} = ?\n⚠️ У тебя 1 попытка!")
            continue
        elif msg_lower in ["🕵 загадки", "загадки"]:
            if not is_dm:
                send_msg(peer, "❌ Только в ЛС!", get_games_keyboard())
                continue
            r = random.choice(RIDDLES_POOL)
            user_states[uid] = {"action": "waiting_riddle_answer", "answers": r["a"], "reward": 40000000000}
            send_msg(peer, f"🕵️‍♂️ **ЗАГАДКА (+40 мк)**\n\n{r['q']}\n⚠️ 1 попытка!")
            continue
        elif msg_lower in ["🎁 бонус", "бонус"]:
            user = db.get_user(uid)
            now = time.time()
            if now - user.get('last_daily', 0) < 86400:
                left = int(86400 - (now - user.get('last_daily', 0)))
                send_msg(peer, f"❌ Бонус уже получен! Приходите через {left//3600}ч {(left%3600)//60}м.", get_main_keyboard())
            else:
                bonus_reward = 300000000000
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
                txt += f"{i}. [id{r['user_id']}|{name}] — {r['clicks_count']} кл.\n"
            send_msg(peer, txt, get_main_keyboard())
            continue
        elif msg_lower == "рефка":
            send_msg(peer, f"🔗 **РЕФЕРАЛЬНАЯ ССЫЛКА:**\n\nhttps://vk.me/{GROUP_ID}?ref={uid}\n\n🎁 За друга: **1 мм**!", get_main_keyboard())
            continue
        elif msg_lower in ["🛍 магазин", "магазин"]:
            send_msg(peer, "🛍️ Магазин услуг:", template=get_shop_carousel())
            continue
        elif msg_lower.startswith("получить снятие кд"):
            item = SHOP_ITEMS[0]
            user = db.get_user(uid)
            if user['balance'] < item["cost_coins"]:
                send_msg(peer, "❌ Недостаточно средств!", get_main_keyboard())
                continue
            db.add_balance(uid, -item["cost_coins"])
            db.update_user_field(uid, 'no_cd_until', time.time() + 43200)
            send_msg(peer, f"✅ Услуга '{item['title']}' успешно куплена на 12 часов!", get_main_keyboard())
            continue
        elif msg_lower.startswith("получить множитель"):
            item = SHOP_ITEMS[1]
            user = db.get_user(uid)
            if user['balance'] < item["cost_coins"]:
                send_msg(peer, "❌ Недостаточно средств!", get_main_keyboard())
                continue
            db.add_balance(uid, -item["cost_coins"])
            db.update_user_field(uid, 'x2_until', time.time() + 43200)
            send_msg(peer, f"✅ Услуга '{item['title']}' успешно куплена на 12 часов!", get_main_keyboard())
            continue
        elif msg_lower == "пополнить" or (msg_lower.startswith("пополнить ") and len(parts) > 1):
            amount_str = " ".join(parts[1:]) if len(parts) > 1 else "желаемую сумму"
            user_states[uid] = {"action": "waiting_deposit_click", "amount_str": amount_str, "peer_id": peer}
            send_msg(peer, f"Чтобы пополнить баланс в боте на *{amount_str}*, переведите эту сумму в Боте нищем юзеру @dimo4kaenergy и нажмите кнопку ниже.", keyboard=get_manual_deposit_keyboard())
            continue
        elif msg_lower == "🔄 я перевел!":
            state = user_states.get(uid)
            if state and state.get("action") == "waiting_deposit_click":
                don_id = f"don_{uid}_{int(time.time())}"
                pending_donations[don_id] = {"uid": uid, "amount_str": state["amount_str"], "peer_id": state["peer_id"]}
                user_states.pop(uid, None)
                send_msg(OWNER_VK_ID, f"Ник {get_user_mention(uid)} утверждает, что перевел вам {state['amount_str']}, проверьте.", keyboard=get_owner_confirm_keyboard(don_id))
                send_msg(peer, "💸 Запрос отправлен Владельцу на верификацию.", get_main_keyboard())
            continue
        elif msg_lower in ["⬅ назад", "назад"]:
            send_msg(peer, "🪐 Возвращаю в главное меню:", get_main_keyboard())
            continue
        elif msg_lower in ["помощь", "список команд", "//help"]:
            txt = "🎲 **КОМАНДЫ:**\n- баланс\n- кликер\n- мины (сапер)\n- математика\n- загадки\n- рефка\n- топ клик\n- магазин"
            if user['moder_rank'] >= 1:
                txt += "\n\n⚠️ **МОДЕРАТОР [1+]:**\n- bal [юз]\n- исключить [реплай]"
            if user['moder_rank'] >= 2:
                txt += "\n\n🍀 **АДМИНИСТРАТОР [2+]:**\n- //logs\n- //giveaward [юз]\n- //moderlist\n- //banlist"
            if user['moder_rank'] >= 3:
                txt += "\n\n👹 **ГЛ. АДМИНИСТРАТОР [3+]:**\n- //ban [дни] [юз]\n- //moder [ранг] [юз]"
            if user['moder_rank'] >= 4:
                txt += "\n\n🏆 **ЗАМ. ВЛАДЕЛЬЦА [4+]:**\n- //set0 [режим] [юз]\n- //moder [ранг] [юз]"
            if user['moder_rank'] == 5:
                txt += "\n\n🎱 **ВЛАДЕЛЕЦ:**\n- пополнить [юз] [сумма]\n- уб [юз] [сумма]\n- //chatid\n- //update\n- //fix\n- //clearfile"
            send_msg(peer, txt, get_main_keyboard())
            continue
        elif msg_lower.startswith("bal") and user['moder_rank'] >= 1:
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                send_msg(peer, f"🍻 Баланс {get_user_mention(target_id)}: {num_to_str(db.get_user(target_id)['balance'])}")
            continue
        elif msg_lower.startswith("исключить") and user['moder_rank'] >= 1:
            if peer <= 2000000000 or peer not in ALLOWED_KICK_CHATS:
                continue
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                try:
                    vk.messages.removeChatUser(chat_id=peer-2000000000, user_id=target_id)
                except:
                    pass
            continue
        elif msg_lower == "//logs" and user['moder_rank'] >= 2:
            logs = db.get_last_logs(10)
            if logs:
                txt = "📋 **ПОСЛЕДНИЕ 10 ВЫВОДОВ:**\n\n"
                for l in logs:
                    txt += f"• ID {l['user_id']} | {num_to_str(l['amount'])}\n"
            else:
                txt = "📋 Логи пусты."
            send_msg(peer, txt)
            continue
        elif msg_lower.startswith("//giveaward") and user['moder_rank'] >= 2:
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                db.update_user_field(target_id, 'has_legendary', 1)
                send_msg(peer, f"✅ Игроку {get_user_mention(target_id)} выдана плашка ♠️ THE LEGENDARY!")
            continue
        elif msg_lower == "//moderlist" and user['moder_rank'] >= 2:
            try:
                conn = sqlite3.connect('database.db')
                c = conn.cursor()
                c.execute("SELECT user_id, moder_rank FROM users WHERE moder_rank > 0 ORDER BY moder_rank DESC")
                mods = c.fetchall()
                conn.close()
                job_names = {1: "Модератор", 2: "Администратор", 3: "Гл. Администратор", 4: "Зам. Владельца", 5: "Владелец"}
                if mods:
                    txt = "📋 **СПИСОК МОДЕРАЦИИ БОТА:**\n\n"
                    for m in mods:
                        txt += f"• {get_user_mention(m[0])} — Должность: **{job_names.get(m[1], 'Игрок')}**\n"
                else:
                    txt = "📋 Модераторы отсутствуют."
                send_msg(peer, txt)
            except:
                pass
            continue
        elif msg_lower == "//banlist" and user['moder_rank'] >= 2:
            try:
                conn = sqlite3.connect('database.db')
                c = conn.cursor()
                c.execute("SELECT user_id, ban_reason FROM users WHERE is_perm_banned = 1 OR ban_until > ?", (time.time(),))
                bans = c.fetchall()
                conn.close()
                if bans:
                    txt = "📋 **СПИСОК ЗАБЛОКИРОВАННЫХ ИГРОКОВ:**\n\n"
                    for b in bans:
                        txt += f"• {get_user_mention(b[0])} | Причина: {b[1]}\n"
                else:
                    txt = "📋 Заблокированные пользователи отсутствуют."
                send_msg(peer, txt)
            except:
                pass
            continue
        elif msg_lower.startswith("//ban") and user['moder_rank'] >= 3:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            try:
                days = int(parts[1])
            except:
                continue
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                s_idx = 2 if is_reply else 3
                reason = " ".join(parts[s_idx:]) if len(parts) > s_idx else "Не указана"
                if days == 0:
                    db.update_user_field(target_id, 'ban_until', 0.0)
                    db.update_user_field(target_id, 'is_perm_banned', 0)
                    try:
                        vk.groups.unban(group_id=GROUP_ID, owner_id=target_id)
                    except:
                        pass
                    send_msg(peer, f"✅ Юзер {get_user_mention(target_id)} разблокирован в боте и в сообществе.")
                elif days == -1:
                    db.update_user_field(target_id, 'is_perm_banned', 1)
                    db.update_user_field(target_id, 'ban_reason', reason)
                    try:
                        vk.groups.ban(group_id=GROUP_ID, owner_id=target_id, comment=reason, comment_visible=1)
                    except:
                        pass
                    send_msg(peer, f"💀 {get_user_mention(target_id)} ЗАБАНЕН НАВСЕГДА в боте и заблокирован в сообществе! Причина: {reason}")
                else:
                    db.update_user_field(target_id, 'ban_until', time.time() + (days * 86400))
                    db.update_user_field(target_id, 'ban_reason', reason)
                    send_msg(peer, f"⚠️ Юзер {get_user_mention(target_id)} забанен на {days} дней. Причина: {reason}")
                send_console_log(f"🔨 Бан-логи: {get_user_mention(uid)} применил бан ({days} дн.) к ID {target_id}", uid, peer)
            continue
        elif msg_lower.startswith("//moder") and user['moder_rank'] >= 3:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            try:
                rank = int(parts[1])
            except:
                continue
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                max_allowed = user['moder_rank'] if user['moder_rank'] == 5 else user['moder_rank'] - 1
                if rank > max_allowed and uid != OWNER_VK_ID:
                    send_msg(peer, "❌ Вы не можете выдать этот ранг!")
                    continue
                final_rank = 0 if rank == -1 else max(0, rank)
                db.update_user_field(target_id, 'moder_rank', final_rank)
                send_msg(peer, f"✅ Уровень должности {get_user_mention(target_id)} изменен на {final_rank}")
                send_console_log(f"💼 Изменение ранга: {get_user_mention(uid)} выдал ранг {final_rank} для ID {target_id}", uid, peer)
            continue
        elif msg_lower.startswith("//set0") and user['moder_rank'] >= 4:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            if len(parts) < 2:
                continue
            mode = parts[1].lower()
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                if mode in ["nk", "all"]:
                    db.update_user_field(target_id, 'nickname', 'Игрок')
                if mode in ["cl", "all"]:
                    db.update_user_field(target_id, 'clicks_count', 0)
                if mode in ["bl", "all"]:
                    db.update_user_field(target_id, 'balance', 0)
                if mode in ["rg", "all"]:
                    db.update_user_field(target_id, 'reg_date', time.strftime("%d.%m.%Y"))
                if mode in ["vv", "all"]:
                    db.update_user_field(target_id, 'total_withdrawn', 0)
                send_msg(peer, f"✅ Операция //set0 {mode} выполнена для {get_user_mention(target_id)}.")
            continue
        elif (msg_lower.startswith("пополнить") or msg_lower.startswith("уб")) and user['moder_rank'] == 5:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            target_id = parse_target(parts, 1, message_obj)
            amt_idx = 1 if is_reply else 2
            if target_id and len(parts) > amt_idx:
                amount = str_to_num(" ".join(parts[amt_idx:]))
                if amount and amount > 0:
                    db.add_balance(target_id, amount)
                    if msg_lower.startswith("уб"):
                        send_msg(peer, f"Вы успешно выдали {num_to_str(amount)} {get_user_mention(target_id)} на баланс!")
                    else:
                        send_msg(peer, f"✅ На баланс {get_user_mention(target_id)} успешно выдано {num_to_str(amount)}")
            continue
        elif msg_lower == "//chatid" and user['moder_rank'] == 5:
            send_msg(peer, f"⚙️ ID текущей беседы ВК: {peer}")
            continue
        elif msg_lower == "//update" and user['moder_rank'] == 5:
            send_msg(peer, "🔄 Обновление файлов ядра из Git...")
            try:
                subprocess.Popen(["bash", "-c", "sleep 1 && git reset --hard HEAD && git pull https://github.com/myaso-52/bot-cl.git main && pkill -9 -f main.py && nohup python3 main.py > bot.log 2>&1 &"])
                sys.exit()
            except:
                pass
            continue
        elif msg_lower == "//fix" and user['moder_rank'] == 5:
            send_msg(peer, "🛠 Глобальная самодиагностика main.py...")
            try:
                with open("main.py", "r", encoding="utf-8") as f:
                    code = f.read()
                fixes = 0
                if "continueelif" in code:
                    code = code.replace("continueelif", "continue\n        elif")
                    fixes += 1
                if fixes > 0:
                    with open("main.py", "w", encoding="utf-8") as f:
                        f.write(code)
                    send_msg(peer, f"⚙️ Успешно исправлено багов: {fixes}. Перезапуск...")
                    subprocess.Popen(["bash", "-c", "sleep 1 && pkill -9 -f main.py && nohup python3 main.py > bot.log 2>&1 &"])
                    sys.exit()
                else:
                    compile(code, "main.py", "exec")
                    send_msg(peer, "✅ Ошибок синтаксиса, ловушек отступов и сбоев разметки не обнаружено!")
            except Exception as e:
                send_msg(peer, f"❌ Сканер поврежден: {e}")
            continue
        elif msg_lower == "//clearfile" and user['moder_rank'] == 5:
            with open(os.path.basename(sys.argv[0]), "w") as f:
                f.write("")
            sys.exit()
        elif msg_lower in ["профиль", "👤 профиль", "проф"]:
            ranks = {0: "Игрок", 1: "Модератор", 2: "Администратор", 3: "Гл. Администратор", 4: "Зам. Владельца", 5: "Владелец"}
            award = " ♠️ THE LEGENDARY" if user.get('has_legendary', 0) == 1 else ""
            name_val = user.get('nickname', 'Игрок')
            if name_val == 'Игрок':
                name_val = get_user_mention(uid)
            r_date = user.get('reg_date') if user.get('reg_date') else "24.07.2026"
            txt = (
                f"🌎 **Профиль пользователя**{award}\n"
                f"🍭 **Имя пользователя:** {name_val}\n"
                f"👹 **Ранг:** {ranks[user['moder_rank']]}\n"
                f"🍻 **Баланс:** {num_to_str(user['balance'])}\n"
                f"🏀 **Кликов в боте:** {user.get('clicks_count', 0)}\n"
                f"🧠 **Всего выведено:** {num_to_str(user.get('total_withdrawn', 0))}\n"
                f"💀 **Дата регистрации в боте:** {r_date}"
            )
            send_msg(peer, txt, get_main_keyboard())
            continue

    elif event.type == VkBotEventType.MESSAGE_EVENT:
        if event.obj['user_id'] != OWNER_VK_ID:
            try:
                vk.messages.sendMessageEventAnswer(
                    event_id=event.obj['event_id'],
                    user_id=event.obj['user_id'],
                    peer_id=event.obj['peer_id'],
                    event_data=json.dumps({"type": "show_snackbar", "text": "❌ Вы не являетесь Владельцем бота!"})
                )
            except:
                pass
            continue

        payload = event.obj.get('payload')
        if payload:
            if "confirm_don_id" in payload:
                don_id = payload["confirm_don_id"]
                don_data = pending_donations.get(don_id)
                try:
                    vk.messages.sendMessageEventAnswer(event_id=event.obj['event_id'], user_id=event.obj['user_id'], peer_id=event.obj['peer_id'])
                except:
                    pass
                if don_data:
                    coins = str_to_num(don_data["amount_str"])
                    if coins:
                        db.add_balance(don_data["uid"], coins)
                        send_msg(don_data["peer_id"], f"🎉 Баланс успешно пополнен на {num_to_str(coins)}!")
                        send_msg(event.obj['peer_id'], f"✅ Вы успешно подтвердили пополнение для {get_user_mention(don_data['uid'])} на сумму {don_data['amount_str']}.")
                        send_console_log(f"Донат: Владелец подтвердил пополнение на {don_data['amount_str']} для ID {don_data['uid']}", OWNER_VK_ID, event.obj['peer_id'])
                    pending_donations.pop(don_id, None)
            elif "reject_don_id" in payload:
                don_id = payload["reject_don_id"]
                don_data = pending_donations.get(don_id)
                try:
                    vk.messages.sendMessageEventAnswer(event_id=event.obj['event_id'], user_id=event.obj['user_id'], peer_id=event.obj['peer_id'])
                except:
                    pass
                if don_data:
                    send_msg(don_data["peer_id"], "❌ Владелец отклонил ваше пополнение.")
                    send_msg(event.obj['peer_id'], "❌ Запрос на пополнение успешно отклонен.")
                    send_console_log(f"Донат: Владелец отклонил пополнение для ID {don_data['uid']}", OWNER_VK_ID, event.obj['peer_id'])
                    pending_donations.pop(don_id, None)
            elif "w_id" in payload:
                w_id = payload["w_id"]
                w_data = pending_withdrawals.get(w_id)
                try:
                    vk.messages.sendMessageEventAnswer(event_id=event.obj['event_id'], user_id=event.obj['user_id'], peer_id=event.obj['peer_id'])
                except:
                    pass
                if w_data:
                    send_msg(w_data["peer_id"], f"✅ **Вывод выполнен!** Владелец успешно перевёл {num_to_str(w_data['amount'])} на ваш аккаунт Бот нищий. Приятной игры! 🎉")
                    send_msg(event.obj['peer_id'], f"✅ Статус заявки обновлен: коины для {get_user_mention(w_data['uid'])} успешно выплачены.")
                    send_console_log(f"Вывод: Владелец подтвердил выплату {num_to_str(w_data['amount'])} для ID {w_data['uid']}", OWNER_VK_ID, event.obj['peer_id'])
                    pending_withdrawals.pop(w_id, None)
