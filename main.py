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

# Инициализируем базу данных из твоего модуля
db.init_db()

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
try:
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Накат необходимых колонок, если их нет
    for col, c_type in [
        ("x2_until", "INTEGER DEFAULT 0"), 
        ("reg_date", "TEXT DEFAULT ''"), 
        ("has_legendary", "INTEGER DEFAULT 0"),
        ("referrer_id", "INTEGER DEFAULT 0"), 
        ("ref_reward_given", "INTEGER DEFAULT 0")
    ]:
        try: cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {c_type}")
        except sqlite3.OperationalError: pass
    conn.commit()
    conn.close()
    print("⚠️ База данных успешно проверена и обновлена!")
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
    {"q": "Его не шьют, не кроят, а оно само на человеке растет. Что это?", "a": ["волосы", "волос"]},
    {"q": "В каком море нет воды?", "a": ["в сухом", "сухом", "на карте", "карта", "карт"]},
    {"q": "Один глаз, один рог, но не носорог. Кто это?", "a": ["корова из-за угла", "корова за углом", "корова"]},
    {"q": "Что всегда увеличивается и никогда не уменьшается в жизни человека?", "a": ["возраст", "года", "год"]},
    {"q": "Оно всегда перед нами, но мы не можем его увидеть. Что это?", "a": ["будущее"]},
    {"q": "У какого слона нет хобота?", "a": ["у шахматного", "шахматный", "шахматы"]},
    {"q": "Чем больше из нее берешь, тем больше она становится. Что это?", "a": ["яма"]},
    {"q": "Что может путешествовать по миру, оставаясь в одном и том же углу?", "a": ["почтовая марка", "марка"]},
    {"q": "Что разбивается, но никогда не падает, и что падает, но никогда не разбивается?", "a": ["сердце и давление", "сердце давление", "давление и сердце"]},
    {"q": "Что может говорить на всех языках мира без обучения?", "a": ["эхо"]}
]

SHOP_ITEMS = [
    {"id": 0, "title": "Снятие КД на кликер (12ч)", "cost_coins": 50_000_000_000_000, "cost_str": "50 мм", "desc": "Снижает задержку кликера до 50 мс на 12 часов."},
    {"id": 1, "title": "Множитель х2 клика (12ч)", "cost_coins": 100_000_000_000_000, "cost_str": "100 мм", "desc": "Удваивает награду за каждый клик (+30 мк) на 12 часов."}
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

def call_withdrawn_api(user_id, amount_coins): pass

def send_msg(chat_or_user_id, text, keyboard=None, template=None):
    params = {"random_id": random.getrandbits(31), "message": text, "peer_id": chat_or_user_id}
    if keyboard: params["keyboard"] = keyboard
    if template: params["template"] = json.dumps(template, ensure_ascii=False)
    try: vk.messages.send(**params)
    except Exception as e: print(f"Ошибка отправки сообщений: {e}")

def send_console_log(text):
    """Отправляет технические логи строго в CONSOLE_CHAT_ID (2000000003)"""
    if CONSOLE_CHAT_ID == 2000000003:
        params = {"random_id": random.getrandbits(31), "message": text, "peer_id": CONSOLE_CHAT_ID}
        try: vk.messages.send(**params)
        except Exception as e: print(f"Ошибка логирования консоли: {e}")

def get_main_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_button('👤 Профиль', color=VkKeyboardColor.PRIMARY)
    kb.add_button('💸 Вывод', color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button('🕹 Mini-игры', color=VkKeyboardColor.PRIMARY)
    kb.add_button('🛍 Магазин', color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button('💰 Баланс', color=VkKeyboardColor.POSITIVE)
    kb.add_button('🎁 Бонус', color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button('⏳ Услуги', color=VkKeyboardColor.SECONDARY)
    kb.add_button('🛠 Тех. поддержка', color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def get_games_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_button('📱 Кликер', color=VkKeyboardColor.PRIMARY)
    kb.add_button('💣 Мины', color=VkKeyboardColor.PRIMARY)
    kb.add_button('🕵‍♂ Загадки', color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button('⬅ Назад', color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()
def get_support_keyboard():
    kb = VkKeyboard(inline=True)
    kb.add_openlink_button(label="👤 Связаться с Тех. Админом", link="https://vk.me")
    return kb.get_keyboard()

def get_manual_deposit_keyboard():
    kb = VkKeyboard(inline=True)
    kb.add_button(label="🔄 Я перевел!", color=VkKeyboardColor.POSITIVE)
    return kb.get_keyboard()

def get_owner_confirm_keyboard(don_id):
    kb = VkKeyboard(inline=True)
    kb.add_button(label="✅ Подтвердить перевод", color=VkKeyboardColor.POSITIVE, payload=json.dumps({"don_id": don_id}))
    kb.add_button(label="❌ Отказать в переводе", color=VkKeyboardColor.NEGATIVE, payload=json.dumps({"don_id": don_id}))
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

def get_mines_keyboard():
    kb = VkKeyboard(inline=True)
    for i in range(1, 10):
        kb.add_button(f"📦 {i}", color=VkKeyboardColor.PRIMARY)
        if i % 3 == 0 and i < 9: kb.add_line()
    return kb.get_keyboard()

print("🚀 Бот 'Заработок | Бот нищий' запущен через VkBotLongPoll!")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        message_obj = event.obj.message
        uid = message_obj['from_id']
        if uid <= 0: continue
        
        msg = message_obj['text'].strip()
        msg_lower = msg.lower()
        peer = message_obj['peer_id']
        t_str_now = time.strftime("%H:%M:%S")
        is_dm = (peer == uid)
        payload = event.obj.message.get('payload')
        user = db.get_user(uid)
        if not user: continue

        # Начисление за реферала при самом первом входе
        if user.get('ref_reward_given', 0) == 0 and user.get('referrer_id', 0) > 0:
            ref_id = user['referrer_id']
            db.add_balance(ref_id, 1_000_000_000_000) # Начисляем 1 мм пригласившему
            db.update_user_field(uid, 'ref_reward_given', 1)
            send_msg(ref_id, f"🔗 По твоей реферальной ссылке зашел {get_user_mention(uid)}! Тебе начислено **1 мм**! 🎁")

        if uid == OWNER_VK_ID and user['moder_rank'] != 5:
            db.update_user_field(uid, 'moder_rank', 5)
            user = db.get_user(uid)

        if TEST_CHAT_ID and peer != TEST_CHAT_ID and peer != CONSOLE_CHAT_ID and peer != MODER_CHAT_ID:
            t_str_log = time.strftime("%H.%M.%S")
            send_msg(TEST_CHAT_ID, f"[{t_str_log}] {msg} от {get_user_mention(uid)}")

        if user['is_perm_banned']: continue
        if user['ban_until'] > time.time():
            now = time.time()
            if uid not in ban_notified_users or (now - ban_notified_users[uid]) > 300:
                ban_notified_users[uid] = now
                seconds_left = int(user['ban_until'] - now)
                hours, minutes, seconds = seconds_left // 3600, (seconds_left % 3600) // 60, seconds_left % 60
                send_msg(peer, f"⚠️ Вы заблокированы!\nРазблокировка через {hours:02d}:{minutes:02d}:{seconds:02d}\nПричина: {user['ban_reason']}")
            continue

        state = user_states.get(uid)
        if state and state.get("action") == "waiting_riddle_answer":
            if msg_lower in ["загадки", "🕹 mini-игры", "мини-игры", "назад", "⬅ назад", "💣 мины", "мины", "🕹 мини-игры"]:
                user_states.pop(uid, None)
            elif msg_lower in state["answers"]:
                user_states.pop(uid, None)
                db.add_balance(uid, 40_000_000_000)
                send_msg(peer, f"🎉 Верно, {get_user_mention(uid)}! Ответ угадан: +40 мк на баланс! 🧠", get_games_keyboard())
                continue
            else:
                user_states.pop(uid, None)
                send_msg(peer, f"❌ {get_user_mention(uid)}, ответ неверный! Правильный ответ был: «{', '.join(state['answers'])}». Повезет в другой раз! 🤫", get_games_keyboard())
                continue
        if msg_lower.startswith("📦 ") and len(msg_lower.split()) > 1:
            if not is_dm:
                send_msg(peer, f"❌ {get_user_mention(uid)}, игра Сапер доступна только в личке с ботом!", get_main_keyboard())
                continue
            game = active_mines_games.get(uid)
            if not game:
                send_msg(peer, "❌ У вас нет активной игры в мины! Напишите «мины» для старта.", get_games_keyboard())
                continue
            try: cell = int(msg_lower.split()[1])
            except: cell = 0
            if cell < 1 or cell > 9: continue

            field = game["field"]
            result = field[cell - 1]
            idx_60 = field.index("win_60") + 1 if "win_60" in field else "?"
            idx_40 = field.index("win_40") + 1 if "win_40" in field else "?"
            location_text = f"\n\n🔍 Карта поля: ячейка {idx_60} [60 мк], ячейка {idx_40} [40 мк], остальные [Бомбы 💥]"
            
            if result == "win_60":
                db.add_balance(uid, 60_000_000_000)
                send_msg(peer, f"💥 Ты открыл коробку {cell}!\n\n🎉 Результат: Ура, {get_user_mention(uid)}! Супер-приз **+60 мк** на баланс! 💰{location_text}", get_games_keyboard())
            elif result == "win_40":
                db.add_balance(uid, 40_000_000_000)
                send_msg(peer, f"💥 Ты открыл коробку {cell}!\n\n💎 Результат: Отлично, {get_user_mention(uid)}! Приз **+40 мк**! 💰{location_text}", get_games_keyboard())
            else:
                send_msg(peer, f"💥 Ты открыл коробку {cell}!\n\n💀 Результат: **БУМ!** {get_user_mention(uid)}, внутри мина!{location_text}", get_games_keyboard())
            active_mines_games.pop(uid, None)
            continue

        if is_contest_active and peer == TARGET_CHAT_ID and msg_lower == current_contest_word:
            is_contest_active = False
            current_contest_word = None
            db.add_balance(uid, 1_000_000_000_000)
            send_msg(TARGET_CHAT_ID, f"🎉 Поздравляем, {get_user_mention(uid)}! Ты оказался самым быстрым и забрал 1 мм на баланс! 💰")
            continue

        if peer == TARGET_CHAT_ID and time.time() >= next_contest_time:
            current_contest_word = random.choice(WORDS_POOL)
            is_contest_active = True
            next_contest_time = time.time() + 3600
            send_msg(TARGET_CHAT_ID, f"🎁 **ЕЖЕЧАСНЫЙ КОНКУРС!**\n\nПервый, кто напишет слово «{current_contest_word}» без кавычек, получит 1 мм на баланс!")
            continue

        parts = msg.split()
        if msg_lower in ["начать", "старт", "привет"]:
            if len(parts) > 1:
                try:
                    ref_id = int(parts[1])
                    if ref_id != uid and user.get('referrer_id', 0) == 0:
                        db.update_user_field(uid, 'referrer_id', ref_id)
                except: pass
            welcome_text = f"👋 Привет, {get_user_mention(uid)}!\n\n🤖 Я игровой бот-кликер. Кликай, отгадывай загадки и фарми валюту!\n\n👇 Навигация по кнопкам ниже:"
            send_msg(peer, welcome_text, get_main_keyboard())
            continue

        if msg_lower in ["💰 баланс", "баланс"]:
            fresh_user = db.get_user(uid)
            send_msg(peer, f"👀 Ваш баланс: {num_to_str(fresh_user['balance'])}", get_main_keyboard())
            continue

        elif msg_lower.startswith("пополнить") and user['moder_rank'] < 5:
            if len(parts) < 2:
                send_msg(peer, "💡 Подсказка: пополнить [сумма], например: пополнить 100 мм", get_main_keyboard())
                continue
            amount_str = " ".join(parts[1:])
            user_states[uid] = {"action": "waiting_deposit_click", "amount_str": amount_str, "peer_id": peer}
            send_msg(peer, f"Чтобы пополнить баланс на {amount_str}, вам нужно перевести эту сумму @dimo4kaenergy в @badbotik.", keyboard=get_manual_deposit_keyboard())
            continue

        elif msg_lower == "🔄 я перевел!":
            state = user_states.get(uid)
            if not state or state.get("action") != "waiting_deposit_click":
                send_msg(peer, "❌ Ошибка! Вы не вводили команду 'пополнить' перед подтверждением!", get_main_keyboard())
                continue
            amount_str = state.get("amount_str")
            don_id = f"don_{uid}_{int(time.time())}"
            pending_donations[don_id] = {"uid": uid, "amount_str": amount_str, "peer_id": state["peer_id"]}
            user_states.pop(uid, None)
            send_msg(OWNER_VK_ID, f"Ник {get_user_mention(uid)} утверждает, что перевел {amount_str}. Проверьте транзакцию.", keyboard=get_owner_confirm_keyboard(don_id))
            send_msg(peer, f"💸 Запрос на верификацию платежа {amount_str} отправлен Владельцу.", get_main_keyboard())
            continue
        elif msg_lower == "✅ подтвердить перевод" and uid == OWNER_VK_ID:
            don_id = None
            if payload:
                try: don_id = json.loads(payload).get("don_id")
                except: pass
            if not don_id: don_id = next((k for k in pending_donations.keys()), None)
            if not don_id or don_id not in pending_donations: 
                send_msg(OWNER_VK_ID, "❌ Активный запрос с данным ID не найден.")
                continue
            don_data = pending_donations[don_id]
            coins = str_to_num(don_data["amount_str"])
            if coins and coins > 0:
                db.add_balance(don_data["uid"], coins)
                send_msg(don_data["peer_id"], f"🎉 Баланс пополнен на {num_to_str(coins)}! Перевод подтвержден.", get_main_keyboard())
                send_msg(OWNER_VK_ID, "Успешно подтверждено!")
                send_console_log(f"💡 [{t_str_now}] 💸 Владелец подтвердил ручное пополнение на {don_data['amount_str']} для {get_user_mention(don_data['uid'])}")
            pending_donations.pop(don_id, None)
            continue

        elif msg_lower == "❌ отказать в переводе" and uid == OWNER_VK_ID:
            don_id = None
            if payload:
                try: don_id = json.loads(payload).get("don_id")
                except: pass
            if not don_id: don_id = next((k for k in pending_donations.keys()), None)
            if not don_id or don_id not in pending_donations:
                send_msg(OWNER_VK_ID, "❌ Запросы на отклонение отсутствуют.")
                continue
            don_data = pending_donations[don_id]
            send_msg(don_data["peer_id"], "❌ Разработчик отклонил ваш перевод денег.", get_main_keyboard())
            send_msg(OWNER_VK_ID, "Успешно отклонено!")
            send_console_log(f"⏰ [{t_str_now}] ⚠️ Владелец ОТКЛОНИЛ операцию пополнения для {get_user_mention(don_data['uid'])}")
            pending_donations.pop(don_id, None)
            continue

        elif msg_lower.startswith("вывод") or msg_lower.startswith("💸 вывод"):
            if len(parts) < 2:
                send_msg(peer, "💡 Подсказка: вывод [сумма]", get_main_keyboard())
                continue
            user = db.get_user(uid)
            amount = str_to_num(" ".join(parts[1:]))
            if amount and amount > 0 and user['balance'] >= amount:
                db.add_balance(uid, -amount)
                db.update_user_field(uid, 'total_withdrawn', user['total_withdrawn'] + amount)
                db.add_withdraw_log(uid, amount)
                call_withdrawn_api(uid, amount)
                send_msg(peer, f"✅ Вывод обработан! С вашего баланса списано {num_to_str(amount)}.", get_main_keyboard())
            else:
                send_msg(peer, "❌ Недостаточно средств на балансе или сумма указана неверно!", get_main_keyboard())
            continue
        elif msg_lower in ["🛍 магазин", "магазин"]:
            send_msg(peer, "🛍️ Магазин услуг! Листайте карусель под сообщением:", template=get_shop_carousel())
            continue

        elif msg_lower.startswith("получить снятие кд на кликер"):
            item = SHOP_ITEMS[0]
            user = db.get_user(uid)
            if user['balance'] < item["cost_coins"]: 
                send_msg(peer, "❌ У вас недостаточно средств!", get_main_keyboard())
                continue
            db.add_balance(uid, -item["cost_coins"])
            db.update_user_field(uid, 'no_cd_until', time.time() + 43200)
            send_msg(peer, "✅ Активировано! Снятие КД на кликер на 12 часов успешно запущено!", get_main_keyboard())
            continue

        elif msg_lower.startswith("получить множитель х2 кл"):
            item = SHOP_ITEMS[1]
            user = db.get_user(uid)
            if user['balance'] < item["cost_coins"]: 
                send_msg(peer, "❌ У вас недостаточно средств!", get_main_keyboard())
                continue
            db.add_balance(uid, -item["cost_coins"])
            db.update_user_field(uid, 'x2_until', time.time() + 43200)
            send_msg(peer, "✅ Списано успешно! Удвоение кликов на 12 часов активно!", get_main_keyboard())
            continue

        elif msg_lower in ["⏳ услуги", "услуги"]:
            now = time.time()
            no_cd_text = f"✅ До {time.strftime('%H:%M:%S', time.localtime(user['no_cd_until']))}" if user.get('no_cd_until', 0) > now else "❌ Пассивно"
            x2_text = f"✅ До {time.strftime('%H:%M:%S', time.localtime(user['x2_until']))}" if user.get('x2_until', 0) > now else "❌ Пассивно"
            send_msg(peer, f"⏳ **АКТИВНЫЕ УСЛУГИ АККАУНТА:**\n\n• Без КД клика (12ч): {no_cd_text}\n• Множитель х2 (12ч): {x2_text}", get_main_keyboard())
            continue

        elif msg_lower in ["рефка", "🔗 рефка", "рефералы"]:
            link = f"https://vk.me{GROUP_ID}?ref={uid}"
            send_msg(peer, f"🔗 **ВАША РЕФЕРАЛЬНАЯ ССЫЛКА:**\n\n{link}\n\n🎁 Поделись с другом! Если он запустит бота, ты получишь **1 мм**!", get_main_keyboard())
            continue

        elif msg_lower in ["топ кликов", "🏆 топ кликов", "топ клики"]:
            try:
                conn = sqlite3.connect('database.db')
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, clicks_count, nickname FROM users ORDER BY clicks_count DESC LIMIT 10")
                top_users = cursor.fetchall()
                conn.close()
                txt = "🏆 **ТАБЛИЦА ЛИДЕРОВ ПО КЛИКАМ:**\n\n"
                for i, row in enumerate(top_users, 1):
                    name = row['nickname'] if row['nickname'] else f"Игрок {row['user_id']}"
                    txt += f"{i}. [id{row['user_id']}|{name}] — {row['clicks_count']} кликов\n"
                send_msg(peer, txt, get_main_keyboard())
            except Exception as e:
                send_msg(peer, f"❌ Не удалось загрузить топ: {e}")
            continue
        elif msg_lower in ["🕹 mini-игры", "мини-игры"]:
            games_text = "🎲 **ДОСТУПНЫЕ МИНИ-ИГРЫ:**\n\n• Клик — добыча монет [Везде]\n• Загадки — викторина на скорость [ЛС]\n• Бонус — ежедневный подарок [Везде]\n• Сапер — поле 3х3 [ЛС]\n• Топ кликов — лучшие игроки."
            send_msg(peer, games_text, get_games_keyboard())
            continue

        elif msg_lower in ["⬅ назад", "назад"]:
            send_msg(peer, "⬅ Вы вернулись в главное меню:", get_main_keyboard())
            continue

        elif msg_lower in ["📱 кликер", "клик", "📱 клик"]:
            user = db.get_user(uid)  # Прямой пересчет макросов
            now = time.time()
            has_no_cd = user.get('no_cd_until', 0) > now
            required_cd = 0.05 if has_no_cd else 3.0
            if (now - user.get('last_click', 0)) < required_cd: continue
            
            db.update_user_field(uid, 'last_click', now)
            db.update_user_field(uid, 'clicks_count', user['clicks_count'] + 1)
            is_x2 = user.get('x2_until', 0) > now
            click_reward = 30_000_000_000 if is_x2 else 15_000_000_000
            new_bal = db.add_balance(uid, click_reward)
            send_msg(peer, f"🎯 Клик! +{num_to_str(click_reward)}\n💰 Баланс: {num_to_str(new_bal)}", get_games_keyboard())
            continue

        elif msg_lower in ["💣 мины", "мины", "сапер"]:
            if peer > 2000000000:
                send_msg(peer, "❌ Сапер доступен только в Личных Сообщениях бота!", get_games_keyboard())
                continue
            pool = ["win_60", "win_40", "bomb", "bomb", "bomb", "bomb", "bomb", "bomb", "bomb"]
            random.shuffle(pool)
            active_mines_games[uid] = {"uid": uid, "field": pool}
            send_msg(peer, "💣 **МИНЫ (САПЕР 3х3)**\n\nВыбери ячейку на кнопках:", keyboard=get_mines_keyboard())
            continue

        elif msg_lower in ["🕵 загадки", "загадки"]:
            if peer > 2000000000:
                send_msg(peer, "❌ Загадки доступны только в Личных Сообщениях!", get_games_keyboard())
                continue
            riddle = random.choice(RIDDLES_POOL)
            user_states[uid] = {"action": "waiting_riddle_answer", "answers": riddle["a"]}
            send_msg(peer, f"🕵️‍♂️ **ЗАГАДКА (+40 мк)**\n\n{riddle['q']}\n\n⚠️ Доступна ровно 1 попытка!")
            continue

        elif msg_lower in ["🎁 бонус", "бонус"]:
            user = db.get_user(uid)
            now = time.time()
            if (now - user.get('last_daily', 0)) < 86400: 
                send_msg(peer, "❌ Вы уже забирали бонус! Возвращайтесь через 24 часа.", get_main_keyboard())
                continue
            chance = random.randint(1, 100)
            win_amount = int(random.randint(300, 500) * 1_000_000_000) if chance <= 98 else int(random.randint(1_000, 5_000) * 1_000_000_000_000)
            db.update_user_field(uid, 'last_daily', now)
            db.add_balance(uid, win_amount)
            send_msg(peer, f"🎁 Твой ежедневный бонус: {num_to_str(win_amount)}", get_main_keyboard())
            continue

        elif msg_lower in ["🛠 тех. поддержка", "тех. поддержка", "поддержка", "техподдержка"]:
            send_msg(peer, "⚠️ Ответ Администратора поступает в течение 12 часов!", keyboard=get_support_keyboard())
            continue

        elif msg_lower.startswith("+ник "):
            new_nick = msg[5:].strip()[:20]
            db.update_user_field(uid, 'nickname', new_nick)
            send_msg(peer, f"✅ Ник изменен на: {new_nick}", get_main_keyboard())
            continue

        elif msg_lower.startswith("👤 профиль") or msg_lower in ["👤 профиль", "профиль", "проф"]:
            target_id = uid
            if len(parts) > 1 and parts[1].lower() not in ["я"]:
                parsed = parse_target(parts, 1, message_obj)
                if parsed: target_id = parsed
            t_user = db.get_user(target_id)
            if not t_user: continue
            ranks = {0: "Игрок", 1: "Модератор", 2: "Администратор", 3: "Гл. Администратор", 4: "Зам. Владельца", 5: "Владелец"}
            award = "♠️ THE LEGENDARY " if t_user.get('has_legendary', 0) == 1 else ""
            profile_card = f"🌎 Пользователь: {get_user_mention(target_id)}\n👹 Ранг: {award}{ranks.get(t_user['moder_rank'], 'Игрок')}\n🍻 Баланс: {num_to_str(t_user['balance'])}\n🏀 Кликов: {t_user.get('clicks_count', 0)}\n🧠 Выведено: {num_to_str(t_user.get('total_withdrawn', 0))}"
            send_msg(peer, profile_card, get_main_keyboard())
            continue

        elif msg_lower.startswith("выгнать") and user['moder_rank'] >= 1:
            if peer <= 2000000000 or peer not in ALLOWED_KICK_CHATS:
                send_msg(peer, "❌ Функция кика активна только в официальных беседах!", get_main_keyboard())
                continue
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                try:
                    vk.messages.removeChatUser(chat_id=peer - 2000000000, user_id=target_id)
                    send_msg(peer, f"✅ Игрок {get_user_mention(target_id)} исключен модератором.")
                except Exception as e: send_msg(peer, f"❌ Ошибка АПИ исключения: {e}")
            continue
        # ИЕРАРХИЧЕСКАЯ АДМИН-ПАНЕЛЬ С ФИКСАМИ ИНДЕКСОВ ПРИ РЕПЛАЯХ
        elif msg_lower.startswith("bal") and user['moder_rank'] >= 1:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages') and len(message_obj['fwd_messages']) > 0))
            if len(parts) < 2 and not is_reply:
                send_msg(peer, "💡 Подсказка: bal [ссылка/юз]")
                continue
            target_id = parse_target(parts, 1, message_obj)
            if target_id: 
                send_msg(peer, f"🍻 Игровой баланс {get_user_mention(target_id)}: {num_to_str(db.get_user(target_id)['balance'])}")
            continue

        elif msg_lower.startswith("//logs") and user['moder_rank'] >= 2:
            logs = db.get_last_logs(10)
            if not logs: send_msg(peer, "📋 Логи серверов чисты.")
            else:
                txt = "📋 **ПОСЛЕДНИЕ 10 ВЫВОДОВ ИЗ БД:**\n\n"
                for l in logs: txt += f"• Юзер: [id{l['user_id']}|Игрок] | Сумма: {num_to_str(l['amount'])}\n"
                send_msg(peer, txt)
            continue

        elif msg_lower.startswith("//giveaward") and user['moder_rank'] >= 2:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages') and len(message_obj['fwd_messages']) > 0))
            if len(parts) < 2 and not is_reply:
                send_msg(peer, "💡 Подсказка: //giveaward [ссылка/юз]")
                continue
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                db.update_user_field(target_id, 'has_legendary', 1)
                send_msg(peer, f"✅ Игроку {get_user_mention(target_id)} выдана плашка ♠️ THE LEGENDARY!")
            continue

        elif msg_lower.startswith("//ban") and user['moder_rank'] >= 3:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages') and len(message_obj['fwd_messages']) > 0))
            if len(parts) < 2 and not is_reply:
                send_msg(peer, "💡 Подсказка: //ban [дни / 0 разбан / -1 перм] [ссылка/юз] [причина]")
                continue
            try: days = int(parts[1])
            except:
                send_msg(peer, "❌ Количество дней банов вносится цифрой.")
                continue
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                start_reason_idx = 2 if is_reply else 3
                reason = " ".join(parts[start_reason_idx:]) if len(parts) > start_reason_idx else "Не указана"
                if days == 0:
                    db.update_user_field(target_id, 'ban_until', 0.0)
                    db.update_user_field(target_id, 'is_perm_banned', 0)
                    send_msg(peer, f"✅ Юзер {get_user_mention(target_id)} успешно разблокирован.")
                    send_console_log(f"🔓 [{t_str_now}] Гл.Админ {get_user_mention(uid)} разбанил {get_user_mention(target_id)}")
                elif days == -1:
                    db.update_user_field(target_id, 'is_perm_banned', 1)
                    db.update_user_field(target_id, 'ban_reason', reason)
                    send_msg(peer, f"💀 Игрок {get_user_mention(target_id)} ЗАБАНЕН НАВСЕГДА! Причина: {reason}")
                    send_console_log(f"🛑 [{t_str_now}] Гл.Админ {get_user_mention(uid)} выдал ПЕРМАЧ {get_user_mention(target_id)}. Причина: {reason}")
                else:
                    db.update_user_field(target_id, 'ban_until', time.time() + (days * 86400))
                    db.update_user_field(target_id, 'ban_reason', reason)
                    send_msg(peer, f"⚠️ Игрок {get_user_mention(target_id)} забанен на {days} дней. Причина: {reason}")
                    send_console_log(f"⏰ [{t_str_now}] Гл.Админ {get_user_mention(uid)} забанил {get_user_mention(target_id)} на {days} дн. Причина: {reason}")
            continue

        elif msg_lower.startswith("//moder") and user['moder_rank'] >= 3:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages') and len(message_obj['fwd_messages']) > 0))
            if len(parts) < 2 and not is_reply:
                send_msg(peer, "💡 Подсказка: //moder [ранг 0-5] [ссылка/юз]")
                continue
            try: rank = int(parts[1])
            except:
                send_msg(peer, "❌ Номер ранга должен быть числом от 0 до 5.")
                continue
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                if rank >= user['moder_rank'] and uid != OWNER_VK_ID:
                    send_msg(peer, "❌ Вы не можете выдать должность выше или равную вашей!")
                    continue
                db.update_user_field(target_id, 'moder_rank', max(0, rank))
                r_names = {0: "Игрок", 1: "Модератор", 2: "Администратор", 3: "Гл. Администратор", 4: "Зам. Владельца", 5: "Владелец"}
                send_msg(peer, f"✅ Должность {get_user_mention(target_id)} обновлена до: {r_names[max(0, rank)]}")
                send_console_log(f"💼 [{t_str_now}] Смена ранга: {get_user_mention(uid)} выдал уровень {rank} для {get_user_mention(target_id)}")
            continue
        elif msg_lower.startswith("//set0") and user['moder_rank'] >= 4:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages') and len(message_obj['fwd_messages']) > 0))
            if len(parts) < 2 or (not is_reply and len(parts) < 3):
                send_msg(peer, "💡 Подсказка: //set0 [nk/cl/bl/all] [ссылка/юз]")
                continue
            mode = parts[1].lower()
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                if mode in ["nk", "all"]: db.update_user_field(target_id, 'nickname', 'Игрок')
                if mode in ["cl", "all"]: db.update_user_field(target_id, 'clicks_count', 0)
                if mode in ["bl", "all"]: db.update_user_field(target_id, 'balance', 0)
                send_msg(peer, f"✅ Обнуление формата //set0 {mode} успешно выполнено для {get_user_mention(target_id)}.")
            continue

        elif msg_lower.startswith("уб") and user['moder_rank'] == 5:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages') and len(message_obj['fwd_messages']) > 0))
            target_id = parse_target(parts, 1, message_obj)
            amount_idx = 1 if is_reply else 2
            if target_id and len(parts) > amount_idx:
                amount = str_to_num(" ".join(parts[amount_idx:]))
                if amount and amount > 0:
                    db.add_balance(target_id, amount)
                    send_msg(peer, f"✅ Создатель начислил {num_to_str(amount)} на твой баланс {get_user_mention(target_id)}")
            continue

        elif msg_lower == "//chatid" and user['moder_rank'] == 5:
            send_msg(peer, f"⚙️ ID текущей беседы ВК: {peer}")
            continue

        elif msg_lower == "//update" and user['moder_rank'] == 5:
            send_msg(peer, "🔄 Скачиваю файлы обновлений из GitHub и перезапускаю ядро бота...")
            send_console_log(f"🔄 [{t_str_now}] Владелец {get_user_mention(uid)} выполнил команду //update")
            try:
                bash_cmd = "sleep 2 && git reset --hard HEAD && git pull && source venv/bin/activate && pip install -r requirements.txt --upgrade && pkill -9 -f main.py && nohup python3 main.py &"
                subprocess.Popen(["bash", "-c", bash_cmd])
                sys.exit()
            except Exception as e: send_msg(peer, f"❌ Критическая ошибка обновления: {e}")
            continue

        elif msg_lower == "//fix" and user['moder_rank'] == 5:
            send_msg(peer, "🛠 Запускаю сканер самодиагностики кода main.py...")
            try:
                file_path = "main.py"
                if not os.path.exists(file_path):
                    send_msg(peer, "❌ Ошибка: файл скрипта main.py отсутствует на хостинге!")
                    continue
                with open(file_path, "r", encoding="utf-8") as f: code = f.read()
                fixes = 0
                if "continueelif" in code:
                    code = code.replace("continueelif", "continue\n        elif")
                    fixes += 1
                if "return kb.get_keyboard()print" in code:
                    code = code.replace("return kb.get_keyboard()print", "return kb.get_keyboard()\n    print")
                    fixes += 1
                if fixes > 0:
                    with open(file_path, "w", encoding="utf-8") as f: f.write(code)
                    send_msg(peer, f"⚙️ Диагностика окончена. Найдено и устранено багов: {fixes}. Перезагружаюсь...")
                    send_console_log(f"🛠 [{t_str_now}] Система //fix исправила {fixes} синтаксических склеек.")
                    subprocess.Popen(["bash", "-c", "sleep 1 && pkill -9 -f main.py && source venv/bin/activate && nohup python3 main.py &"])
                    sys.exit()
                else:
                    try:
                        compile(code, file_path, 'exec')
                        send_msg(peer, "✅ Компилятор Python проверил код. Критических ошибок разметки, багов отступов и ловушек синтаксиса в main.py не обнаружено!")
                    except SyntaxError as se:
                        send_msg(peer, f"❌ Обнаружен синтаксический баг:\nСтрока {se.lineno}: {se.msg}\nИсправь его через GitHub репозиторий!")
            except Exception as e: send_msg(peer, f"❌ Система сканера повреждена: {e}")
            continue

        elif msg_lower in ["//help", "список команд"]:
            r = user['moder_rank']
            txt = "📋 **СПИСОК ВСЕХ КОМАНД БОТА:**\n- баланс\n- профиль\n- услуги\n- рефка\n- топ кликов"
            if r >= 1: txt += "\n\n⚠️ **РАНГ 1 — МОДЕРАТОР:**\n- bal [юз]\n- выгнать [ссылка/реплай]"
            if r >= 2: txt += "\n\n🍀 **РАНГ 2 — АДМИНИСТРАТОР:**\n- //logs\n- //giveaward [юз]"
            if r >= 3: txt += "\n\n👹 **РАНГ 3 — ГЛ. АДМИНИСТРАТОР:**\n- //ban [дни / 0 разбан] [юз]\n- //moder [0-5 ранг] [юз]"
            if r >= 4: txt += "\n\n🏆 **РАНГ 4 — ЗАМ. ВЛАДЕЛЬЦА:**\n- //set0 [nk/cl/bl/all] [юз]"
            if r == 5: txt += "\n\n🎱 **РАНГ 5 — ВЛАДЕЛЕЦ:**\n- уб [юз] [сумма]\n- //chatid\n- //update\n- //fix"
            send_msg(peer, txt, get_main_keyboard())
            continue
