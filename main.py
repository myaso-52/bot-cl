import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import src.db as db
import src.badbotik as badbot
import sqlite3
import random
import time
import sys
import os
import subprocess
import json
import re
import threading
from datetime import datetime, timedelta, timezone

VK_TOKEN = "vk1.a.4NLW0LW3cobhYjBFzUQ1uvIF8Zn93a7G9W--YJ-URTkk9tf9Qt7TCXYFGv1pQ-o17M_1oRUhJMEV53edLMcBKwIB9F3JIRJl-Vi0YXAAT26pOvv3_XY5Yc6wj6PQmt8p2BVheWDb4GKoIsjBkTT9pyVWWTK3qv0LZwZJv7FOFqczW5BAc7X9Hub2eaYgeWt9txSLeBYlbB-MiTG47JBKkQ"
USER_TOKEN = "vk1.a.TTXs3rVY8MBoW-rwBBHVsr2HCIyQY01d3AlTB_WWhkRBuoTDSWE34s9DRDcc0d5g15y84rnMkgJq1j4FD_RWhMDOTK4e-euYHiz1d9ABg7WlYzUA4D3ajSepPSx6O0nvgiQ6J7KLh-r_8XB0NPJfbbzWuqnTZFPckYSSYIOSKXbmLCLp_G7IPgMfzPS8uwUOCBUU3bghNCV9uEL0WvyrhQ"

GROUP_ID = 240438650
TARGET_CHAT_ID = 2000000001
TEST_CHAT_ID = 2000000002
MODER_CHAT_ID = 2000000004
CONSOLE_CHAT_ID = 2000000003
OWNER_VK_ID = 864686414
DONATE_CHAT_ID = 2000000006
REPORT_CHAT_ID = 2000000007

ALLOWED_KICK_CHATS = [TARGET_CHAT_ID, TEST_CHAT_ID, CONSOLE_CHAT_ID, MODER_CHAT_ID]
ADD_CHATS = [TARGET_CHAT_ID, TEST_CHAT_ID, REPORT_CHAT_ID]

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

db.init_db()
# Загружаем TEST_MODE из БД
try:
    conn = sqlite3.connect('database.db')
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    row = conn.execute("SELECT value FROM settings WHERE key = 'test_mode'").fetchone()
    TEST_MODE = (row[0] == '1') if row else False
    conn.close()
except:
    TEST_MODE = False
print("⚠️ База данных успешно синхронизирована!")

ban_notified_users = {}
user_states = {}
pending_donations = {}
pending_withdrawals = {}
active_games = {}
active_reports = {}
lottery_tickets = {}  # {uid: количество билетов}
lottery_pool = 0  # общий банк

# Задания
active_tasks = {}  # {номер: {"type": тип, "target": цель, "reward": награда}}
try:
    conn = sqlite3.connect('database.db')
    for row in conn.execute("SELECT id, type, target, reward, reward_str FROM tasks_save"):
        desc = row[4] if row[4] and row[4] != 'custom' else f"Задание #{row[0]}"
        active_tasks[row[0]] = {"type": "custom", "desc": desc, "reward": row[3], "reward_str": row[4]}
        if row[0] >= task_next_id:
            task_next_id = row[0] + 1
    conn.close()
except:
    pass
task_progress = {}  # {uid: {номер: прогресс}}
task_next_id = 1
try:
    conn = sqlite3.connect('database.db')
    for row in conn.execute("SELECT id, type, target, reward, reward_str FROM tasks_save"):
        pass  # старый формат
        if row[0] >= task_next_id:
            task_next_id = row[0] + 1
    conn.close()
except:
    pass

# Промокоды
promo_codes = {}
try:
    conn = sqlite3.connect('database.db')
    for row in conn.execute("SELECT code, amount, activations, reward_str FROM promos_save"):
        promo_codes[row[0]] = {"amount": row[1], "activations": row[2], "used": [], "reward_str": row[3]}
        for u in conn.execute("SELECT user_id FROM promo_used_save WHERE code = ?", (row[0],)):
            promo_codes[row[0]]["used"].append(u[0])
    conn.close()
except:
    pass
cupons = {}  # {uid: количество_бесплатных_выводов}  # {код: {"amount": сумма, "activations": всего, "used": []}}
promo_elite_used = {}  # {uid: время последнего создания}

TASK_TYPES = {
    "реф": "Приведи друга (реферал)",
    "клик": "Кликер-марафон (клики)",
    "сапер": "Победи в сапёре",
    "кнб": "Победи в КНБ",
    "сейф": "Взломай сейф",
    "вордли": "Угадай слово в Вордли",
    "баланс": "Накопи на балансе",
    "вывод": "Выведи из бота",
    "вход": "Заходи ежедневно",
    "магазин": "Купи в магазине",
    "элит": "Купи ELITE подписку",
    "пополни": "Пополни баланс",
    "чат": "Напиши в чат сообщений"
}

WORDS_POOL = [
    "пирамида", "компьютер", "телефон", "автомобиль", "библиотека", "горизонт",
    "календарь", "магазин", "ресторан", "самолет", "университет", "фейерверк",
    "шоколад", "экскурсия", "ювелирный", "ящерица", "абрикос", "баскетбол",
    "витамин", "гитара", "дельфин", "ежевика", "живопись", "завтрак",
    "инструмент", "карандаш", "лабиринт", "мармелад", "носорог", "одуванчик",
    "папоротник", "робот", "саксофон", "телескоп", "ураган", "фламинго",
    "хризантема", "циркуль", "чемодан", "экватор", "юность", "абзац",
    "барабан", "вертолет", "галактика", "динозавр", "енот", "жираф"
]

WORDLE_WORDS = [
    "аванс", "автор", "агент", "арена", "багаж", "банан", "банка", "башня",
    "билет", "бокал", "буква", "букет", "вагон", "ветка", "вилка", "вирус",
    "волна", "вышка", "гараж", "гений", "герой", "голос", "горка", "гость",
    "груша", "дверь", "диван", "диета", "дождь", "доска", "драка", "жажда",
    "жених", "живот", "забор", "завод", "закат", "замок", "запах", "зебра",
    "земля", "золото", "игрок", "кабан", "канал", "книга", "ковер", "кость",
    "кофе", "крыло", "кулак", "лампа", "лента", "лимон", "линия", "лодка",
    "ложка", "луна", "масло", "место", "месяц", "метро", "мозг", "море",
    "мороз", "мост", "музей", "мышь", "мясо", "налог", "народ", "небо",
    "номер", "ночь", "обед", "огонь", "океан", "орел", "орех", "отец",
    "очки", "пакет", "палец", "парк", "паук", "песня", "песок", "петля",
    "печь", "пирог", "план", "победа", "поезд", "пожар", "помощь", "право",
    "птица", "пуля", "радио", "рана", "река", "роза", "роман", "рыба",
    "рынок", "салат", "сахар", "свет", "свеча", "семья", "сила", "скала",
    "слава", "снег", "собака", "совет", "соль", "спина", "спорт", "стена",
    "стиль", "стол", "стул", "танец", "театр", "текст", "тема", "тень",
    "товар", "точка", "трава", "труд", "удар", "ужин", "улица", "урок",
    "утро", "факт", "фара", "ферма", "финал", "фирма", "флаг", "флот",
    "форма", "фраза", "фрукт", "хвост", "хлеб", "цвет", "цель", "цена",
    "центр", "чай", "час", "чудо", "шанс", "школа", "штора", "шум",
    "экран", "ягода"
]

contest_secret = random.randint(1, 50)
contest_active = False
contest_winner_found = False

def start_contest():
    global contest_secret, contest_active, contest_winner_found
    print("DEBUG: Конкурс запущен!")
    contest_secret = random.randint(1, 50)
    contest_active = True
    contest_winner_found = False
    try:
        send_msg(TARGET_CHAT_ID, f"🎲 Конкурс «Угадай число»!\n\nЯ загадал число от 1 до 50.\nПриз: 1 мм!\nПиши число прямо в чат! Попытки не ограничены!")
    except:
        pass
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    delay = (next_hour - now).total_seconds()
    threading.Timer(delay, start_contest).start()



RIDDLES_POOL = [
    {"q": "Его не шьют, не кроят, а оно само на человеке растет. Что это?", "a": ["волосы", "волос"]},
    {"q": "В каком море нет воды?", "a": ["в сухом", "сухом", "на карте", "карта"]},
    {"q": "Один глаз, один рог, но не носорог. Кто это?", "a": ["корова из-за угла", "корова"]},
    {"q": "Что всегда увеличивается и никогда не уменьшается?", "a": ["возраст", "года", "год"]},
    {"q": "Висит груша — нельзя скушать. Что это?", "a": ["лампочка", "лампа"]},
    {"q": "Без окон, без дверей — полна горница людей. Что это?", "a": ["огурец"]},
    {"q": "Сидит дед, во сто шуб одет. Кто его раздевает, тот слёзы проливает. Что это?", "a": ["лук", "луковица"]},
    {"q": "Зимой и летом одним цветом. Что это?", "a": ["ёлка", "елка", "ель", "сосна"]},
    {"q": "Не лает, не кусает, а в дом не пускает. Что это?", "a": ["замок"]},
    {"q": "Течёт, течёт — не вытечет, бежит, бежит — не выбежит. Что это?", "a": ["река", "речка"]},
    {"q": "Стоит Антошка на одной ножке. Что это?", "a": ["гриб"]},
    {"q": "Кто ходит сидя?", "a": ["шахматист"]},
    {"q": "Какой конь не ест овса?", "a": ["шахматный", "шахматный конь"]},
    {"q": "Что можно приготовить, но нельзя съесть?", "a": ["уроки", "домашку", "домашнее задание"]},
    {"q": "Что становится мокрым, пока сушит?", "a": ["полотенце"]},
    {"q": "Что можно увидеть с закрытыми глазами?", "a": ["сон", "сновидение"]},
    {"q": "Чем больше из неё берёшь, тем больше она становится. Что это?", "a": ["яма"]},
    {"q": "Кто говорит на всех языках?", "a": ["эхо"]},
    {"q": "Что идёт вверх и вниз, но остаётся на месте?", "a": ["лестница", "ступеньки"]},
]

SHOP_ITEMS = [
    {"id": 0, "title": "Снятие КД кликера (24ч)", "cost_coins": 50000000000000, "cost_str": "50 мм", "desc": "Убирает задержку кликера на 24 часа."},
    {"id": 1, "title": "Множитель игр х2 (24ч)", "cost_coins": 50000000000000, "cost_str": "50 мм", "desc": "Все награды в мини-играх удваиваются на 24 часа!"},
    {"id": 2, "title": "Безлимит вывод (24ч)", "cost_coins": 25000000000000, "cost_str": "25 мм", "desc": "Снимает ограничение на вывод на 24 часа."},
    {"id": 3, "title": "🌟 ELITE подписка", "cost_coins": 5000000000000, "cost_str": "5 мм/день", "desc": "Премиум подписка. Команда: купэлит (дни)"},
    {"id": 4, "title": "👑 VIP пакет (24ч + 3дн ELITE)", "cost_coins": 130000000000000, "cost_str": "130 мм", "desc": "Снятие КД, х2 игры, безлимит вывод 24ч + ELITE 3дн + VIP"},
]

def str_to_num(text):
    if isinstance(text, list):
        text = " ".join(text)
    text = text.replace(',', '.').strip().lower()
    multipliers = {'ммм': 1000000000000000000, 'ммк': 1000000000000000, 'мм': 1000000000000, 'мк': 1000000000, 'кк': 1000000, 'к': 1000}
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

def balance_to_str(num):
    num = int(num)
    s = str(num)
    # Добавляем точки каждые 3 цифры
    result = ""
    for i, c in enumerate(reversed(s)):
        if i > 0 and i % 3 == 0:
            result = "." + result
        result = c + result
    return result

def num_to_str(num):
    num = int(num)
    if num >= 1000000000000000000:
        return f"{int(num / 1000000000000000000)}ммм"
    if num >= 1000000000000000:
        return f"{int(num / 1000000000000000)}ммк"
    if num >= 1000000000000:
        return f"{int(num / 1000000000000)}мм"
    if num >= 1000000000000:
        return f"{int(num / 1000000000000)}мм"
    if num >= 1000000000:
        return f"{int(num / 1000000000)}мк"
    if num >= 1000000:
        return f"{int(num / 1000000)}кк"
    if num >= 1000:
        return f"{int(num / 1000)}к"
    return str(num)

def parse_user_id(text):
    text = text.strip()
    if '://vk.com/' in text or '://vk.ru/' in text:
        text = text.split('/')[-1].strip()
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

def send_msg(chat_or_user_id, text, keyboard=None, template=None, reply_to=None):
    if chat_or_user_id > 2000000000:
        keyboard = None
    params = {"random_id": random.getrandbits(31), "message": text, "peer_id": chat_or_user_id}
    if reply_to:
        params["reply_to"] = reply_to
    elif chat_or_user_id == peer:
        params["reply_to"] = message_obj.get("id")
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
    time_str = datetime.now(tz_moscow).strftime("[%d.%m.%Y %H:%M:%S]")
    log_message = f"{time_str} | Команда: \"{text_command}\" | Чат: {chat_peer} | @id{user_id}"
    db.add_system_log(log_message)
    params = {"random_id": random.getrandbits(31), "message": log_message, "peer_id": CONSOLE_CHAT_ID}
    try:
        vk.messages.send(**params)
    except Exception as e:
        print(f"Ошибка отправки в консоль: {e}")

def get_main_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_button('Профиль', color=VkKeyboardColor.PRIMARY, payload={"cmd": "профиль"})
    kb.add_button('Мини-игры', color=VkKeyboardColor.PRIMARY, payload={"cmd": "мини-игры"})
    kb.add_button('Магазин', color=VkKeyboardColor.PRIMARY, payload={"cmd": "магазин"})
    kb.add_line()
    kb.add_button('Баланс', color=VkKeyboardColor.PRIMARY, payload={"cmd": "баланс"})
    kb.add_button('Бонус', color=VkKeyboardColor.NEGATIVE, payload={"cmd": "бонус"})
    kb.add_button('Пополнить', color=VkKeyboardColor.NEGATIVE, payload={"cmd": "пополнить"})
    kb.add_line()
    kb.add_button('Рефка', color=VkKeyboardColor.NEGATIVE, payload={"cmd": "рефка"})
    kb.add_button('Задания', color=VkKeyboardColor.POSITIVE, payload={"cmd": "задания"})
    kb.add_button('Помощь', color=VkKeyboardColor.POSITIVE, payload={"cmd": "помощь"})
    kb.add_line()
    kb.add_button('Поддержка', color=VkKeyboardColor.NEGATIVE, payload={"cmd": "тех_поддержка"})
    kb.add_button('Администрация', color=VkKeyboardColor.POSITIVE, payload={"cmd": "администрация"})
    kb.add_line()
    kb.add_button('💸 Вывод', color=VkKeyboardColor.NEGATIVE, payload={"cmd": "вывод"})
    return kb.get_keyboard()


def get_support_keyboard():
    kb = VkKeyboard(one_time=False)
    kb.add_openlink_button(label="Агент Сенгоку", link="https://vk.me/francescopapa")
    kb.add_line()
    kb.add_button('⬅ Назад', color=VkKeyboardColor.SECONDARY, payload={"cmd": "назад"})
    return kb.get_keyboard()

def get_games_keyboard(page=1):
    kb = VkKeyboard(one_time=False)
    if page == 1:
        kb.add_button('Сапер', color=VkKeyboardColor.POSITIVE, payload={"cmd": "сапер"})
        kb.add_button('Загадки', color=VkKeyboardColor.POSITIVE, payload={"cmd": "загадки"})
        kb.add_line()
        kb.add_button('Математика', color=VkKeyboardColor.POSITIVE, payload={"cmd": "математика"})
        kb.add_button('Кликер', color=VkKeyboardColor.POSITIVE, payload={"cmd": "кликер"})
        kb.add_line()
        kb.add_button('Назад', color=VkKeyboardColor.SECONDARY, payload={"cmd": "назад"})
        kb.add_button('Дальше', color=VkKeyboardColor.PRIMARY, payload={"cmd": "игры2"})
    elif page == 2:
        kb.add_button('Угадай число', color=VkKeyboardColor.POSITIVE, payload={"cmd": "угадай"})
        kb.add_button('Крестики-нолики', color=VkKeyboardColor.POSITIVE, payload={"cmd": "крестики"})
        kb.add_line()
        kb.add_button('КНБ', color=VkKeyboardColor.POSITIVE, payload={"cmd": "кнб"})
        kb.add_button('Вордли', color=VkKeyboardColor.POSITIVE, payload={"cmd": "вордли"})
        kb.add_line()
        kb.add_button('Назад', color=VkKeyboardColor.PRIMARY, payload={"cmd": "игры1"})
        kb.add_button('Дальше', color=VkKeyboardColor.PRIMARY, payload={"cmd": "игры3"})
    else:
        kb.add_button('Сейф', color=VkKeyboardColor.POSITIVE, payload={"cmd": "сейф"})
        kb.add_button('Бомба', color=VkKeyboardColor.NEGATIVE, payload={"cmd": "бомба"})
        kb.add_line()
        kb.add_button('Виселица', color=VkKeyboardColor.POSITIVE, payload={"cmd": "виселица"})
        kb.add_button('Миллионер', color=VkKeyboardColor.POSITIVE, payload={"cmd": "миллионер"})
        kb.add_line()
        kb.add_button('Назад', color=VkKeyboardColor.PRIMARY, payload={"cmd": "игры2"})
    return kb.get_keyboard()

def get_mines_keyboard(game_state):
    kb = VkKeyboard(one_time=False)
    opened = game_state.get("opened", [])
    for i in range(1, 10):
        idx = i - 1
        if idx in opened:
            kb.add_button("💎", color=VkKeyboardColor.POSITIVE, payload={"cmd": f"box_{i}"})
        else:
            kb.add_button(f"📦 {i}", color=VkKeyboardColor.PRIMARY, payload={"cmd": f"box_{i}"})
        if i % 3 == 0:
            kb.add_line()
    if len(opened) > 0 and len(opened) < (5 if game_state.get("elite") else 3):
        kb.add_button("💰 Забрать куш", color=VkKeyboardColor.POSITIVE, payload={"cmd": "куш"})
    else:
        kb.add_button("⬅ Назад", color=VkKeyboardColor.SECONDARY, payload={"cmd": "назад"})
    return kb.get_keyboard()


def get_xo_keyboard(board):
    kb = VkKeyboard(inline=True)
    for i in range(9):
        if board[i] == " ":
            kb.add_button("▫️", color=VkKeyboardColor.SECONDARY, payload={"cmd": f"xo_{i}"})
        elif board[i] == "X":
            kb.add_button("❌", color=VkKeyboardColor.NEGATIVE)
        else:
            kb.add_button("⭕", color=VkKeyboardColor.POSITIVE)
        if i % 3 == 2 and i < 8:
            kb.add_line()
    return kb.get_keyboard()

def get_knb_keyboard():
    kb = VkKeyboard(inline=True)
    kb.add_button("🪨 Камень", color=VkKeyboardColor.PRIMARY, payload={"cmd": "knb_камень"})
    kb.add_button("✂️ Ножницы", color=VkKeyboardColor.NEGATIVE, payload={"cmd": "knb_ножницы"})
    kb.add_button("📄 Бумага", color=VkKeyboardColor.POSITIVE, payload={"cmd": "knb_бумага"})
    return kb.get_keyboard()

def check_xo_win(board, player):
    wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a,b,c in wins:
        if board[a] == board[b] == board[c] == player:
            return True
    return False

def format_wordle_guess(secret, guess):
    result = ""
    if len(secret) != 5 or len(guess) != 5:
        return "⬛⬛⬛⬛⬛"
    for i in range(5):
        if guess[i] == secret[i]:
            result += "🟩"
        elif guess[i] in secret:
            result += "🟨"
        else:
            result += "⬛"
    return result

def get_shop_carousel():
    elements = []
    for item in SHOP_ITEMS:
        elements.append({
            "title": item["title"],
            "description": f"Стоимость: {item['cost_str']}\n{item['desc']}",
            "buttons": [{"action": {"type": "text", "label": f"Купить {item['title']}", "payload": json.dumps({"cmd": f"buy_{item['id']}"})}}]
        })
    return {"type": "carousel", "elements": elements}

def get_manual_deposit_keyboard():
    kb = VkKeyboard(inline=True)
    kb.add_button(label="🔄 Я перевел!", color=VkKeyboardColor.POSITIVE, payload={"cmd": "transfer_done"})
    return kb.get_keyboard()

def get_donate_chat_keyboard(uid, amount_str):
    kb = VkKeyboard(inline=True)
    kb.add_button(label=f"💰 уб @id{uid} {amount_str}", color=VkKeyboardColor.POSITIVE, payload=json.dumps({"donate_approve": f"{uid}_{amount_str}"}))
    kb.add_button(label="❌ Отклонить", color=VkKeyboardColor.NEGATIVE, payload=json.dumps({"donate_reject": str(uid)}))
    return kb.get_keyboard()

MILLIONER_QUESTIONS = [
    {"q": "Какая планета вращается в обратную сторону?", "a": ["Венера", "Марс", "Юпитер", "Сатурн"], "correct": 0},
    {"q": "Сколько сердец у осьминога?", "a": ["1", "2", "3", "4"], "correct": 2},
    {"q": "Какой элемент самый распространённый во Вселенной?", "a": ["Кислород", "Водород", "Гелий", "Углерод"], "correct": 1},
    {"q": "Сколько костей у взрослого человека?", "a": ["186", "206", "226", "256"], "correct": 1},
    {"q": "Какой океан самый глубокий?", "a": ["Атлантический", "Индийский", "Тихий", "Сев. Ледовитый"], "correct": 2},
    {"q": "Сколько % Земли покрыто водой?", "a": ["51%", "61%", "71%", "81%"], "correct": 2},
    {"q": "Сколько дней в году на Меркурии?", "a": ["88", "165", "225", "365"], "correct": 0},
    {"q": "Кто создал Python?", "a": ["Гейтс", "Джобс", "ван Россум", "Торвальдс"], "correct": 2},
    {"q": "Сколько клавиш у пианино?", "a": ["66", "76", "88", "96"], "correct": 2},
    {"q": "Самый калорийный фрукт?", "a": ["Банан", "Авокадо", "Яблоко", "Виноград"], "correct": 1},
    {"q": "Когда распался СССР?", "a": ["1989", "1990", "1991", "1992"], "correct": 2},
    {"q": "Сколько игроков в футболе?", "a": ["9", "10", "11", "12"], "correct": 2},
    {"q": "Самая длинная река в мире?", "a": ["Амазонка", "Нил", "Янцзы", "Миссисипи"], "correct": 1},
    {"q": "Сколько цветов в радуге?", "a": ["5", "6", "7", "8"], "correct": 2},
    {"q": "Кто написал 'Войну и мир'?", "a": ["Достоевский", "Толстой", "Пушкин", "Гоголь"], "correct": 1},
    {"q": "Какая страна самая большая?", "a": ["США", "Китай", "Россия", "Канада"], "correct": 2},
    {"q": "Сколько зубов у взрослого человека?", "a": ["28", "30", "32", "34"], "correct": 2},
    {"q": "Какой газ преобладает в воздухе?", "a": ["Кислород", "Азот", "Углекислый", "Водород"], "correct": 1},
    {"q": "Столица Австралии?", "a": ["Сидней", "Мельбурн", "Канберра", "Перт"], "correct": 2},
    {"q": "Сколько метров в километре?", "a": ["100", "500", "1000", "10000"], "correct": 2},
    {"q": "Кто изобрёл телефон?", "a": ["Эдисон", "Белл", "Тесла", "Маркони"], "correct": 1},
    {"q": "Самое быстрое животное?", "a": ["Гепард", "Сокол", "Антилопа", "Страус"], "correct": 1},
    {"q": "Сколько часов в сутках?", "a": ["12", "24", "36", "48"], "correct": 1},
    {"q": "Самая большая планета?", "a": ["Земля", "Марс", "Юпитер", "Сатурн"], "correct": 2},
    {"q": "Кто написал 'Мастера и Маргариту'?", "a": ["Толстой", "Булгаков", "Достоевский", "Чехов"], "correct": 1},
    {"q": "Сколько континентов?", "a": ["5", "6", "7", "8"], "correct": 2},
    {"q": "Столица Японии?", "a": ["Пекин", "Сеул", "Токио", "Бангкок"], "correct": 2},
    {"q": "Какой год високосный?", "a": ["2018", "2019", "2020", "2021"], "correct": 2},
    {"q": "Самое глубокое озеро?", "a": ["Байкал", "Титикака", "Виктория", "Онтарио"], "correct": 0},
    {"q": "Символ золота?", "a": ["Ag", "Au", "Fe", "Cu"], "correct": 1},
    {"q": "Столица Бразилии?", "a": ["Рио", "Бразилиа", "Сан-Паулу", "Сальвадор"], "correct": 1},
    {"q": "Самая маленькая страна?", "a": ["Монако", "Ватикан", "Сан-Марино", "Мальдивы"], "correct": 1},
    {"q": "Вес литра воды?", "a": ["0.5кг", "1кг", "1.5кг", "2кг"], "correct": 1},
    {"q": "Кто открыл Америку?", "a": ["Магеллан", "Колумб", "Кук", "Диаш"], "correct": 1},
    {"q": "Полос на флаге США?", "a": ["11", "12", "13", "14"], "correct": 2},
    {"q": "Костей в черепе?", "a": ["12", "18", "22", "29"], "correct": 2},
    {"q": "Самая высокая гора?", "a": ["Эверест", "К2", "Канченджанга", "Лхоцзе"], "correct": 0},
    {"q": "Автор Гарри Поттера?", "a": ["Толкин", "Роулинг", "Льюис", "Мартин"], "correct": 1},
    {"q": "Литров в галлоне?", "a": ["2.5", "3.0", "3.78", "4.5"], "correct": 2},
    {"q": "Кто создал интернет?", "a": ["Гейтс", "Бернерс-Ли", "Джобс", "Цукерберг"], "correct": 1},
    {"q": "Дней в неделе?", "a": ["5", "6", "7", "8"], "correct": 2},
]

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
                    if cmd_val.startswith("horse_"):
                        horse_name = cmd_val.replace("horse_", "")
                        game = active_games.get(uid)
                        if game and game.get("game") == "horses":
                            horses = game["horses"]
                            selected = next((h for h in horses if h["name"] == horse_name), None)
                            if not selected:
                                continue
                            db.add_balance(uid, -10000000000)
                            # Запускаем гонку
                            results = []
                            for h in horses:
                                score = sum(random.randint(1, 5) for _ in range(5))
                                results.append({"name": h["name"], "emoji": h["emoji"], "score": score, "koef": h["koef"]})
                            results.sort(key=lambda x: x["score"], reverse=True)
                            winner = results[0]
                            race_msg = "🏇 Скачки! Ставка: 10 мк\n\n"
                            for r in results:
                                race_msg += f"{r['emoji']} {r['name']}: {r['score']} очков\n"
                            if winner["name"] == horse_name:
                                win_amount = int(10000000000 * winner["koef"])
                                db.add_balance(uid, win_amount)
                                race_msg += f"\n🎉 {winner['emoji']} {winner['name']} победил!\nВыигрыш: +{num_to_str(win_amount)}"
                            else:
                                race_msg += f"\n😢 Твой {selected['emoji']} {selected['name']} проиграл.\nПобедил: {winner['emoji']} {winner['name']}"
                            send_msg(peer, race_msg, get_games_keyboard(3))
                            active_games.pop(uid, None)
                            continue
                    send_console_log(f"Кнопка: {p_obj['cmd']}", uid, peer)
            except:
                pass
        elif msg:
            if uid not in [864686414, 827888215]:
                send_console_log(msg, uid, peer)

        if payload:
            try:
                p_obj = json.loads(payload) if isinstance(payload, str) else payload
                if "cmd" in p_obj:
                    cmd_val = p_obj["cmd"]
                    if cmd_val.startswith("horse_"):
                        horse_name = cmd_val.replace("horse_", "")
                        game = active_games.get(uid)
                        if game and game.get("game") == "horses":
                            horses = game["horses"]
                            selected = next((h for h in horses if h["name"] == horse_name), None)
                            if not selected:
                                continue
                            db.add_balance(uid, -10000000000)
                            # Запускаем гонку
                            results = []
                            for h in horses:
                                score = sum(random.randint(1, 5) for _ in range(5))
                                results.append({"name": h["name"], "emoji": h["emoji"], "score": score, "koef": h["koef"]})
                            results.sort(key=lambda x: x["score"], reverse=True)
                            winner = results[0]
                            race_msg = "🏇 Скачки! Ставка: 10 мк\n\n"
                            for r in results:
                                race_msg += f"{r['emoji']} {r['name']}: {r['score']} очков\n"
                            if winner["name"] == horse_name:
                                win_amount = int(10000000000 * winner["koef"])
                                db.add_balance(uid, win_amount)
                                race_msg += f"\n🎉 {winner['emoji']} {winner['name']} победил!\nВыигрыш: +{num_to_str(win_amount)}"
                            else:
                                race_msg += f"\n😢 Твой {selected['emoji']} {selected['name']} проиграл.\nПобедил: {winner['emoji']} {winner['name']}"
                            send_msg(peer, race_msg, get_games_keyboard(3))
                            active_games.pop(uid, None)
                            continue
                    cmd_val = p_obj["cmd"]
                    cmd_map = {
                        "профиль": "профиль", "мини-игры": "мини-игры", "магазин": "магазин",
                        "баланс": "баланс", "бонус": "бонус", "пополнить": "пополнить",
                        "сапер": "сапер", "загадки": "загадки", "математика": "математика",
                        "кликер": "кликер", "тех_поддержка": "тех. поддержка", "назад": "назад",
                        "куш": "💰 забрать куш", "transfer_done": "🔄 я перевел!", "угадай": "угадай число",
                        "крестики": "крестики-нолики", "помощь": "помощь", "администрация": "администрация",
                        "вывод": "вывод",
                        "кнб": "кнб", "вордли": "вордли", "сейф": "сейф", "бомба": "бомба", "виселица": "виселица",
                        "миллионер": "миллионер", "рефка": "рефка",
                        "задания": "задания",
                        "топ_клик": "топ клик",
                        "топ_вывод": "топ вывода"
                    }
                    if cmd_val == "millioner_5050":
                        game = active_games.get(uid)
                        if game and game.get("game") == "millioner":
                            if user['balance'] < 100000000000:
                                continue
                            db.add_balance(uid, -100000000000)
                            q = game["question"]
                            c = q["correct"]
                            w = [i for i in range(4) if i != c]
                            random.shuffle(w)
                            s = sorted([c, w[0]])
                            kb = VkKeyboard(one_time=True)
                            for i in s:
                                kb.add_button(q["a"][i], color=VkKeyboardColor.PRIMARY, payload={"cmd": f"millioner_{i}"})
                                if i == s[0]: kb.add_line()
                            send_msg(peer, f"💡 50/50\n\n{q['q']}", keyboard=kb.get_keyboard())
                        continue
                    if cmd_val == "millioner_take":
                        game = active_games.get(uid)
                        if game and game.get("game") == "millioner":
                            reward = game.get("bank", 0)
                            fresh_user = db.get_user(uid)
                            if fresh_user.get('game_boost_until', 0) > time.time():
                                reward *= 2
                            db.add_balance(uid, reward)
                            send_msg(peer, f"💰 Выигрыш: +{num_to_str(reward)}", get_games_keyboard(3))
                            active_games.pop(uid, None)
                        continue
                    if cmd_val == "millioner_next":
                        game = active_games.get(uid)
                        if game and game.get("game") == "millioner":
                            q = random.choice(MILLIONER_QUESTIONS)
                            game["question"] = q
                            kb = VkKeyboard(one_time=True)
                            for i, ans in enumerate(q["a"]):
                                kb.add_button(ans, color=VkKeyboardColor.PRIMARY, payload={"cmd": f"millioner_{i}"})
                                if i == 1:
                                    kb.add_line()
                            kb.add_line()
                        kb.add_button("💡 50/50 (100мк)", color=VkKeyboardColor.NEGATIVE, payload={"cmd": "millioner_5050"})
                        send_msg(peer, f"💰 Банк: {num_to_str(game.get('bank', 0))}\n\n{q['q']}", keyboard=kb.get_keyboard())
                        continue
                    if cmd_val.startswith("millioner_"):
                        idx = int(cmd_val.split("_")[1])
                        game = active_games.get(uid)
                        if game and game.get("game") == "millioner":
                            q = game["question"]
                            if idx == q["correct"]:
                                game["bank"] = game.get("bank", 0) + 40000000000
                                kb = VkKeyboard(one_time=True)
                                kb.add_button("💰 Забрать " + num_to_str(game["bank"]), color=VkKeyboardColor.POSITIVE, payload={"cmd": "millioner_take"})
                                kb.add_button("▶️ Продолжить", color=VkKeyboardColor.PRIMARY, payload={"cmd": "millioner_next"})
                                send_msg(peer, f"🎉 Верно! Банк: {num_to_str(game['bank'])}", keyboard=kb.get_keyboard())
                            else:
                                send_msg(peer, f"❌ Неверно! Ответ: {q['a'][q['correct']]}\nПроигрыш!", get_games_keyboard(3))
                                active_games.pop(uid, None)
                        continue
                    
                    if cmd_val == "игры2":
                        send_msg(peer, "Мини-игры (стр. 2/3):", get_games_keyboard(2))
                        continue
                    if cmd_val == "игры3":
                        send_msg(peer, "Мини-игры (стр. 3/3):", get_games_keyboard(3))
                        continue
                    if cmd_val == "игры1":
                        send_msg(peer, "Мини-игры (стр. 1/3):", get_games_keyboard(1))
                        continue
                    if cmd_val in cmd_map:
                        msg = cmd_map[cmd_val]
                        msg_lower = msg.lower()
                    elif cmd_val.startswith("box_"):
                        box_num = cmd_val.split('_')[-1]
                        msg = f"📦 {box_num}"
                        msg_lower = msg.lower()
                    elif cmd_val.startswith("xo_"):
                        msg = f"xo_{cmd_val.split('_')[-1]}"
                        msg_lower = msg.lower()
                    elif cmd_val.startswith("knb_"):
                        msg = f"knb_{cmd_val.split('_')[-1]}"
                        msg_lower = msg.lower()
                    elif cmd_val.startswith("buy_"):
                        item_id = int(cmd_val.split("_")[-1])
                        if item_id == 0:
                            msg = "получить снятие кд"
                        elif item_id == 1:
                            msg = "получить множитель игр"
                        elif item_id == 2:
                            msg = "получить безлимит вывод"
                        elif item_id == 3:
                            msg = "купэлит"
                        elif item_id == 4:
                            msg = "купить вип"
                        msg_lower = msg.lower()
                    parts = msg.split()
            except:
                pass

        user = db.get_user(uid)
        if TEST_MODE and uid not in [864686414, 827888215]:
            send_msg(peer, "бот на тестировании и загрузке обновления")
            continue
        # Проверка закрытых команд
        try:
            conn = sqlite3.connect('database.db')
            closed = [row[0] for row in conn.execute("SELECT cmd FROM closed_cmds")]
            conn.close()
        except:
            closed = []
        found_closed = False
        for cc in closed:
            if msg_lower == cc.lower() or msg_lower.startswith(cc.lower()):
                send_msg(peer, "команда была временно отключена разработчиком по тех причинам")
                found_closed = True
                break
        if found_closed:
            continue
        if user:
            # Сохраняем имя из ВК при каждом сообщении если ник "Игрок"
            if user.get('nickname') == 'Игрок' or not user.get('nickname'):
                try:
                    name_from_msg = f"{message_obj.get('first_name', '')} {message_obj.get('last_name', '')}"
                    if name_from_msg.strip():
                        db.update_user_field(uid, 'nickname', name_from_msg)
                        user['nickname'] = name_from_msg
                        USER_NAMES_CACHE[uid] = name_from_msg
                except:
                    pass
            try:
                vk_user = vk.users.get(user_ids=uid)
                name = f"{vk_user[0]['first_name']} {vk_user[0]['last_name']}"
                db.update_user_field(uid, 'nickname', name)
                user['nickname'] = name
                USER_NAMES_CACHE[uid] = name
            except:
                pass
        if not user:
            continue
        # Счётчик сообщений для задания "чат"
        if uid not in task_progress:
            task_progress[uid] = {}
        task_progress[uid]["chat_msgs"] = task_progress[uid].get("chat_msgs", 0) + 1
        for num, task in list(active_tasks.items()):
            if task['type'] == 'чат':
                msgs = task_progress[uid].get("chat_msgs", 0)
                if task_progress[uid].get(num, 0) != msgs:
                    task_progress[uid][num] = msgs
                if msgs >= task['target'] and num in active_tasks:
                    db.add_balance(uid, task['reward'])
                    new_bal = db.get_user(uid)["balance"]
                    send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                    del active_tasks[num]
        # Проверка заданий - обновление прогресса
        # Прогресс удалён

        # Проверка подписки на сообщество
        try:
            member = vk.groups.isMember(group_id=GROUP_ID, user_id=uid)
            if not member:
                send_msg(peer, "❌ Чтобы играть, подпишись на сообщество @badbotikzarabotok!", get_main_keyboard())
                continue
        except:
            pass
        
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

        if peer == TARGET_CHAT_ID:
            cg = active_games.get(0)
            if cg and cg.get("game") in ["chgame_num", "chgame_word"]:
                if cg["game"] == "chgame_num":
                    try:
                        g = int(msg)
                        if g == cg["secret"]:
                            db.add_balance(uid, cg["reward"])
                            send_msg(peer, f"🎉 {get_user_mention(uid)} угадал {cg['secret']}!\n+{cg['reward_str']}")
                            active_games.pop(0, None)
                    except:
                        pass
                pass

        if message_obj.get('reply_message') and peer == REPORT_CHAT_ID:
            reply_text = msg
            for rep_id, rep_data in list(active_reports.items()):
                if rep_data.get("taken_by") == uid or uid == OWNER_VK_ID:
                    send_msg(rep_data["uid"], f"📝 Ответ по репорту:\n\n{reply_text}")
                    send_msg(REPORT_CHAT_ID, f"✅ Ответ отправлен заявителю {get_user_mention(rep_data['uid'])}")
                    break

        if active_games.get(uid, {}).get("game") == "bomb":
            if not is_dm:
                continue
            game = active_games[uid]
            guess = msg.strip()
            if not guess.isdigit():
                send_msg(peer, "❌ Введи число!")
                continue
            if game.get("length") and len(guess) != game.get("length"):
                send_msg(peer, f"❌ Нужно {game.get('length', '?')}-значное число!")
                continue
            now = time.time()
            elite_bonus = 10 if user.get('elite_until', 0) > now else 0
            deadline = game.get("deadline", time.time()) + elite_bonus
            if now > deadline:
                send_msg(peer, f"💥 БУМ! Время вышло! Число-пример: {game['secret']}", get_games_keyboard(3))
                active_games.pop(uid, None)
                continue
            # Проверка: первая цифра
            if "first_digit" not in game or guess[0] != str(game["first_digit"]):
                left = int(deadline - now)
                send_msg(peer, f"❌ Первая цифра должна быть {game['first_digit']}!\n⏳ Осталось {left} сек.")
                continue
            # Проверка: сумма цифр
            guess_sum = sum(int(d) for d in guess)
            if "digit_sum" not in game or guess_sum != game.get("digit_sum", 0):
                left = int(deadline - now)
                if guess_sum > game.get("digit_sum", 0):
                    send_msg(peer, f"❌ Сумма {guess_sum} > {game.get('digit_sum', 0)}. Бери цифры меньше!\n⏳ Осталось {left} сек.")
                else:
                    send_msg(peer, f"❌ Сумма {guess_sum} < {game.get('digit_sum', 0)}. Бери цифры больше!\n⏳ Осталось {left} сек.")
                continue
            # Проверка: повторы не больше 2
            from collections import Counter
            counts = Counter(guess)
            if max(counts.values()) > 2:
                left = int(deadline - now)
                send_msg(peer, f"❌ Цифра повторяется больше 2 раз!\n⏳ Осталось {left} сек.")
                continue
            # Подсказка после 3 попыток
            game["attempts"] = game.get("attempts", 0) + 1
            if game["attempts"] == 3:
                last_digit = game["secret"][-1]
                hint_text = "чётная" if int(last_digit) % 2 == 0 else "нечётная"
                game["reward_penalty"] = 10000000000
                send_msg(peer, f"💡 Подсказка: последняя цифра {hint_text}.\n⚠️ Награда уменьшена на 10 мк.")
                continue
            # Всё верно!
            reward = 100000000000 - game.get("reward_penalty", 0)
            if user.get('game_boost_until', 0) > now:
                reward *= 2
            db.add_balance(uid, reward)
            send_msg(peer, f"🔧 Бомба обезврежена!\nТвой код: {guess} (сумма: {guess_sum})\n🎉 +{num_to_str(reward)} на баланс!", get_games_keyboard(3))
            active_games.pop(uid, None)
            continue

        if active_games.get(uid, {}).get("game") == "hangman":
            if not is_dm:
                continue
            game = active_games[uid]
            guess = msg_lower.strip().lower()
            game["attempts"] += 1
            if guess == game["word"]:
                reward = game["reward"]
                if user.get('game_boost_until', 0) > time.time():
                    reward *= 2
                db.add_balance(uid, reward)
                send_msg(peer, f"🎉 Верно! Слово: {game['word']}\n+{num_to_str(reward)} на баланс!", get_games_keyboard(3))
                active_games.pop(uid, None)
            else:
                send_msg(peer, f"❌ Неверно! Слово было: {game['word']}", get_games_keyboard(3))
                active_games.pop(uid, None)
            continue

        if active_games.get(uid, {}).get("game") == "safe":
            if not is_dm:
                continue
            game = active_games[uid]
            guess = msg.strip()
            if len(guess) != 4 or not guess.isdigit():
                send_msg(peer, "❌ Введи 4 цифры!")
                continue
            secret = game["secret"]
            game["attempts"] += 1
            attempts = game["attempts"]
            
            if guess == secret:
                reward = 70000000000
                if user.get('game_boost_until', 0) > time.time():
                    reward *= 2
                db.add_balance(uid, reward)
                if uid not in task_progress:
                    task_progress[uid] = {}
                    task_progress[uid]["safe_wins"] = task_progress[uid].get("safe_wins", 0) + 1
                send_msg(peer, f"🔓 СЕЙФ ВЗЛОМАН! Код: {secret}\n🎉 Ты угадал за {attempts} попыток!\n+{num_to_str(reward)} на баланс!", get_games_keyboard(1))
                active_games.pop(uid, None)
                continue
            
            if attempts >= 7:
                if user.get('elite_until', 0) > time.time():
                    send_msg(peer, f"🛡 ELITE защита! ❌ Попытки кончились! Код был: {secret}", get_games_keyboard(1))
                else:
                    db.add_balance(uid, -20000000000)
                    send_msg(peer, f"😢 Попытки кончились! Код был: {secret} (-20мк)", get_games_keyboard(1))
                active_games.pop(uid, None)
                continue
            
            # Показываем угаданные цифры на своих местах
            hint = ""
            for i in range(4):
                if guess[i] == secret[i]:
                    hint += guess[i]
                else:
                    hint += "_"
            
            send_msg(peer, f"🔐 Попытка {attempts}/7\n{hint[0]} {hint[1]} {hint[2]} {hint[3]}")
            continue
        if active_games.get(uid, {}).get("game") == "wordle":
            if not is_dm:
                continue
            game = active_games[uid]
            guess = msg_lower.strip()
            if len(guess) != 5 or not guess.isalpha():
                send_msg(peer, "❌ Введи слово из 5 русских букв!")
                continue
            secret = game["secret"]
            game["attempts"] += 1
            attempts = game["attempts"]
            squares = format_wordle_guess(secret, guess)
            guess_upper = guess.upper()
            
            if guess == secret:
                if attempts == 1:
                    reward = 150000000000
                elif attempts <= 4:
                    reward = 60000000000
                else:
                    reward = 35000000000
                if user.get('game_boost_until', 0) > time.time():
                    reward *= 2
                db.add_balance(uid, reward)
                if uid not in task_progress:
                    task_progress[uid] = {}
                    task_progress[uid]["wordle_wins"] = task_progress[uid].get("wordle_wins", 0) + 1
                send_msg(peer, f"🟩 Вордли\n\n{guess_upper}\n{squares}\n\n🎉 Ты угадал за {attempts} попыток!\n+{num_to_str(reward)} на баланс!", get_games_keyboard(1))
                active_games.pop(uid, None)
                continue
            
            if attempts >= 6:
                send_msg(peer, f"🟩 Вордли\n\n{guess_upper}\n{squares}\n\n❌ Попытки кончились! Слово было: {secret.upper()}", get_games_keyboard(1))
                active_games.pop(uid, None)
                continue
            
            history = game.get("history", "")
            history += f"{guess_upper}\n{squares}\n\n"
            game["history"] = history
            send_msg(peer, f"🟩 Вордли (попытка {attempts}/6)\n\n{history}⬜ — буквы нет\n🟨 — буква есть, но не на месте\n🟩 — буква на месте")
            continue

        if msg_lower.startswith("📦 ") and len(msg_lower.split()) > 1:
            if not is_dm:
                send_msg(peer, "❌ Сапер доступен только в ЛС!", get_main_keyboard())
                continue
            game = active_games.get(uid)
            if not game or game.get("game") != "mines":
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
                send_msg(peer, f"💥 БУМ! В коробке {cell} была мина! 💀\n\nКуш {num_to_str(game['current_bank'])} сгорел!\n🔍 Карта:\n{bomb_map}", get_games_keyboard(1))
                active_games.pop(uid, None)
            else:
                game["opened"].append(idx)
                game["current_bank"] += 40000000000
                max_diamonds = 6 if game.get("elite") else 3
                if len(game["opened"]) == max_diamonds:
                    win_reward = game["current_bank"]
                    if user.get('game_boost_until', 0) > time.time():
                        win_reward *= 2
                    db.add_balance(uid, win_reward)
                    if "mines_wins" not in task_progress.get(uid, {}):
                        if uid not in task_progress:
                            task_progress[uid] = {}
                    task_progress[uid]["mines_wins"] = task_progress[uid].get("mines_wins", 0) + 1
                    mines_msg = f"🏆 ПОБЕДА! +{num_to_str(win_reward)} на баланс!"
                    if uid in task_progress:
                        for num, task in list(active_tasks.items()):
                            if task['type'] == 'сапер':
                                wins = task_progress[uid].get("mines_wins", 0)
                                pct = int(wins / task['target'] * 100) if task['target'] > 0 else 0
                                filled = min(5, int(pct / 20))
                                done = "🟢" * filled + "⚪" * (5 - filled)
                                mines_msg += f"\n📋 Задание #{num}: {done} {wins}/{task['target']}"
                    send_msg(peer, mines_msg, get_games_keyboard(1))
                    active_games.pop(uid, None)
                else:
                    send_msg(peer, f"💎 Коробка {cell} безопасна!\n💰 Куш: {num_to_str(game['current_bank'])}", keyboard=get_mines_keyboard(game))
            continue

        if msg_lower.startswith("xo_") and active_games.get(uid, {}).get("game") == "xo":
            game = active_games[uid]
            board = game["board"]
            try:
                cell = int(msg_lower.split("_")[1])
            except:
                continue
            if board[cell] != " ":
                continue
            board[cell] = "X"
            if check_xo_win(board, "X"):
                win_reward = 30000000000
                if user.get('game_boost_until', 0) > time.time():
                    win_reward *= 2
                db.add_balance(uid, win_reward)
                field = f"{board[0]}|{board[1]}|{board[2]}\n{board[3]}|{board[4]}|{board[5]}\n{board[6]}|{board[7]}|{board[8]}"
                send_msg(peer, f"🎉 Ты победил! +{num_to_str(win_reward)}\n\n{field}", get_games_keyboard(1))
                active_games.pop(uid, None)
                continue
            if " " not in board:
                tie_reward = 5000000000
                if user.get('game_boost_until', 0) > time.time():
                    tie_reward *= 2
                db.add_balance(uid, tie_reward)
                field = f"{board[0]}|{board[1]}|{board[2]}\n{board[3]}|{board[4]}|{board[5]}\n{board[6]}|{board[7]}|{board[8]}"
                send_msg(peer, f"🤝 Ничья! +{num_to_str(tie_reward)}\n\n{field}", get_games_keyboard(1))
                active_games.pop(uid, None)
                continue
            empty = [i for i, v in enumerate(board) if v == " "]
            bot_move = None
            for p in ["O", "X"]:
                for i in empty:
                    board[i] = p
                    if check_xo_win(board, p):
                        bot_move = i
                        board[i] = " "
                        break
                    board[i] = " "
                if bot_move is not None:
                    break
            if bot_move is None:
                bot_move = random.choice(empty)
            board[bot_move] = "O"
            if check_xo_win(board, "O"):
                if user.get('elite_until', 0) > time.time():
                    field = f"{board[0]}|{board[1]}|{board[2]}\n{board[3]}|{board[4]}|{board[5]}\n{board[6]}|{board[7]}|{board[8]}"
                    send_msg(peer, f"🛡 ELITE защита! Деньги не списаны!\n\n{field}", get_games_keyboard(1))
                else:
                    db.add_balance(uid, -20000000000)
                    field = f"{board[0]}|{board[1]}|{board[2]}\n{board[3]}|{board[4]}|{board[5]}\n{board[6]}|{board[7]}|{board[8]}"
                    send_msg(peer, f"😢 Бот победил! -20 мк\n\n{field}", get_games_keyboard(1))
                active_games.pop(uid, None)
                continue
            field = f"{board[0]}|{board[1]}|{board[2]}\n{board[3]}|{board[4]}|{board[5]}\n{board[6]}|{board[7]}|{board[8]}"
            send_msg(peer, f"Твой ход! ❌\n\n{field}", keyboard=get_xo_keyboard(board))
            continue

        if msg_lower.startswith("knb_"):
            if not is_dm:
                send_msg(peer, "❌ КНБ доступна только в ЛС!", get_main_keyboard())
                continue
            choices = {"камень": "🪨", "ножницы": "✂️", "бумага": "📄"}
            player_choice = msg_lower.split("_")[1]
            if player_choice not in choices:
                continue
            bot_choice = random.choice(list(choices.keys()))
            player_emoji = choices[player_choice]
            bot_emoji = choices[bot_choice]
            
            if player_choice == bot_choice:
                reward = 5000000000
                if user.get('game_boost_until', 0) > time.time():
                    reward *= 2
                db.add_balance(uid, reward)
                result = f"🤝 Ничья! +{num_to_str(reward)}"
            elif (player_choice == "камень" and bot_choice == "ножницы") or \
                 (player_choice == "ножницы" and bot_choice == "бумага") or \
                 (player_choice == "бумага" and bot_choice == "камень"):
                reward = 20000000000
                if user.get('game_boost_until', 0) > time.time():
                    reward *= 2
                db.add_balance(uid, reward)
                if uid not in task_progress:
                    task_progress[uid] = {}
                task_progress[uid]["knb_wins"] = task_progress[uid].get("knb_wins", 0) + 1
                result = f"🎉 Ты победил! +{num_to_str(reward)}"
                for num, task in list(active_tasks.items()):
                    if task['type'] == 'кнб':
                        wins = task_progress[uid].get("knb_wins", 0)
                        pct = int(wins / task['target'] * 100) if task['target'] > 0 else 0
                        filled = min(5, int(pct / 20))
                        done = "🟢" * filled + "⚪" * (5 - filled)
                        result += f"\n📋 Задание #{num}: {done} {wins}/{task['target']}"
                        if wins >= task['target'] and num in active_tasks:
                            new_bal = db.get_user(uid)["balance"]
                            send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                            del active_tasks[num]
                        if uid in task_progress and num in task_progress[uid]:
                            del task_progress[uid][num]
                            try:
                                conn = sqlite3.connect('database.db')
                                conn.execute('DELETE FROM tasks WHERE id = ?', (num,))
                                conn.commit()
                                conn.close()
                            except:
                                pass
            else:
                if user.get('elite_until', 0) > time.time():
                    result = "🛡 ELITE защита! Деньги не списаны!"
                else:
                    db.add_balance(uid, -20000000000)
                    result = "😢 Бот победил! -20мк"
            
            send_msg(peer, f"✂️ КНБ\n\nТы: {player_emoji}\nБот: {bot_emoji}\n\n{result}", keyboard=get_knb_keyboard())
            continue

        state = user_states.get(uid)
        if state and state.get("action") == "waiting_guess":
            if msg_lower in ["назад", "⬅ назад", "мини-игры", "🕹 mini-игры"]:
                user_states.pop(uid, None)
                send_msg(peer, "🕹 Возврат в игры:", get_games_keyboard(1))
                continue
            try:
                guess = int(msg)
                secret = state["secret"]
                attempts = state["attempts"] + 1
                if guess == secret:
                    reward = state["reward"]
                    if user.get('game_boost_until', 0) > time.time():
                        reward *= 2
                    db.add_balance(uid, reward)
                    user_states.pop(uid, None)
                    send_msg(peer, f"🎉 Верно! Загаданное число: {secret}\nТы угадал за {attempts} попыток!\n+{num_to_str(reward)} на баланс!", get_games_keyboard(1))
                    continue
                elif guess < secret:
                    hint = "🔺 Больше!"
                else:
                    hint = "🔻 Меньше!"
                if attempts >= 7:
                    user_states.pop(uid, None)
                    send_msg(peer, f"❌ Попытки кончились! Число было: {secret}", get_games_keyboard(1))
                    continue
                user_states[uid]["attempts"] = attempts
                send_msg(peer, f"{hint}\n🎲 Попытка {attempts}/7. Твоё число: {guess}")
                continue
            except:
                send_msg(peer, "❌ Введи число от 1 до 100!")
                continue

        if state and state.get("action") in ["waiting_riddle_answer", "waiting_math_answer"]:
            if msg_lower in ["загадки", "математика", "🕹 mini-игры", "мини-игры", "назад", "⬅ назад", "сапер", "💣 сапер", "кликер", "тех. поддержка", "угадай число", "🎲 угадай число", "крестики-нолики", "❌⭕ крестики-нолики", "кнб", "✂️ кнб", "вордли", "🟩 вордли", "сейф", "🔐 сейф", "купэлит", "элит", "elite"]:
                user_states.pop(uid, None)
            elif msg_lower in state["answers"]:
                user_states.pop(uid, None)
                reward = state["reward"]
                if user.get('game_boost_until', 0) > time.time():
                    reward *= 2
                db.add_balance(uid, reward)
                send_msg(peer, f"🎉 Верно, {get_user_mention(uid)}! Награда +{num_to_str(reward)} на баланс! 🧠", get_games_keyboard(1))
                continue
            else:
                correct_answer = state['answers'][0]
                user_states.pop(uid, None)
                send_msg(peer, f"❌ Неверно! Правильный ответ: «{correct_answer}». Повезет в другой раз!", get_games_keyboard(1))
                continue

        if msg_lower in ["начать", "старт", "привет"]:
            if len(parts) > 1:
                try:
                    ref_id = int(parts[-1])
                    if ref_id != uid and user.get('referrer_id', 0) == 0:
                        db.update_user_field(uid, 'referrer_id', ref_id)
                        ref_user = db.get_user(ref_id)
                        if ref_user:
                            db.add_balance(ref_id, 500000000000)
                            try:
                                send_msg(ref_id, f"🎁 Новый реферал! +500 мк на баланс!")
                            except:
                                pass
                except:
                    pass
            send_msg(peer, f"👋 Привет, {get_user_mention(uid)}!\n\n⚠️ Нажимая кнопки, вы принимаете правила @badbotik\n📌 Бот — фан-бот Нищего, не является отдельным проектом\n\n🚀 Используй кнопки ниже:", get_main_keyboard())
            continue
        elif msg_lower in ["💰 баланс", "баланс"]:
            send_msg(peer, f"👀 Ваш баланс: {balance_to_str(db.get_user(uid)['balance'])}", get_main_keyboard())
            continue
        elif msg_lower in ["🕹 mini-игры", "мини-игры"]:
            send_msg(peer, "🕹 Мини-игры:\n\n💣 Сапер\n🕵 Загадки\n🧮 Математика\n📱 Кликер\n🎲 Угадай число\n❌⭕ Крестики-нолики\n✂️ КНБ\n🟩 Вордли\n🔐 Сейф\n💣 Бомба\n🪢 Виселица\n💰 Миллионер\n⚔️ Битва", get_games_keyboard(1))
            continue
        elif msg_lower in ["📱 кликер", "клик", "кликер"]:
            now = time.time()
            if now - user.get('last_click', 0) < 4.0 and user.get('no_cd_until', 0) < now:
                left = int(4.0 - (now - user.get('last_click', 0)))
                dots = '. ' * left
                send_msg(peer, f"⏳ Кликер будет доступен через {left} сек")
                continue
            if user.get('elite_until', 0) > now:
                required_cd = 0.05
                reward = 20000000000
            else:
                required_cd = 0.05 if user.get('no_cd_until', 0) > now else 4.0
                reward = 30000000000 if user.get('x2_until', 0) > now else 15000000000
            if (now - user.get('last_click', 0)) < required_cd:
                continue
            db.update_user_field(uid, 'last_click', now)

            db.update_user_field(uid, 'clicks_count', user.get('clicks_count', 0) + 1)
            for num, task in list(active_tasks.items()):
                if task['type'] == 'клик' and num in active_tasks:
                    if uid not in task_progress:
                        task_progress[uid] = {}
                    task_progress[uid][num] = task_progress[uid].get(num, 0) + 1
                    if task_progress[uid][num] >= task['target']:
                        db.add_balance(uid, task['reward'])
                        send_msg(peer, f"🎉 Задание #{num} выполнено!\n+{task['reward_str']}")
            new_bal = db.add_balance(uid, reward)
            send_msg(peer, f"🎯 Клик! +{num_to_str(reward)}\n💰 Баланс: {num_to_str(new_bal)}", get_games_keyboard(1))
            continue
        elif msg_lower in ["💣 мины", "мины", "сапер", "💣 сапер"]:
            if not is_dm:
                send_msg(peer, "❌ Сапер доступен только в ЛС!", get_games_keyboard(1))
                continue
            is_elite = user.get('elite_until', 0) > time.time()
            f = [1, 1, 1, 0, 0, 0, 0, 0, 0] if is_elite else [1, 1, 1, 1, 1, 1, 0, 0, 0]
            random.shuffle(f)
            active_games[uid] = {"game": "mines", "field": f, "opened": [], "current_bank": 0, "elite": is_elite}
            diamonds = "6" if is_elite else "3"
            send_msg(peer, f"💣 Сапер (3х3)\nНа поле {diamonds} алмаза. Каждая чистая коробка: +40 мк в куш!", keyboard=get_mines_keyboard(active_games[uid]))
        elif msg_lower == "💰 забрать куш":
            game = active_games.get(uid)
            if game and game.get("game") == "mines" and len(game["opened"]) > 0:
                db.add_balance(uid, game["current_bank"])
                send_msg(peer, f"💰 Ты забрал куш: {num_to_str(game['current_bank'])}!", get_games_keyboard(1))
                if uid not in task_progress:
                    task_progress[uid] = {}
                task_progress[uid]["mines_wins"] = task_progress[uid].get("mines_wins", 0) + 1
                for num, task in list(active_tasks.items()):
                    if task['type'] == 'сапер':
                        wins = task_progress[uid].get("mines_wins", 0)
                        pct = int(wins / task['target'] * 100) if task['target'] > 0 else 0
                        filled = min(5, int(pct / 20))
                        done = "🟢" * filled + "⚪" * (5 - filled)
                        send_msg(peer, f"📋 Задание #{num}: {done} {wins}/{task['target']}")
                        if wins >= task['target'] and num in active_tasks:
                            new_bal = db.get_user(uid)["balance"]
                            send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                            del active_tasks[num]
                        if uid in task_progress and num in task_progress[uid]:
                                del task_progress[uid][num]
                                del task_progress[uid][num]
                active_games.pop(uid, None)
            continue
        elif msg_lower in ["🧮 математика", "математика"]:
            a = random.randint(10, 99)
            b = random.randint(10, 99)
            user_states[uid] = {"action": "waiting_math_answer", "answers": [str(a + b)], "reward": 25000000000}
            send_msg(peer, f"🧮 Математика (+25 мк)\n\nРеши пример: {a} + {b} = ?\n⚠️ У тебя 1 попытка!")
            continue
        elif msg_lower in ["🕵 загадки", "загадки"]:
            if not is_dm:
                send_msg(peer, "❌ Только в ЛС!", get_games_keyboard(1))
                continue
            r = random.choice(RIDDLES_POOL)
            user_states[uid] = {"action": "waiting_riddle_answer", "answers": r["a"], "reward": 40000000000}
            send_msg(peer, f"🕵️‍♂️ Загадка (+40 мк)\n\n{r['q']}\n⚠️ 1 попытка!")
            continue
        elif msg_lower in ["🎲 угадай число", "угадай число"]:
            secret = random.randint(1, 100)
            user_states[uid] = {"action": "waiting_guess", "secret": secret, "attempts": 0, "reward": 50000000000}
            send_msg(peer, "🎲 Угадай число (+50 мк)!\n\nЯ загадал число от 1 до 100.\nУ тебя 7 попыток. Пиши число в чат!")
            continue
        elif msg_lower in ["❌⭕ крестики-нолики", "крестики-нолики"]:
            if not is_dm:
                send_msg(peer, "❌ Крестики-нолики доступны только в ЛС!", get_games_keyboard(1))
                continue
            board = [" "] * 9
            active_games[uid] = {"game": "xo", "board": board}
            send_msg(peer, "❌⭕ Крестики-нолики (3x3)\n\nТы играешь за ❌, бот за ⭕.\nВыигрыш: +30 мк\nПроигрыш: -20 мк\nНичья: +5 мк\n\nТвой ход! Выбери клетку:", keyboard=get_xo_keyboard(board))
            continue
        elif msg_lower == "битва":
            send_msg(peer, "⚔️ Битва\n\nИспользование: битва (сумма) (ответ на смс соперника)\nПример: битва 5мм\n\nПобедитель забирает ставку!")
            continue

        elif msg_lower.startswith("битва ") and len(parts) > 1:
            parts_cmd = msg.split()
            amount = str_to_num(parts_cmd[1])
            if not amount or amount <= 0:
                send_msg(peer, "❌ Укажите сумму!")
                continue
            if user['balance'] < amount:
                send_msg(peer, f"❌ Недостаточно средств!")
                continue
            target_id = parse_target(parts_cmd, 2, message_obj)
            if not target_id or target_id == uid:
                send_msg(peer, "❌ Ответьте на сообщение соперника!")
                continue
            if db.get_user(target_id)['balance'] < amount:
                send_msg(peer, f"❌ У соперника недостаточно средств!")
                continue
            battle_key = f"bwait_{uid}_{target_id}"
            active_games[battle_key] = {"game": "battle_wait", "amount": amount, "p1": uid, "p2": target_id, "peer": peer}
            send_msg(peer, f"⚔️ {get_user_mention(uid)} вызывает на битву {get_user_mention(target_id)} на {num_to_str(amount)}!\n\n{get_user_mention(target_id)}, напиши 'принять'")
            continue

        elif msg_lower == "принять":
            for key, b in list(active_games.items()):
                if b.get("game") == "battle_wait" and b["p2"] == uid:
                    send_msg(b["peer"], "3...")
                    time.sleep(1); send_msg(b["peer"], "2...")
                    time.sleep(1); send_msg(b["peer"], "1...")
                    time.sleep(1)
                    op = random.choice(["*", "/", "+", "-"])
                    if op == "*":
                        a = random.randint(10, 99); bb = random.randint(10, 99); ans = a * bb
                    elif op == "/":
                        bb = random.randint(10, 99); ans = random.randint(10, 99); a = bb * ans
                    elif op == "+":
                        a = random.randint(1000, 9999); bb = random.randint(1000, 9999); ans = a + bb
                    else:
                        a = random.randint(1000, 9999); bb = random.randint(100, 999); ans = a - bb
                    b["game"] = "battle_go"; b["a"] = a; b["b"] = bb; b["answer"] = ans; b["op"] = op
                    active_games[b["p1"]] = b; active_games[b["p2"]] = b
                    send_msg(b["peer"], f"⚔️ БИТВА!\n\n{a} x {bb} = ?\nСтавка: {num_to_str(b['amount'])}")
                    break
            continue

        elif active_games.get(uid, {}).get("game") == "battle_go":
            b = active_games[uid]
            try: answer = int(msg.strip())
            except: continue
            if answer == b["answer"]:
                w = uid; l = b["p1"] if uid == b["p2"] else b["p2"]
                db.add_balance(w, b["amount"]); db.add_balance(l, -b["amount"])
                send_msg(b["peer"], f"🎉 {get_user_mention(w)} победил!\n+{num_to_str(b['amount'])}\n{get_user_mention(l)} -{num_to_str(b['amount'])}")
                active_games.pop(b["p1"], None); active_games.pop(b["p2"], None)
            continue

        elif msg_lower in ["✂️ кнб", "кнб"]:
            if not is_dm:
                send_msg(peer, "❌ КНБ доступна только в ЛС!", get_games_keyboard(1))
                continue
            send_msg(peer, "✂️ КНБ\n\nВыигрыш: +25 мк\nНичья: +5 мк\nПроигрыш: 0\n\nВыбери:", keyboard=get_knb_keyboard())
            continue
        elif msg_lower in ["🏇 скачки", "скачки"]:
            if not is_dm:
                send_msg(peer, "❌ Скачки доступны только в ЛС!", get_games_keyboard(3))
                continue
            if user['balance'] < 10000000000:
                send_msg(peer, "❌ Минимальная ставка: 10 мк!", get_games_keyboard(3))
                continue
            horses = [
                {"name": "Буран", "emoji": "🐎", "koef": 1.5, "color": VkKeyboardColor.PRIMARY},
                {"name": "Ветер", "emoji": "🐴", "koef": 2.5, "color": VkKeyboardColor.POSITIVE},
                {"name": "Молния", "emoji": "🏇", "koef": 4, "color": VkKeyboardColor.POSITIVE},
                {"name": "Тайфун", "emoji": "🦄", "koef": 7, "color": VkKeyboardColor.NEGATIVE}
            ]
            active_games[uid] = {"game": "horses", "horses": horses, "bet": 0}
            kb = VkKeyboard(one_time=True)
            for h in horses:
                kb.add_button(f"{h['emoji']} {h['name']} x{h['koef']}", color=h['color'], payload={"cmd": f"horse_{h['name']}"})
                kb.add_line()
            send_msg(peer, "🏇 Конные скачки!\n\nВыбери лошадь (ставка 10 мк):", keyboard=kb.get_keyboard())
            continue

        elif msg_lower in ["миллионер", "💰 миллионер"]:
            if not is_dm:
                send_msg(peer, "❌ Только в ЛС!", get_games_keyboard(3))
                continue
            q = random.choice(MILLIONER_QUESTIONS)
            kb = VkKeyboard(one_time=True)
            for i, ans in enumerate(q["a"]):
                kb.add_button(ans, color=VkKeyboardColor.PRIMARY, payload={"cmd": f"millioner_{i}"})
                if i == 1:
                    kb.add_line()
            kb.add_button("💡 50/50 (100мк)", color=VkKeyboardColor.NEGATIVE, payload={"cmd": "millioner_5050"})
            active_games[uid] = {"game": "millioner", "question": q, "reward": 40000000000, "bank": 0}
            send_msg(peer, f"💰 Миллионер?\n\n{q['q']}\n\n+40мк за ответ!", keyboard=kb.get_keyboard())
            continue

        elif msg_lower in ["виселица", "🪢 виселица"]:
            if not is_dm:
                send_msg(peer, "❌ Виселица доступна только в ЛС!", get_games_keyboard(3))
                continue
            import random
            word = random.choice(WORDS_POOL).lower()
            shuffled = list(word)
            random.shuffle(shuffled)
            while ''.join(shuffled) == word:
                random.shuffle(shuffled)
            shuffled_str = ''.join(shuffled)
            word_len = len(word)
            if word_len <= 8:
                reward = 40000000000
            elif word_len <= 10:
                reward = 60000000000
            else:
                reward = 85000000000
            active_games[uid] = {"game": "hangman", "word": word, "shuffled": shuffled_str, "reward": reward, "attempts": 0}
            send_msg(peer, f"🪢 Виселица!\n\nПеремешанные буквы: {shuffled_str.upper()}\nДлина: {word_len} букв\nНаграда: {num_to_str(reward)}\n\nПиши слово (1 попытка):")
            continue

        elif msg_lower in ["💣 бомба", "бомба"]:
            if not is_dm:
                send_msg(peer, "❌ Бомба доступна только в ЛС!", get_games_keyboard(3))
                continue
            import random
            length = random.randint(6, 8)
            secret_code = str(random.randint(10**(length-1), 10**length - 1))
            digit_sum = sum(int(d) for d in secret_code)
            first_digit = secret_code[0]
            active_games[uid] = {"game": "bomb", "secret": secret_code, "deadline": time.time() + 30, "length": length, "digit_sum": digit_sum, "first_digit": first_digit, "attempts": 0, "reward_penalty": 0}
            send_msg(peer, f"💣 Таймер-бомба!\n\nЗагадано {length}-значное число.\nСумма цифр: {digit_sum}\nПервая цифра: {first_digit}\n\n⏳ 30 секунд! Введи число:")
            continue

        elif msg_lower in ["🔐 сейф", "сейф"]:
            if not is_dm:
                send_msg(peer, "❌ Сейф доступен только в ЛС!", get_games_keyboard(1))
                continue
            secret_code = ""
            digits = list("0123456789")
            random.shuffle(digits)
            secret_code = "".join(digits[:4])
            active_games[uid] = {"game": "safe", "secret": secret_code, "attempts": 0}
            send_msg(peer, "🔐 Взлом сейфа!\n\nЯ загадал 4-значный код (цифры не повторяются).\nУ тебя 7 попыток.\nВведи 4 цифры:")
            continue
        elif msg_lower in ["🟩 вордли", "вордли"]:
            if not is_dm:
                send_msg(peer, "❌ Вордли доступен только в ЛС!", get_games_keyboard(1))
                continue
            secret = random.choice(WORDLE_WORDS)
            active_games[uid] = {"game": "wordle", "secret": secret, "attempts": 0, "history": ""}
            send_msg(peer, "🟩 Вордли — угадай слово из 5 букв!\n\nУ тебя 6 попыток.\n\n⬜ — буквы нет\n🟨 — буква есть, но не на месте\n🟩 — буква на месте\n\nВведи слово из 5 букв:")
            continue
        elif msg_lower in ["🎁 бонус", "бонус"]:
            user = db.get_user(uid)
            now = time.time()
            if now - user.get('last_daily', 0) < 86400:
                left = int(86400 - (now - user.get('last_daily', 0)))
                send_msg(peer, f"❌ Бонус уже получен! Приходите через {left//3600}ч {(left%3600)//60}м.", get_main_keyboard())
            else:
                bonus_reward = 300000000000
                if user.get('elite_until', 0) > now:
                    bonus_reward *= 2
                db.add_balance(uid, bonus_reward)
                db.update_user_field(uid, 'last_daily', now)
                send_msg(peer, f"🎁 Ежедневный бонус получен! +{num_to_str(bonus_reward)} на баланс.", get_main_keyboard())
            continue
        elif msg_lower in ["🛠 тех. поддержка", "тех. поддержка", "техподдержка"]:
            send_msg(peer, "Агент Сенгоку отвечает в течении 12 часов! Чтобы с ним связаться нажмите на кнопку ниже,", get_support_keyboard())
            continue
        elif msg_lower == "вывод":
            send_msg(peer, "💸 Вывод средств\n\n💰 Мин. сумма: 1мм\n📝 вывод (сумма)\nПример: вывод 1мм\n\n💡 Средства выводятся в @badbotik")
            continue

        elif msg_lower.startswith("вывод") and len(parts) > 1:
            amount = str_to_num(parts[1:])
            if not amount or amount <= 0:
                send_msg(peer, "❌ Укажите корректную сумму для вывода. Пример: вывод 1мм")
                continue
            if amount < 1000000000000:
                send_msg(peer, f"❌ Минимальная сумма вывода: 1мм. Ваш запрос: {num_to_str(amount)}")
                continue
            if cupons.get(uid, 0) > 0:
                cupons[uid] -= 1
                send_msg(peer, f"🎫 Использован купон! Бесплатный вывод {num_to_str(amount)}")
            elif user['balance'] < amount:
                send_msg(peer, "❌ Недостаточно средств на балансе бота.")
                continue
            now = time.time()
            last_withdraw = user.get('last_withdraw', 0)
            withdraw_cd = 1800 if user.get('elite_until', 0) > now else 7200
            if now - last_withdraw < withdraw_cd:
                left = int(withdraw_cd - (now - last_withdraw))
                send_msg(peer, f"❌ Вывод доступен раз в {withdraw_cd//3600}ч {(withdraw_cd%3600)//60}м!\nОсталось: {left//3600}ч {(left%3600)//60}м")
                continue
            db.add_balance(uid, -amount)
            db.update_user_field(uid, 'total_withdrawn', user.get('total_withdrawn', 0) + amount)
            db.update_user_field(uid, 'last_withdraw', now)
            db.add_withdraw_log(uid, amount)
            success = badbot.pay_user(uid, amount)
            if success:
                send_msg(peer, f"✅ Вывод {num_to_str(amount)} выполнен!")
                send_msg(DONATE_CHAT_ID, f"✅ Вывод: {num_to_str(amount)} -> {get_user_mention(uid)}")
            else:
                db.add_balance(uid, amount)
                db.update_user_field(uid, 'total_withdrawn', user.get('total_withdrawn', 0) - amount)
                db.update_user_field(uid, 'last_withdraw', last_withdraw)
                send_msg(peer, "❌ Ошибка вывода. Средства возвращены на баланс.")
            continue
        elif msg_lower.startswith("+ник ") and len(parts) > 1:
            new_name = " ".join(parts[1:]).strip()
            if len(new_name) > 15:
                send_msg(peer, "❌ Максимальная длина имени — 15 символов!")
                continue
            db.update_user_field(uid, 'nickname', new_name)
            USER_NAMES_CACHE[uid] = new_name
            send_msg(peer, f"✅ Вы успешно изменили имя профиля на: {new_name}!")
            continue
        elif msg_lower.startswith("+игра "):
            game = " ".join(parts[1:]).strip()
            allowed_games = ["сапер", "кликер", "бомба", "вордли", "кнб", "угадай число", "сейф", "крестики-нолики", "математика", "загадки", "виселица", "миллионер"]
            if game.lower() not in allowed_games:
                send_msg(peer, f"❌ Игра не найдена! Доступные: {', '.join(allowed_games)}")
                continue
            db.update_user_field(uid, 'fav_game', game)
            send_msg(peer, f"✅ Любимая игра: {game}")
            continue

        elif msg_lower == "+игра":
            send_msg(peer, "❌ Использование: +игра (название)\nДоступные: сапер, кликер, бомба, вордли, кнб, угадай число, сейф, крестики-нолики, математика, загадки, виселица")
            continue

        elif msg_lower.startswith("+исполнитель "):
            artist = " ".join(parts[1:]).strip()
            if len(artist) > 30:
                send_msg(peer, "❌ Максимум 30 символов!")
                continue
            db.update_user_field(uid, 'fav_artist', artist)
            send_msg(peer, f"✅ Любимый исполнитель: {artist}")
            continue

        elif msg_lower == "+исполнитель":
            send_msg(peer, "❌ Использование: +исполнитель (имя)")
            continue

        elif msg_lower.startswith("+ник"):
            send_msg(peer, "❌ Использование: +ник (новое имя)\nПример: +ник КрутойИгрок")
            continue
        elif msg_lower == "топ":
            send_msg(peer, "📊 Какой топ?\n• топ клик — по кликам\n• топ вывод — по выводу")
            continue

        elif msg_lower in ["топ кликов", "топ клик"]:
            conn = sqlite3.connect('database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, clicks_count, nickname FROM users ORDER BY clicks_count DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()
            txt = "🏆 Топ-10 по кликам:\n\n"
            for i, r in enumerate(rows, 1):
                name = r['nickname']
                if not name or name == 'Игрок':
                    try:
                        if r['user_id'] > 0:
                            vk_u = vk.users.get(user_ids=r['user_id'])
                            name = f"{vk_u[0]['first_name']} {vk_u[0]['last_name']}"
                        else:
                            name = f"Сообщество {abs(r['user_id'])}"
                    except:
                        name = f"ID {r['user_id']}"
                txt += f"{i}. [id{r['user_id']}|{name}] — {r['clicks_count']} кл.\n"
            send_msg(peer, txt, get_main_keyboard())
            continue

        elif msg_lower in ["топ вывода"]:
            conn = sqlite3.connect('database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, total_withdrawn, nickname FROM users ORDER BY total_withdrawn DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()
            txt = "🏆 Топ-10 по выводу:\n\n"
            for i, r in enumerate(rows, 1):
                name = r['nickname']
                if not name or name == 'Игрок':
                    try:
                        if r['user_id'] > 0:
                            vk_u = vk.users.get(user_ids=r['user_id'])
                            name = f"{vk_u[0]['first_name']} {vk_u[0]['last_name']}"
                        else:
                            name = f"Сообщество {abs(r['user_id'])}"
                    except:
                        name = f"ID {r['user_id']}"
                txt += f"{i}. [id{r['user_id']}|{name}] — {num_to_str(r['total_withdrawn'])}\n"
            send_msg(peer, txt, get_main_keyboard())
            continue

        elif msg_lower in ["топ клик", "топ кликов"]:
            conn = sqlite3.connect('database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, clicks_count, nickname FROM users ORDER BY clicks_count DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()
            txt = "🏆 Топ-10 по кликам:\n\n"
            for i, r in enumerate(rows, 1):
                name = r['nickname']
                if not name or name == 'Игрок':
                    try:
                        if r['user_id'] > 0:
                            vk_u = vk.users.get(user_ids=r['user_id'])
                            name = f"{vk_u[0]['first_name']} {vk_u[0]['last_name']}"
                        else:
                            name = f"Сообщество {abs(r['user_id'])}"
                    except:
                        name = f"ID {r['user_id']}"
                txt += f"{i}. [id{r['user_id']}|{name}] — {r['clicks_count']} кл.\n"
            send_msg(peer, txt, get_main_keyboard())
            continue
        elif msg_lower in ["топ вывод", "топ вывода"]:
            conn = sqlite3.connect('database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, total_withdrawn, nickname FROM users ORDER BY total_withdrawn DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()
            txt = "🏆 Топ-10 по выводу:\n\n"
            for i, r in enumerate(rows, 1):
                name = r['nickname']
                if not name or name == 'Игрок':
                    try:
                        if r['user_id'] > 0:
                            vk_u = vk.users.get(user_ids=r['user_id'])
                            name = f"{vk_u[0]['first_name']} {vk_u[0]['last_name']}"
                        else:
                            name = f"Сообщество {abs(r['user_id'])}"
                    except:
                        name = f"ID {r['user_id']}"
                txt += f"{i}. [id{r['user_id']}|{name}] — {num_to_str(r['total_withdrawn'])}\n"
            send_msg(peer, txt, get_main_keyboard())
            continue

        elif msg_lower in ["рефка", "🔗 рефка"]:
            send_msg(peer, f"🔗 Реферальная ссылка:\n\nhttps://vk.me/{GROUP_ID}?ref={uid}\n\n🎁 За друга: 500 мк!", get_main_keyboard())
            continue
        elif msg_lower in ["услуги", "мои услуги"]:
            user = db.get_user(uid)
            now = time.time()
            txt = "🛍 Ваши активные услуги:\n\n"
            has_any = False
            if user.get('no_cd_until', 0) > now:
                left = int(user['no_cd_until'] - now)
                txt += f"• Снятие КД кликера: ещё {left//3600}ч {(left%3600)//60}м\n"
                has_any = True
            if user.get('x2_until', 0) > now:
                left = int(user['x2_until'] - now)
                txt += f"• Множитель х2 клика: ещё {left//3600}ч {(left%3600)//60}м\n"
                has_any = True
            if user.get('elite_until', 0) > now:
                left = int(user['elite_until'] - now)
                txt += f"• 🌟 ELITE: ещё {left//3600}ч {(left%3600)//60}м\n"
                has_any = True
            if user.get('game_boost_until', 0) > now:
                left = int(user['game_boost_until'] - now)
                txt += f"• Множитель игр х2: ещё {left//3600}ч {(left%3600)//60}м\n"
                has_any = True
            if not has_any:
                txt += "❌ Нет активных услуг."
            send_msg(peer, txt, get_main_keyboard())
            continue
        elif msg_lower in ["задания", "📋 задания"]:
            if not active_tasks:
                send_msg(peer, "📋 Нет активных заданий.", get_games_keyboard(1))
                continue
            txt = "📋 Активные задания:\n\n"
            for num, task in list(active_tasks.items()):
                txt += f"#{num} {task.get('desc', task.get('type', '?'))} | Награда: {num_to_str(task['reward'])}\n"
            send_msg(peer, txt, get_games_keyboard(1))
            continue
        elif msg_lower in ["прогресс"]:
            send_msg(peer, "📋 Используйте команду: задания", get_main_keyboard())
            continue

        elif False:
            if not active_tasks:
                send_msg(peer, "📋 Нет активных заданий.", get_main_keyboard())
                continue
            txt = "📊 Ваш прогресс:\n\n"
            has_any = False
            for num, task in list(active_tasks.items()):
                progress = task_progress.get(uid, {}).get(num, 0)
                pct = int(progress / task['target'] * 100) if task['target'] > 0 else 0
                filled = min(5, int(pct / 20))
                done = "🟢" * filled
                left = "⚪" * (5 - filled)
                txt += f"#{num} {done}{left} {progress}/{task['target']}\n"
                has_any = True
            if not has_any:
                txt += "Нет прогресса."
            send_msg(peer, txt, get_main_keyboard())
            continue
        elif msg_lower == "+день":
            if uid not in task_progress:
                task_progress[uid] = {}
            task_progress[uid]["daily_login"] = task_progress[uid].get("daily_login", 0) + 1
            send_msg(peer, f"✅ День засчитан! ({task_progress[uid]['daily_login']})")
            for num, task in list(active_tasks.items()):
                if task['type'] == 'вход':
                    logins = task_progress[uid].get("daily_login", 0)
                    pct = int(logins / task['target'] * 100) if task['target'] > 0 else 0
                    filled = min(5, int(pct / 20))
                    done = "🟢" * filled + "⚪" * (5 - filled)
                    send_msg(peer, f"📋 Задание #{num}: {done} {logins}/{task['target']}")
                    if logins >= task['target'] and num in active_tasks:
                        db.add_balance(uid, task['reward'])
                        new_bal = db.get_user(uid)["balance"]
                        send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                        del active_tasks[num]
            continue
        elif msg_lower in ["промокоды", "промо список"]:
            if not promo_codes:
                send_msg(peer, "🎫 Нет активных промокодов.")
                continue
            txt = "🎫 Активные промокоды:\n\n"
            for name, promo in promo_codes.items():
                left = promo['activations'] - len(promo['used'])
                txt += f"• {name} — {promo['reward_str']} (активаций: {left})\n"
            txt += "\nДля активации: промо (название)\nПример: промо MEGAPROMO"
            send_msg(peer, txt)
            continue
        elif msg_lower in ["элит", "elite", "elit", "элит привилегии"]:
            send_msg(peer, "🌟 ELITE привилегии:\n\n✅ Кликер без КД\n✅ +50% к награде кликера\n✅ Ежедневный бонус x2\n✅ 6 алмазов в сапёре (x2)\n✅ Защита от снятия денег при проигрыше (КНБ, сейф, крестики-нолики)\n✅ +10 сек в Бомбе\n✅ Ставка на 2 лошадей в Скачках\n✅ Вывод раз в 30 минут\n✅ Значок 🌟 ELITE в профиле\n\nСтоимость: 5 мм/день\nКупить: купэлит (дни)", get_main_keyboard())
            continue
        elif msg_lower in ["мой elite", "мой элит", "мой elit"]:
            user = db.get_user(uid)
            now = time.time()
            if user.get('elite_until', 0) > now:
                left = int(user['elite_until'] - now)
                send_msg(peer, f"🌟 Ваша ELITE подписка закончится через {left//3600}ч {(left%3600)//60}м", get_main_keyboard())
            else:
                send_msg(peer, "❌ У вас нет активной ELITE подписки.", get_main_keyboard())
            continue
        elif msg_lower in ["репорт", "Репорт"]:
            send_msg(peer, "📢 Репорт\n\nИспользование: репорт (ответ на смс) (причина)\nПример: репорт оскорбление\n\nОтветьте на сообщение нарушителя и укажите причину!")
            continue

        elif msg_lower.startswith("мут "):
            parts_cmd = msg.split()
            if len(parts_cmd) < 3:
                send_msg(peer, "❌ Использование: мут (ответ/ссылка) (часы) (причина)\nПример: мут @user 2 оскорбление")
                continue
            target_id = parse_target(parts_cmd, 1, message_obj)
            if not target_id:
                send_msg(peer, "❌ Пользователь не найден!")
                continue
            try:
                hours = int(parts_cmd[2])
            except:
                send_msg(peer, "❌ Укажите срок в часах!")
                continue
            reason = " ".join(parts_cmd[3:]) if len(parts_cmd) > 3 else "Не указана"
            vk.messages.send(peer_id=peer, message=f"!мут {hours} ч", reply_to=message_obj.get('reply_message', {}).get('id') or message_obj.get('id'), random_id=0)
            send_msg(peer, f"✅ Мут {hours}ч для {get_user_mention(target_id)}\nПричина: {reason}")
            continue

        elif msg_lower.startswith("репорт "):
            if not message_obj.get('reply_message'):
                send_msg(peer, "❌ Ответьте на сообщение нарушителя!")
                continue
            target_id = message_obj['reply_message']['from_id']
            target_text = message_obj['reply_message'].get('text', '')
            reason = " ".join(parts[1:]) if len(parts) > 1 else "Не указана"
            now_str = datetime.now(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M:%S")
            chat_names_rep = {2000000001: "Работяги / Бот Заработок", 2000000004: "Чат модерации", 2000000003: "Консоль"}
            chat_name = chat_names_rep.get(peer, f"Чат {peer}")
            report_msg = f"📋 Репорт\n\nОт: {get_user_mention(uid)}\nНа: {get_user_mention(target_id)} (ID: {target_id})\n💬 Чат: {chat_name}\nСообщение: {target_text}\nПричина: {reason}\n🕐 {now_str} (МСК)"
            fwd_id = message_obj['reply_message']['id']
            conn = sqlite3.connect('database.db')
            cur = conn.execute("SELECT user_id FROM users WHERE moder_rank >= 1")
            for (mod_id,) in cur.fetchall():
                try:
                    vk.messages.send(peer_id=mod_id, message=report_msg, random_id=0)
                except:
                    pass
            conn.close()
            send_msg(peer, "✅ Репорт отправлен!")
            continue

        elif msg_lower in ["🛍 магазин", "магазин"]:
            if not is_dm:
                send_msg(peer, "❌ Магазин доступен только в ЛС!", get_main_keyboard())
                continue
            send_msg(peer, "🛍️ Магазин услуг:", template=get_shop_carousel())
            continue
        elif msg_lower.startswith("получить снятие кд"):
            if not is_dm:
                send_msg(peer, "❌ Магазин доступен только в ЛС!", get_main_keyboard())
                continue
            item = SHOP_ITEMS[0]
            user = db.get_user(uid)
            if user['balance'] < item["cost_coins"]:
                send_msg(peer, "❌ Недостаточно средств!", get_main_keyboard())
                continue
            db.add_balance(uid, -item["cost_coins"])
            db.update_user_field(uid, 'no_cd_until', time.time() + 86400)
            user = db.get_user(uid)
            send_msg(peer, f"✅ Услуга '{item['title']}' успешно куплена на 12 часов!", get_main_keyboard())
            if uid not in task_progress:
                task_progress[uid] = {}
            task_progress[uid]["shop_buys"] = task_progress[uid].get("shop_buys", 0) + 1
            for num, task in list(active_tasks.items()):
                if task['type'] == 'магазин':
                    buys = task_progress[uid].get("shop_buys", 0)
                    pct = int(buys / task['target'] * 100) if task['target'] > 0 else 0
                    filled = min(5, int(pct / 20))
                    done = "🟢" * filled + "⚪" * (5 - filled)
                    send_msg(peer, f"📋 Задание #{num}: {done} {buys}/{task['target']}")
                    if buys >= task['target'] and num in active_tasks:
                                db.add_balance(uid, task['reward'])
                                new_bal = db.get_user(uid)["balance"]
                                send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                                del active_tasks[num]
            continue
        elif msg_lower.startswith("получить множитель"):
            if not is_dm:
                send_msg(peer, "❌ Магазин доступен только в ЛС!", get_main_keyboard())
                continue
            item = SHOP_ITEMS[1]
            user = db.get_user(uid)
            if user['balance'] < item["cost_coins"]:
                send_msg(peer, "❌ Недостаточно средств!", get_main_keyboard())
                continue
            db.add_balance(uid, -item["cost_coins"])
            db.update_user_field(uid, 'x2_until', time.time() + 86400)
            send_msg(peer, f"✅ Услуга '{item['title']}' успешно куплена на 12 часов!", get_main_keyboard())
            if uid not in task_progress:
                task_progress[uid] = {}
            task_progress[uid]["shop_buys"] = task_progress[uid].get("shop_buys", 0) + 1
            for num, task in list(active_tasks.items()):
                if task['type'] == 'магазин':
                    buys = task_progress[uid].get("shop_buys", 0)
                    pct = int(buys / task['target'] * 100) if task['target'] > 0 else 0
                    filled = min(5, int(pct / 20))
                    done = "🟢" * filled + "⚪" * (5 - filled)
                    send_msg(peer, f"📋 Задание #{num}: {done} {buys}/{task['target']}")
                    if buys >= task['target'] and num in active_tasks:
                        db.add_balance(uid, task['reward'])
                        new_bal = db.get_user(uid)["balance"]
                        send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                    del active_tasks[num]
            continue
        elif msg_lower.startswith("получить безлимит вывод"):
            if not is_dm:
                send_msg(peer, "❌ Магазин доступен только в ЛС!", get_main_keyboard())
                continue
            item = SHOP_ITEMS[2]
            user = db.get_user(uid)
            if user['balance'] < item["cost_coins"]:
                send_msg(peer, "❌ Недостаточно средств!", get_main_keyboard())
                continue
            db.add_balance(uid, -item["cost_coins"])
            db.update_user_field(uid, 'last_withdraw', 0)
            send_msg(peer, f"✅ Безлимит вывод на 24 часа!", get_main_keyboard())
            continue

        elif msg_lower in ["купить вип", "купить вип пакет"]:
            if not is_dm:
                send_msg(peer, "❌ Магазин доступен только в ЛС!", get_main_keyboard())
                continue
            item = SHOP_ITEMS[4]
            user = db.get_user(uid)
            if user['balance'] < item["cost_coins"]:
                send_msg(peer, "❌ Недостаточно средств!", get_main_keyboard())
                continue
            db.add_balance(uid, -item["cost_coins"])
            db.update_user_field(uid, 'no_cd_until', time.time() + 86400)
            db.update_user_field(uid, 'game_boost_until', time.time() + 86400)
            db.update_user_field(uid, 'last_withdraw', 0)
            current_elite = user.get('elite_until', 0)
            if current_elite < time.time():
                current_elite = time.time()
            db.update_user_field(uid, 'elite_until', current_elite + 3 * 86400)
            db.update_user_field(uid, 'vip_until', time.time() + 86400)
            send_msg(peer, "✅ VIP пакет активирован!\n• Снятие КД кликера 24ч\n• х2 игры 24ч\n• Безлимит вывод 24ч\n• ELITE 3 дня\n• Метка VIP", get_main_keyboard())
            continue

        elif msg_lower.startswith("получить множитель игр"):
            if not is_dm:
                send_msg(peer, "❌ Магазин доступен только в ЛС!", get_main_keyboard())
                continue
            item = SHOP_ITEMS[2]
            user = db.get_user(uid)
            if user['balance'] < item["cost_coins"]:
                send_msg(peer, "❌ Недостаточно средств!", get_main_keyboard())
                continue
            db.add_balance(uid, -item["cost_coins"])
            db.update_user_field(uid, 'game_boost_until', time.time() + 86400)
            send_msg(peer, f"✅ Услуга '{item['title']}' успешно куплена на 12 часов!", get_main_keyboard())
            if uid not in task_progress:
                task_progress[uid] = {}
            task_progress[uid]["shop_buys"] = task_progress[uid].get("shop_buys", 0) + 1
            for num, task in list(active_tasks.items()):
                if task['type'] == 'магазин':
                    buys = task_progress[uid].get("shop_buys", 0)
                    pct = int(buys / task['target'] * 100) if task['target'] > 0 else 0
                    filled = min(5, int(pct / 20))
                    done = "🟢" * filled + "⚪" * (5 - filled)
                    send_msg(peer, f"📋 Задание #{num}: {done} {buys}/{task['target']}")
                    if buys >= task['target'] and num in active_tasks:
                        db.add_balance(uid, task['reward'])
                        new_bal = db.get_user(uid)["balance"]
                        send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                    del active_tasks[num]
            continue
        elif msg_lower in ["купэлит", "elite"] or msg_lower.startswith("купэлит ") or msg_lower.startswith("elite "):
            if len(parts) > 1:
                try:
                    days = int(parts[1])
                except:
                    send_msg(peer, "❌ Использование: купэлит (кол-во дней)\nСтоимость: 5 мм/день")
                    continue
            else:
                user_states[uid] = {"action": "waiting_elite_days", "peer_id": peer}
                send_msg(peer, "🌟 ELITE подписка — 5 мм/день\n\nНа сколько дней хотите купить?\nВведите число дней:")
                continue
            if days < 1:
                send_msg(peer, "❌ Минимальный срок — 1 день!")
                continue
            cost = days * 5000000000000
            fresh_user = db.get_user(uid)
            if fresh_user['balance'] < cost:
                send_msg(peer, f"❌ Недостаточно средств!\nНужно: {num_to_str(cost)}\nВаш баланс: {num_to_str(fresh_user['balance'])}\n\nПополните баланс командой: пополнить {num_to_str(cost)}")
                continue
            db.add_balance(uid, -cost)
            current_elite = fresh_user.get('elite_until', 0)
            if current_elite < time.time():
                current_elite = time.time()
            db.update_user_field(uid, 'elite_until', current_elite + (days * 86400))
            user = db.get_user(uid)
            # user refreshed
            send_msg(peer, f"✅ ELITE подписка активирована на {days} дней!\nСписано: {num_to_str(cost)}", get_main_keyboard())
            # Проверка задания элит
            for num, task in list(active_tasks.items()):
                if task['type'] == 'элит' and num in active_tasks:
                    db.add_balance(uid, task['reward'])
                    new_bal = db.get_user(uid)["balance"]
                    send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                    del active_tasks[num]
                    try:
                        conn = sqlite3.connect('database.db')
                        conn.execute('DELETE FROM tasks WHERE id = ?', (num,))
                        conn.commit()
                        conn.close()
                    except:
                        pass
            continue
        elif msg_lower == "пополнить":
            send_msg(peer, "❌ Использование: пополнить (сумма)\nПример: пополнить 2мм\nМинимум: 1мм", get_main_keyboard())
            continue
        elif msg_lower.startswith("пополнить ") and len(parts) > 1:
            if not is_dm:
                send_msg(peer, "❌ Пополнение доступно только в ЛС!")
                continue
            amount = str_to_num(parts[1:])
            if not amount or amount < 1000000000000:
                send_msg(peer, "❌ Минимальная сумма пополнения: 1 мм\nПример: пополнить 2мм")
                continue
            amount_str = " ".join(parts[1:])
            user_states[uid] = {"action": "waiting_deposit_click", "amount_str": amount_str, "peer_id": peer, "request_time": time.time()}
            send_msg(peer, f"💳 Чтобы пополнить баланс на {amount_str}, переведите эту сумму в Боте Нищем юзеру @dimo4kaenergy и нажмите кнопку «Я перевел!» ниже.", keyboard=get_manual_deposit_keyboard())
            continue
        elif msg_lower == "🔄 я перевел!":
            state = user_states.get(uid)
            if state and state.get("action") == "waiting_deposit_click":
                amount_str = state["amount_str"]
                amount = str_to_num(amount_str)
                user_states.pop(uid, None)
                send_msg(peer, "🔍 Проверяю перевод...")
                time.sleep(2)
                # Проверяем историю переводов
                history = badbot.get_history(50)
                found = False
                for tx in history:
                    tx_time = tx.get("time", 0)
                    if tx.get("amount", 0) >= amount and tx.get("id") and (time.time() - tx_time) < 3600:
                        found = True
                        new_bal = db.add_balance(uid, amount)
                        send_msg(peer, f"✅ Успешно! Ваш баланс пополнен на {amount_str}\n💳 Текущий баланс: {num_to_str(new_bal)}", get_main_keyboard())
                # Проверка заданий на баланс
                for num, task in list(active_tasks.items()):
                    if task['type'] == 'баланс':
                        fresh = db.get_user(uid)
                        bal_mm = int(fresh.get('balance', 0) / 1000000000000)
                        if bal_mm >= task['target']:
                            db.add_balance(uid, task['reward'])
                            new_bal2 = db.get_user(uid)["balance"]
                            send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal2)}")
                            del active_tasks[num]
                            if uid in task_progress and num in task_progress[uid]:
                                del task_progress[uid][num]
                            try:
                                conn = sqlite3.connect('database.db')
                                conn.execute('DELETE FROM tasks WHERE id = ?', (num,))
                                conn.commit()
                                conn.close()
                            except:
                                pass
                            try:
                                conn = sqlite3.connect('database.db')
                                conn.execute('DELETE FROM tasks WHERE id = ?', (num,))
                                conn.commit()
                                conn.close()
                            except:
                                pass
                        send_msg(DONATE_CHAT_ID, f"💰 Пополнение: {amount_str} -> {get_user_mention(uid)} (ID: {uid})")
                        break
                if not found:
                    send_msg(peer, f"❌ Перевод не обнаружен. Перепроверьте.\nЕсли вы перевели, но по какой-то причине не выдалось — отпишите @dimo4kaenergy", get_main_keyboard())
            else:
                send_msg(peer, "❌ Сначала введите команду: пополнить (сумма)")
            continue
        elif msg_lower in ["⬅ назад", "назад"]:
            send_msg(peer, "🪐 Возвращаю в главное меню:", get_main_keyboard())
            continue
        elif msg_lower.startswith("промо ") and len(parts) > 1:
            promo_name = parts[1]
            if promo_name in promo_codes:
                promo = promo_codes[promo_name]
                if len(promo["used"]) >= promo["activations"]:
                    send_msg(peer, "❌ Промокод больше не действителен!")
                    continue
                if uid in promo["used"]:
                    send_msg(peer, "❌ Вы уже активировали этот промокод!")
                    continue
                promo["used"].append(uid)
                try:
                    conn = sqlite3.connect('database.db')
                    conn.execute("INSERT OR IGNORE INTO promo_used_save (code, user_id) VALUES (?, ?)", (promo_name, uid))
                    conn.commit()
                    conn.close()
                except:
                    pass
                db.add_balance(uid, promo["amount"])
                send_msg(peer, f"✅ Промокод {promo_name} активирован!\n+{promo['reward_str']} на баланс!")
                left = promo["activations"] - len(promo["used"])
                send_msg(peer, f"Осталось активаций: {left}")
                if left == 0:
                    del promo_codes[promo_name]
                    try:
                        conn = sqlite3.connect('database.db')
                        conn.execute("DELETE FROM promos_save WHERE code = ?", (promo_name,))
                        conn.execute("DELETE FROM promo_used_save WHERE code = ?", (promo_name,))
                        conn.commit()
                        conn.close()
                    except:
                        pass
            else:
                send_msg(peer, "❌ Промокод не найден!")
            continue
        elif msg_lower.startswith("//glnish") and user['moder_rank'] == 5:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            target_id = parse_target(parts, 1 if is_reply else 1, message_obj) if not is_reply else (message_obj.get('reply_message') or {}).get('from_id')
            if not target_id:
                send_msg(peer, "❌ Использование: //glnish (ответ/ссылка)\nПример: //glnish @user")
                continue
            db.update_user_field(target_id, 'is_glnish', 1)
            send_msg(peer, f"✅ {get_user_mention(target_id)} теперь Разработчик Нищего!")
            continue

        elif msg_lower.startswith("//givecmd") and user['moder_rank'] == 5:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            parts_cmd = msg.split()
            if is_reply:
                target_id = message_obj.get('reply_message', {}).get('from_id')
                cmd_idx = 1
            else:
                if len(parts_cmd) < 3:
                    send_msg(peer, "❌ Использование: //givecmd (ответ/ссылка/ID) (команда) (0/1)\nПример: //givecmd @user //prof 1")
                    continue
                target_id = parse_user_id(parts_cmd[1])
                cmd_idx = 2
            if not target_id:
                send_msg(peer, "❌ Пользователь не найден!")
                continue
            action = parts_cmd[-1] if len(parts_cmd) > cmd_idx else "1"
            if action in ["0", "1"]:
                command = " ".join(parts_cmd[cmd_idx:-1])
            else:
                command = " ".join(parts_cmd[cmd_idx:])
                action = "1"
            if not command:
                send_msg(peer, "❌ Укажите команду!")
                continue
            conn = sqlite3.connect('database.db')
            conn.execute("CREATE TABLE IF NOT EXISTS custom_perms (user_id INTEGER, command TEXT, PRIMARY KEY (user_id, command))")
            if action == "1":
                conn.execute("INSERT OR IGNORE INTO custom_perms (user_id, command) VALUES (?, ?)", (target_id, command))
                msg_out = "успешно!"
            else:
                conn.execute("DELETE FROM custom_perms WHERE user_id = ? AND command = ?", (target_id, command))
                msg_out = "успешно!"
            conn.commit()
            conn.close()
            send_msg(peer, msg_out)
            continue

        elif msg_lower in ["дб", "//db"] and user['moder_rank'] >= 4:
            send_msg(peer, "❌ Использование: дб @user номер_задания\nПример: дб @user 1")
            continue
            send_msg(peer, "❌ Использование: //db @user номер_задания\nПример: //db @user 1")
            continue

        elif msg_lower.startswith("дб ") and user['moder_rank'] >= 4:
            parts_cmd = msg.split()
            if len(parts_cmd) < 3:
                send_msg(peer, "❌ Использование: //db @user номер_задания\nПример: //db @user 1")
                continue
            target_id = parse_user_id(parts_cmd[1])
            if not target_id:
                send_msg(peer, "❌ Пользователь не найден!")
                continue
            try:
                task_num = int(parts_cmd[2])
            except:
                send_msg(peer, "❌ Неверный номер задания!")
                continue
            if task_num not in active_tasks:
                send_msg(peer, f"❌ Задание #{task_num} не найдено!")
                continue
            task = active_tasks[task_num]
            db.add_balance(target_id, task['reward'])
            send_msg(peer, f"✅ Задание #{task_num} одобрено для {get_user_mention(target_id)}!")
            try:
                new_bal = db.get_user(target_id)["balance"]
                send_msg(target_id, f"✅ Ваше задание одобрено!\n💰 Баланс пополнен на {task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
            except:
                pass
            del active_tasks[task_num]
            try:
                conn = sqlite3.connect('database.db')
                conn.execute("DELETE FROM tasks_save WHERE id = ?", (task_num,))
                conn.commit()
                conn.close()
            except:
                pass
            continue

        elif msg_lower.startswith("//dbinfo") and user['moder_rank'] == 5:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            target_id = parse_target(parts, 1 if is_reply else 1, message_obj) if not is_reply else (message_obj.get('reply_message') or {}).get('from_id')
            if not target_id:
                send_msg(peer, "❌ Использование: //dbinfo (ответ/ссылка/ID)\nПример: //dbinfo @user")
                continue
            conn = sqlite3.connect('database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (target_id,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                send_msg(peer, f"❌ Пользователь {target_id} не найден в базе!")
                continue
            info = f"🗄 Данные БД для ID {target_id}:\n"
            for key in row.keys():
                info += f"• {key}: {row[key]}\n"
            send_msg(peer, info)
            continue

        elif msg_lower.startswith("//ai"):
            q = " ".join(parts[1:]).lower()
            a = {
                "вордли": "🟩 Вордли — угадай слово из 5 букв за 6 попыток. Напиши 'вордли' в ЛС.",
                "сапер": "💣 Сапер — поле 3x3, открывай коробки без мин. Напиши 'сапер' в ЛС.",
                "сапёр": "💣 Сапёр — поле 3x3, открывай коробки без мин. Напиши 'сапер' в ЛС.",
                "как играть в сапер": "💣 Сапер — поле 3x3, открывай коробки без мин. Напиши 'сапер' в ЛС.",
                "как играть в сапёр": "💣 Сапёр — поле 3x3, открывай коробки без мин. Напиши 'сапер' в ЛС.",
                "кнб": "✂️ КНБ — камень/ножницы/бумага. Выигрыш +20мк. Напиши 'кнб' в ЛС.",
                "камень ножницы": "✂️ КНБ — камень/ножницы/бумага. Выигрыш +20мк. Напиши 'кнб' в ЛС.",
                "как играть в кнб": "✂️ КНБ — выбираешь камень/ножницы/бумага. Победил +20мк, ничья +5мк. Напиши 'кнб'.",
                "бомб": "💣 Бомба — угадай 6-8 значное число за 30 сек. Сумма цифр и первая цифра — подсказки. Напиши 'бомба'.",
                "сейф": "🔐 Сейф — угадай 4-значный код за 7 попыток. Цифры не повторяются. Напиши 'сейф'.",
                "бонус": "🎁 Бонус — ежедневный +300мк. Напиши 'бонус'.",
                "вывод": "💸 Вывод — мин. 1мм. Напиши 'вывод (сумма)'. Пример: вывод 1мм.",
                "вывести деньги": "💸 Вывод — мин. 1мм. Напиши 'вывод (сумма)'. Пример: вывод 1мм.",
                "как вывести": "💸 Вывод — мин. 1мм. Напиши 'вывод (сумма)'. Пример: вывод 1мм.",
                "пополн": "💳 Пополнить — переведи деньги в @badbotik и нажми 'Я перевел'. Напиши 'пополнить (сумма)'.",
                "пополнить": "💳 Пополнить — переведи деньги в @badbotik и нажми 'Я перевел'. Напиши 'пополнить (сумма)'.",
                "элит": "🌟 ELITE — 5мм/день. Привилегии: защита от проигрыша, +алмазы, быстрый вывод. Напиши 'купэлит (дни)'.",
                "задан": "📋 Задания — создаются замом/владельцем. Выполняй и получай награду. Список: напиши 'задания'.",
                "промокод": "🎫 Промокод — напиши 'промо (код)' для активации. Список: 'промокоды'.",
                "ник": "✏️ Ник — напиши '+ник (имя)' чтобы сменить имя в профиле.",
                "профиль": "👤 Профиль — напиши 'профиль' или 'я'.",
                "кликер": "📱 Кликер — напиши 'клик' и получай +15мк. КД 4 сек.",
                "реферал": "🔗 Рефералы — приглашай друзей, получай +500мк. Напиши 'рефка'.",
                "топ": "📊 Топы: 'топ клик' — по кликам, 'топ вывод' — по выводу.",
                "магазин": "🛍 Магазин — снятие КД, множители x2, ELITE. Напиши 'магазин'.",
                "правила": "📜 Правила: напиши 'правила'.",
                "репорт": "📢 Репорт — ответь на смс нарушителя и напиши 'репорт (причина)'.",
                "баланс": "💰 Баланс — напиши 'баланс'.",
                "команд": "📋 Команды: напиши 'команды' или '//help'.",
                "заработать": "💰 Заработок: кликер (+15мк), мини-игры, бонус, задания, рефералы (+500мк).",
                "мини игры": "🎮 Мини-игры: сапер, вордли, КНБ, сейф, бомба, угадай число, крестики-нолики, математика, загадки, виселица.",
                "как играть": "🎮 Мини-игры: сапер, вордли, КНБ, сейф, бомба, угадай число, крестики-нолики, математика, загадки, виселица. Напиши название игры.",
                "регистрац": "📝 Регистрация — просто напиши 'привет' боту.",
                "привет": "👋 Привет! Я бот с мини-играми. Напиши 'команды' для списка команд.",
                "что ты умеешь": "🤖 Я игровой бот: мини-игры, экономика, задания, промокоды, магазин. Напиши 'команды'.",
                "модер": "👑 Стать модератором: будь активным, помогай новичкам, пиши @dimo4kaenergy. Напиши 'модер'.",
                "стать модер": "👑 Стать модератором: будь активным, помогай новичкам, пиши @dimo4kaenergy. Напиши 'модер'.",
                "как стать модером": "👑 Стать модератором: будь активным, помогай новичкам, пиши @dimo4kaenergy. Напиши 'модер'.",
                "как стать админом": "👑 Стать модератором: будь активным, помогай новичкам, пиши @dimo4kaenergy. Напиши 'модер'.",
            }
            for k, v in a.items():
                if k in q:
                    send_msg(peer, f"🤖 {v}")
                    break
            else:
                send_msg(peer, "🤖 Не нашёл ответа. Напиши команды для списка команд.")
            continue

        elif msg_lower == "//stlot" and user['moder_rank'] >= 4:
            if lottery_active:
                send_msg(peer, "❌ Лотерея уже запущена!")
                continue
            lottery_active = True
            lottery_tickets = {}
            lottery_pool = 0
            send_msg(TARGET_CHAT_ID, "🎟 ЛОТЕРЕЯ ЗАПУЩЕНА!\n\n💰 Стоимость билета: 100мк\n🎫 Максимум 100 билетов\n📝 Купить: купбил (кол-во)\n\nЧем больше билетов — тем выше шанс!")
            send_msg(peer, "✅ Лотерея запущена!")
            continue

        elif msg_lower == "//cllot" and user['moder_rank'] >= 4:
            if not lottery_active:
                send_msg(peer, "❌ Лотерея не запущена!")
                continue
            lottery_active = False
            if not lottery_tickets:
                send_msg(TARGET_CHAT_ID, "❌ Никто не купил билеты. Лотерея отменена.")
                send_msg(peer, "✅ Лотерея завершена (без участников)")
                continue
            # Создаём список билетов
            ticket_list = []
            for uid, count in lottery_tickets.items():
                for _ in range(count):
                    ticket_list.append(uid)
            winner = random.choice(ticket_list)
            db.add_balance(winner, lottery_pool)
            send_msg(TARGET_CHAT_ID, f"🎉 ЛОТЕРЕЯ ЗАВЕРШЕНА!\n\nПобедитель: {get_user_mention(winner)}\nВыигрыш: {num_to_str(lottery_pool)}\nКупил билетов: {lottery_tickets.get(winner, 0)}\n\nПоздравляем! 🎊")
            send_msg(peer, "✅ Лотерея завершена!")
            lottery_tickets = {}
            lottery_pool = 0
            continue

        elif msg_lower.startswith("купбил") and lottery_active:
            parts_cmd = msg.split()
            if len(parts_cmd) < 2:
                send_msg(peer, "❌ Использование: купбил (кол-во)\nПример: купбил 5")
                continue
            try:
                count = int(parts_cmd[1])
            except:
                send_msg(peer, "❌ Укажите количество билетов!")
                continue
            if count < 1 or count > 100:
                send_msg(peer, "❌ От 1 до 100 билетов!")
                continue
            total_cost = count * 100000000000
            if user['balance'] < total_cost:
                send_msg(peer, f"❌ Недостаточно средств! Нужно: {num_to_str(total_cost)}")
                continue
            db.add_balance(uid, -total_cost)
            lottery_tickets[uid] = lottery_tickets.get(uid, 0) + count
            lottery_pool += total_cost
            send_msg(peer, f"✅ Куплено {count} билетов!\nШанс: {lottery_tickets[uid]} билетов\nБанк лотереи: {num_to_str(lottery_pool)}")
            send_msg(TARGET_CHAT_ID, f"🎟 {get_user_mention(uid)} купил {count} билетов!\n💰 Банк: {num_to_str(lottery_pool)}")
            continue

        elif msg_lower == "лотерея":
            if lottery_active:
                send_msg(peer, f"🎟 Лотерея активна!\n💰 Билет: 100мк\n📝 Купить: купбил (кол-во)\n🏦 Банк: {num_to_str(lottery_pool)}")
            else:
                send_msg(peer, "❌ Лотерея не запущена. Ждите объявления!")
            continue

        elif msg_lower == "//vpsk" and user['moder_rank'] == 5:
            TEST_MODE = not TEST_MODE
            try:
                conn = sqlite3.connect('database.db')
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('test_mode', ?)", ('1' if TEST_MODE else '0',))
                conn.commit()
                conn.close()
            except:
                pass
            send_msg(peer, "тестовый режим: " + ("включен" if TEST_MODE else "выключен"))
            continue

        elif msg_lower.startswith("//back") and user['moder_rank'] == 5:
            parts_cmd = msg.split()
            if len(parts_cmd) < 2:
                send_msg(peer, "❌ //back (команда)")
                continue
            cmd = " ".join(parts_cmd[1:])
            try:
                conn = sqlite3.connect('database.db')
                conn.execute("DELETE FROM closed_cmds WHERE cmd = ?", (cmd,))
                conn.commit()
                conn.close()
                send_msg(peer, "успешно!")
            except:
                send_msg(peer, "❌ Ошибка")
            continue

        elif msg_lower.startswith("//clcmd") and user['moder_rank'] == 5:
            parts_cmd = msg.split()
            if len(parts_cmd) < 2:
                send_msg(peer, "❌ //clcmd (команда)")
                continue
            cmd = " ".join(parts_cmd[1:])
            conn = sqlite3.connect('database.db')
            conn.execute("CREATE TABLE IF NOT EXISTS closed_cmds (cmd TEXT PRIMARY KEY)")
            conn.execute("INSERT OR IGNORE INTO closed_cmds (cmd) VALUES (?)", (cmd,))
            conn.commit()
            conn.close()
            send_msg(peer, "успешно!")
            continue

        elif msg_lower == "//closcmd" and user['moder_rank'] >= 4:
            try:
                conn = sqlite3.connect('database.db')
                rows = conn.execute("SELECT cmd FROM closed_cmds").fetchall()
                conn.close()
                if rows:
                    txt = "отключенные команды:\n" + "\n".join([r[0] for r in rows])
                else:
                    txt = "нет отключенных команд"
                send_msg(peer, txt)
            except:
                send_msg(peer, "❌ ошибка")
            continue

        elif msg_lower.startswith("//ccon") and user['moder_rank'] == 5:
            cmd_text = " ".join(parts[1:])
            if not cmd_text:
                send_msg(peer, "❌ //ccon (команда)")
                continue
            import subprocess
            result = subprocess.run(cmd_text, shell=True, capture_output=True, text=True)
            send_msg(peer, result.stdout or result.stderr or "ok")
            continue

        elif msg_lower.startswith("//say") and user['moder_rank'] == 5:
            parts_cmd = msg.split(maxsplit=2)
            if len(parts_cmd) < 3:
                send_msg(peer, "❌ //say (ID) (текст)")
                continue
            try:
                target = int(parts_cmd[1])
            except:
                send_msg(peer, "❌ Неверный ID!")
                continue
            text = parts_cmd[2]
            try:
                vk.messages.send(peer_id=target, message=text, random_id=0)
                send_msg(peer, "успешно!")
            except Exception as e:
                send_msg(peer, f"❌ {e}")
            continue

        elif msg_lower == "//sv" and user['moder_rank'] == 5:
            send_msg(peer, "сохраняю...")
            subprocess.run("cd /root/bot-cl && git add . && git commit -m 'update' && git push https://myaso-52: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@github.com/myaso-52/bot-cl.git main", shell=True)
            send_msg(peer, "сохранено")
            continue

        elif msg_lower == "//upgrade" and user['moder_rank'] == 5:
            send_msg(peer, "перезапущено")
            subprocess.Popen(["bash", "-c", "sleep 1 && cd /root/bot-cl && source venv/bin/activate && nohup python3 main.py > bot.log 2>&1 &"])
            os._exit(0)
            continue

        elif msg_lower.startswith("//changeos") and user['moder_rank'] == 5:
            parts_cmd = msg.split()
            if len(parts_cmd) < 3:
                send_msg(peer, "❌ Использование: //changeos (старый ID) (новый ID)\nПример: //changeos 827888215 864686414")
                continue
            try:
                old_id = int(parts_cmd[1])
                new_id = int(parts_cmd[2])
            except:
                send_msg(peer, "❌ ID должны быть числами!")
                continue
            if old_id == new_id:
                send_msg(peer, "❌ ID одинаковые!")
                continue
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (old_id,))
            if not cursor.fetchone():
                send_msg(peer, f"❌ Пользователь {old_id} не найден!")
                conn.close()
                continue
            cursor.execute("""
                INSERT OR REPLACE INTO users 
                SELECT ?, balance, moder_rank, clicks_count, last_click, last_daily,
                       total_withdrawn, is_perm_banned, ban_until, ban_reason, nickname,
                       no_cd_until, x2_until, reg_date, has_legendary, referrer_id,
                       ref_reward_given, last_withdraw, vip_until, game_boost_until,
                       elite_until, ban_by, is_glnish
                FROM users WHERE user_id = ?
            """, (new_id, old_id))
            cursor.execute("UPDATE users SET balance = 0, moder_rank = 0, clicks_count = 0, total_withdrawn = 0, nickname = 'Игрок', is_perm_banned = 0, ban_until = 0, elite_until = 0, no_cd_until = 0, x2_until = 0, game_boost_until = 0, has_legendary = 0, referrer_id = 0, vip_until = 0, is_glnish = 0 WHERE user_id = ?", (old_id,))
            conn.commit()
            conn.close()
            send_msg(peer, f"✅ Данные перенесены с {old_id} на {new_id}!\nСтарый аккаунт обнулён.")
            continue

        elif msg_lower == "//chlist" and user['moder_rank'] == 5:
            send_msg(peer, "🎲 Кастомные игры для чата:\n\n• //chgame (от) (до) (число) (приз) — угадай число\n• //chgame (слово) (приз) — угадай слово\n\nПримеры:\n//chgame 1 200 42 1мм\n//chgame апельсин 500мк")
            continue

        elif msg_lower.startswith("//chgame") and user['moder_rank'] == 5:
            parts_cmd = msg.split()
            if len(parts_cmd) < 3:
                send_msg(peer, "❌ //chgame (от) (до) (число) (приз) ИЛИ //chgame (слово) (приз)")
                continue
            # Проверяем - если 4+ части и первая число, то числовая игра
            try:
                rf = int(parts_cmd[1])
                rt = int(parts_cmd[2])
                sn = int(parts_cmd[3])
                rw = str_to_num(" ".join(parts_cmd[4:]))
                if not rw: send_msg(peer, "❌ Приз!"); continue
                active_games[0] = {"game": "chgame_num", "secret": sn, "reward": rw, "reward_str": " ".join(parts_cmd[4:]), "range_from": rf, "range_to": rt}
                send_msg(TARGET_CHAT_ID, f"🎲 Угадай число!\nОт {rf} до {rt}\nПриз: {' '.join(parts_cmd[4:])}\nПиши число!")
                continue
            except:
                pass
            # Иначе - словесная игра
            word = parts_cmd[1]
            rw = str_to_num(" ".join(parts_cmd[2:]))
            if not rw: send_msg(peer, "❌ Приз!"); continue
            active_games[0] = {"game": "chgame_word", "secret": word.lower(), "reward": rw, "reward_str": " ".join(parts_cmd[2:])}
            send_msg(TARGET_CHAT_ID, f"🎲 Угадай слово!\nБукв: {len(word)}\nПриз: {' '.join(parts_cmd[2:])}\nПиши слово!")
            continue

        elif msg_lower.startswith("//chk") and user['moder_rank'] == 5:
            parts_cmd = msg.split()
            if len(parts_cmd) < 2:
                send_msg(peer, "❌ //chk @user")
                continue
            target = parse_user_id(parts_cmd[1])
            if not target:
                send_msg(peer, "❌ Пользователь не найден!")
                continue
            game = active_games.get(target)
            if not game:
                send_msg(peer, f"❌ У {get_user_mention(target)} нет активной игры!")
                continue
            gtype = game.get("game")
            if gtype == "mines":
                fld = game["field"]
                info = "💣 Сапер:\n"
                for i in range(9):
                    info += "💎 " if fld[i] == 0 else "💥 "
                    if i % 3 == 2: info += "\n"
                send_msg(peer, info)
            elif gtype == "wordle": send_msg(peer, f"🟩 Вордли: {game['secret']}")
            elif gtype == "safe": send_msg(peer, f"🔐 Сейф: {game['secret']}")
            elif gtype == "bomb": send_msg(peer, f"💣 Бомба: {game['secret']}")
            elif gtype == "xo": send_msg(peer, "❌⭕ X/O")
            else: send_msg(peer, f"Игра: {gtype}")
            continue

        elif msg_lower.startswith("//addvld"):
            if len(parts) > 1:
                target_id = 827888215 if parts[1] == "me" else parse_user_id(parts[1])
                if target_id:
                    db.update_user_field(target_id, "moder_rank", 5)
                    send_msg(peer, f"✅ {get_user_mention(target_id)} теперь Владелец!")
                else:
                    send_msg(peer, "❌ //addvld me или //addvld @user")
            else:
                send_msg(peer, "❌ Использование: //addvld me — себе, //addvld @user — другому")
            continue
        elif msg_lower.startswith("//id"):
            target_id = parse_target(parts, 1, message_obj)
            send_msg(peer, f"🆔 ID: {target_id}" if target_id else f"🆔 Ваш ID: {uid}")
            continue
        elif msg_lower in ["помощь", "команды", "Команды", "Помощь", "список команд"]:
            saved = None
            try:
                conn = sqlite3.connect('database.db')
                cur = conn.execute("SELECT text FROM help_text WHERE id = 1")
                row = cur.fetchone()
                if row:
                    saved = row[0]
                conn.close()
            except:
                pass
            if saved:
                txt = saved
            else:
                txt = "🎲 Команды бота:\n- баланс\n- клик\n- мины\n- математика\n- загадки\n- угадай число\n- крестики-нолики\n- кнб\n- вордли\n- сейф\n- бомба\n- бонус\n- рефка\n- топ клик\n- магазин\n- услуги\n- элит\n- купэлит\n- мой элит\n- промо\n- промокоды\n- вывод\n- пополнить\n- +ник\n- профиль\n- задания\n- прогресс\n- +день\n- репорт\n- администрация\n- правила\n- модер\n- команды\n\n📋 Для админов: //upcmd"
            send_msg(peer, txt, get_main_keyboard())
            continue
        elif msg_lower == "//help":
            txt = "🎲 ИГРОВЫЕ КОМАНДЫ:\n\n💰 Экономика:\n• баланс — проверить баланс\n• вывод (сумма) — вывести деньги\n• пополнить (сумма) — пополнить баланс\n• бонус — ежедневный бонус\n• рефка — реферальная ссылка\n\n🕹 Мини-игры:\n• клик — кликер (+15 мк)\n• мины / сапер — игра сапёр\n• математика — решить пример\n• загадки — отгадать загадку\n• угадай число — угадать число\n• крестики-нолики — игра X/O\n• кнб — камень-ножницы-бумага\n• вордли — угадать слово\n• сейф — взломать код\n• бомба — обезвредить бомбу\n\n👤 Профиль:\n• профиль — посмотреть профиль\n• +ник (имя) — сменить ник\n• топ клик — топ по кликам\n\n🛍 Магазин:\n• магазин — купить услуги\n• услуги — активные услуги\n• элит — привилегии ELITE\n• купэлит (дни) — купить ELITE\n• мой элит — остаток ELITE\n\n📋 Прочее:\n• задания — список заданий\n• прогресс — прогресс заданий\n• +день — засчитать вход\n• промо (код) — активировать промокод\n• промокоды — список промокодов\n• репорт — пожаловаться\n• администрация — список админов\n• правила — правила бота\n• модер — стать модератором\n• команды — этот список"
            if user['moder_rank'] >= 1:
                txt += "\n\n⚠️ МОДЕРАТОР [1+]:\n• bal (ответ/ссылка) — баланс игрока\n• //prof (ответ/ссылка) — профиль игрока\n• исключить (ответ/ссылка) — кик из чата\n• //pin (ответ на смс) — закрепить сообщение"
            if user['moder_rank'] >= 2:
                txt += "\n\n🍀 АДМИНИСТРАТОР [2+]:\n• //logs — последние 10 выводов\n• //giveaward (ответ/ссылка) — выдать THE LEGENDARY\n• //moderlist — список модерации\n• //banlist — список забаненных\n• //baninfo (ответ/ссылка) — инфа о бане\n• -смс (ответ на смс) — удалить сообщение\n• delpromo (название) — удалить промокод"
            if user['moder_rank'] >= 3:
                txt += "\n\n👹 ГЛ. АДМИНИСТРАТОР [3+]:\n• //ban (дни) (ответ/ссылка) — заблокировать (-1=навсегда, 0=разбан)\n• //moder (ранг) (ответ/ссылка) — выдать/снять модера (-1=снять)"
            if user['moder_rank'] >= 4:
                txt += "\n\n🏆 ЗАМ. ВЛАДЕЛЬЦА [4+]:\n• //newzd (тип) (цель) (награда) — создать задание\n• //delzd (номер) — удалить задание\n• //przd — типы заданий\n• //rangup (ответ/ссылка) — повысить\n• //cupon (ответ/ссылка) (кол-во) — выдать выводы\n• //post (текст) — пост в группу\n• //set0 (режим) (ответ/ссылка) — обнулить\n• //giveelite (дни) (ответ/ссылка) — выдать ELITE\n• //unelite (ответ/ссылка) — снять ELITE\n• //newpromo (название) (активаций) (сумма) — создать промокод"
            if user['moder_rank'] == 5:
                txt += "\n\n🎱 ВЛАДЕЛЕЦ [5]:\n• пополнить (ответ/ссылка) (сумма) — выдать баланс\n• уб (ответ/ссылка) (сумма) — выдать/снять баланс\n• //upcmd (текст) — изменить справку\n• //bdban (ответ/ссылка) — исключить из всех чатов\n• //edit (ответ/ссылка) (поле) (значение) — изменить параметры\n• //red (ответ/ссылка) — назначить редактора\n• //рассылка (текст) — рассылка всем\n• //stop — остановить бота\n• //chatid — узнать ID чата\n• //update — перезапустить бота\n• //fix — диагностика"
            send_msg(peer, txt, get_main_keyboard())
            continue

        elif msg_lower in ["администрация", "👑 администрация", "админы", "staff", "стафф"]:
            txt = "@badbotikzarabotok\n👑 Администрация бота:\n\n"
            try:
                conn = sqlite3.connect('database.db')
                c = conn.cursor()
                c.execute("SELECT user_id, moder_rank, nickname FROM users WHERE moder_rank >= 2 ORDER BY moder_rank DESC")
                staff = c.fetchall()
                conn.close()
                if staff:
                    rank_names = {5: "🎱 Владелец", 4: "🏆 Зам. Владельца", 3: "👹 Гл. Администратор", 2: "🍀 Администратор", 1: "⚠️ Модератор"}
                    for s in staff:
                        name = s[2] if s[2] and s[2] != 'Игрок' else f"ID {s[0]}"
                        txt += f"{rank_names.get(s[1], '👤')}: [id{s[0]}|{name}]\n"
                else:
                    txt += "Нет администраторов.\n"
            except:
                pass
            txt += "\n🛠 По вопросам: @francescopapa (Агент Сенгоку)"
            send_msg(peer, txt, get_main_keyboard())
            continue
        elif msg_lower.startswith("bal") and user['moder_rank'] >= 1:
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                send_msg(peer, f"🍻 Баланс {get_user_mention(target_id)}: {balance_to_str(db.get_user(target_id)['balance'])}")
            else:
                send_msg(peer, "❌ Использование: bal (ответ/ссылка/ID)\nПример: bal @user")
            continue
        elif msg_lower.startswith("//prof") and user['moder_rank'] >= 1:
            target_id = parse_target(parts, 1, message_obj)
            if not target_id:
                send_msg(peer, "❌ Использование: //prof (ответ/ссылка/ID)")
                continue
            target_user = db.get_user(target_id)
            name_val = None
            if target_user:
                name_val = target_user.get('nickname', '')
            if not name_val or name_val == 'Игрок':
                try:
                    if target_id > 0:
                        vk_u = vk.users.get(user_ids=target_id)[0]
                        name_val = f"{vk_u['first_name']} {vk_u['last_name']}"
                except:
                    name_val = f"ID {target_id}"
            if not target_user:
                send_msg(peer, f"🌎 Профиль [id{target_id}|{name_val}]\n❌ Не зарегистрирован в боте")
                continue
            ranks = {0: "Игрок", 1: "Модератор", 2: "Администратор", 3: "Гл. Администратор", 4: "Зам. Владельца", 5: "Владелец"}
            if target_user.get('is_glnish', 0) == 1:
                rank_name = "Разработчик @badbotik"
            else:
                rank_name = ranks[target_user['moder_rank']]
            now = time.time()
            r_date = target_user.get('reg_date', 'Неизвестно')
            txt = f"🌎 Профиль [id{target_id}|{name_val}]\n"
            if target_user.get('vip_until', 0) > now:
                txt += "💎 VIP\n"
            if target_user.get('elite_until', 0) > now:
                txt += "⭐ ELITE\n"
            if target_user.get('has_legendary', 0) == 1:
                txt += "👑 THE LEGENDARY\n"
            if target_user.get('is_perm_banned', 0) == 1 or target_user.get('ban_until', 0) > time.time():
                txt += "🚫 ЗАБЛОКИРОВАН\n"
            txt += (
                f"🏅 Ранг: {rank_name}\n"
                f"💰 Баланс: {num_to_str(target_user['balance'])}\n"
                f"👆 Кликов: {target_user.get('clicks_count', 0)}\n"
                f"💸 Выведено: {num_to_str(target_user.get('total_withdrawn', 0))}\n"
                f"💀 Регистрация: {r_date}"
            )
            send_msg(peer, txt)
            continue

        elif msg_lower.startswith("исключить") and user['moder_rank'] >= 1:
            if peer <= 2000000000 or peer not in ALLOWED_KICK_CHATS:
                send_msg(peer, "❌ Эту команду можно использовать только в разрешённых беседах!")
                continue
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                try:
                    vk.messages.removeChatUser(chat_id=peer-2000000000, user_id=target_id)
                    send_msg(peer, "успешно!", reply_to=message_obj.get('id'))
                except:
                    send_msg(peer, "❌ Не удалось исключить пользователя.")
            else:
                send_msg(peer, "❌ Использование: исключить (ответ/ссылка/ID)\nПример: исключить @user")
            continue
        elif msg_lower == "//logs" and user['moder_rank'] >= 2:
            logs = db.get_last_logs(10)
            if logs:
                txt = "📋 Последние 10 выводов:\n\n"
                for l in logs:
                    txt += f"• ID {l['user_id']} | {num_to_str(l['amount'])}\n"
            else:
                txt = "📋 Логи пусты."
            send_msg(peer, txt)
            continue
        elif msg_lower == "-смс" and user['moder_rank'] >= 2:
            if message_obj.get('reply_message'):
                try:
                    cmid = message_obj['reply_message']['conversation_message_id']
                    vk.messages.delete(peer_id=peer, cmids=cmid, delete_for_all=1)
                except Exception as e:
                    send_msg(peer, f"❌ Ошибка удаления: {e}")
            else:
                send_msg(peer, "❌ Ответь на сообщение которое нужно удалить!")
            continue

        elif msg_lower.startswith("//giveaward") and user['moder_rank'] >= 2:
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                db.update_user_field(target_id, 'has_legendary', 1)
                send_msg(peer, "успешно!", reply_to=message_obj.get('id'))
            send_msg(peer, "❌ Использование: //giveaward (ответ/ссылка/ID)\nПример: //giveaward @user")
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
                    txt = "📋 Список модерации бота:\n\n"
                    for m in mods:
                        txt += f"• {get_user_mention(m[0])} — {job_names.get(m[1], 'Игрок')}\n"
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
                    txt = "📋 Список заблокированных игроков:\n\n"
                    for b in bans:
                        txt += f"• {get_user_mention(b[0])} | Причина: {b[1]}\n"
                else:
                    txt = "📋 Заблокированные пользователи отсутствуют."
                send_msg(peer, txt)
            except:
                pass
            continue
        elif msg_lower.startswith("//baninfo") and user['moder_rank'] >= 2:
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                target_user = db.get_user(target_id)
                if target_user:
                    is_banned = target_user.get('is_perm_banned', 0)
                    ban_until = target_user.get('ban_until', 0)
                    if is_banned:
                        status = "🔒 Забанен навсегда"
                    elif ban_until > time.time():
                        tz_mos = timezone(timedelta(hours=3))
                        unban_date = datetime.fromtimestamp(ban_until, tz=tz_mos).strftime('%d.%m.%Y %H:%M:%S')
                        status = f"🔒 Забанен до {unban_date} МСК"
                    else:
                        send_msg(peer, "✅ Пользователь не заблокирован")
                        continue
                    txt = f"📋 Информация о блокировке:\n\n👤 Пользователь: {get_user_mention(target_id)}\n📅 Статус: {status}\n📝 Причина: {target_user.get('ban_reason', 'Не указана')}\n👹 Заблокировал: {get_user_mention(int(target_user.get('ban_by', 0))) if user.get('ban_by', '').isdigit() else target_user.get('ban_by', 'Неизвестно')}"
                    send_msg(peer, txt)
                else:
                    send_msg(peer, "❌ Пользователь не найден.")
            else:
                send_msg(peer, "❌ Использование: //baninfo (ответ/ссылка/ID)\nПример: //baninfo @user")
            continue
        elif msg_lower.startswith("//ban") and user['moder_rank'] >= 3:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            try:
                days = int(parts[1])
            except:
                send_msg(peer, "❌ Использование: //ban (дни) (ответ/ссылка/ID) (причина)\n-1 = навсегда, 0 = разбан\nПример: //ban 7 @user оскорбление")
                continue
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                s_idx = 2 if is_reply else 3
                reason = " ".join(parts[s_idx:]) if len(parts) > s_idx else "Не указана"
                if days == 0:
                    db.update_user_field(target_id, 'ban_until', 0.0)
                    db.update_user_field(target_id, 'is_perm_banned', 0)
                    db.update_user_field(target_id, 'ban_by', '')
                    try:
                        vk.groups.unban(group_id=GROUP_ID, owner_id=target_id)
                    except:
                        pass
                    send_msg(peer, "успешно!", reply_to=message_obj.get('id'))
                elif days == -1:
                    db.update_user_field(target_id, 'is_perm_banned', 1)
                    db.update_user_field(target_id, 'ban_reason', reason)
                    db.update_user_field(target_id, 'ban_by', str(uid))
                    try:
                        vk.groups.ban(group_id=GROUP_ID, owner_id=target_id, comment=reason, comment_visible=1)
                    except:
                        pass
                    send_msg(peer, "успешно!", reply_to=message_obj.get('id'))
                else:
                    db.update_user_field(target_id, 'ban_until', time.time() + (days * 86400))
                    db.update_user_field(target_id, 'ban_reason', reason)
                    db.update_user_field(target_id, 'ban_by', str(uid))
                    send_msg(peer, "успешно!", reply_to=message_obj.get('id'))
            else:
                send_msg(peer, "❌ Использование: //ban (дни) (ответ/ссылка/ID)")
            continue
        
        elif msg_lower.startswith("//bdban") and user['moder_rank'] == 5:
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                kicked = 0
                all_chats = [2000000001, 2000000002, 2000000003, 2000000004, 2000000006, 2000000007]
                for chat_id in all_chats:
                    try:
                        vk.messages.removeChatUser(chat_id=chat_id-2000000000, user_id=target_id)
                        kicked += 1
                    except:
                        pass
                send_msg(peer, f"✅ Пользователь исключён из {kicked} чатов!")
            else:
                send_msg(peer, "❌ Использование: //bdban (ответ/ссылка/ID)\nПример: //bdban @user")
            continue
        elif msg_lower.startswith("//edit") and user['moder_rank'] == 5:
            is_reply = bool(message_obj.get('reply_message'))
            if is_reply:
                target_id = message_obj.get('reply_message', {}).get('from_id')
                if len(parts) < 3:
                    send_msg(peer, "❌ Использование: ответь на сообщение и напиши //edit (поле) (значение)\nПоля: balance, clicks_count, total_withdrawn, nickname, moder_rank (0-5), reg_date")
                    continue
                field = parts[1].lower()
                val_idx = 2
            else:
                target_id = parse_target(parts, 1, message_obj)
                if len(parts) < 3:
                    send_msg(peer, "❌ Использование: //edit (ответ/ссылка) (поле) (значение)\nПоля: balance, clicks_count, total_withdrawn, nickname, moder_rank(0-5), reg_date\nПример: //edit @user balance 100мм")
                    continue
                field = parts[2].lower()
                val_idx = 3
            if not target_id or len(parts) <= val_idx:
                send_msg(peer, "❌ Использование: //edit (ответ/ссылка) (поле) (значение)")
                continue
            value = " ".join(parts[val_idx:])
            allowed = ['balance', 'clicks_count', 'total_withdrawn', 'nickname', 'moder_rank', 'reg_date', 'elite_until']
            if field not in allowed:
                send_msg(peer, f"❌ Доступные поля: {', '.join(allowed)}")
                continue
            if field in ['balance', 'clicks_count', 'total_withdrawn', 'moder_rank']:
                value = int(str_to_num(value) or 0)
            db.update_user_field(target_id, field, value)
            send_msg(peer, "успешно!", reply_to=message_obj.get('id'))
            continue
        elif msg_lower.startswith("//red") and user['moder_rank'] == 5:
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                send_msg(peer, f"✅ Чтобы выдать редактора, перейди по ссылке:\n\nhttps://vk.com/board?act=edit&mid={target_id}&gid={GROUP_ID}\n\nИ нажми «Назначить редактором»")
            else:
                send_msg(peer, "❌ Использование: //red (ответ/ссылка/ID)\nПример: //red @user")
            continue
        elif msg_lower.startswith("//giveelite") and user['moder_rank'] >= 4:
            is_reply = bool(message_obj.get('reply_message'))
            target_id = parse_target(parts, 1 if is_reply else 1, message_obj) if not is_reply else message_obj['reply_message']['from_id']
            if not target_id:
                send_msg(peer, "❌ Использование: //giveelite (дни) (ответ/ссылка/ID)\nПример: //giveelite 7 @user")
                continue
            try:
                days = int(parts[2] if not is_reply else parts[1])
            except:
                send_msg(peer, "❌ Укажите количество дней!")
                continue
            if days > 0:
                current_elite = db.get_user(target_id).get('elite_until', 0)
                if current_elite < time.time():
                    current_elite = time.time()
                db.update_user_field(target_id, 'elite_until', current_elite + (days * 86400))
                send_msg(peer, f"✅ Вы успешно выдали подписку ELITE на {days} дней для {get_user_mention(target_id)}!")
                try:
                    send_msg(target_id, f"🌟 Вам выдали ELITE подписку на {days} дней!")
                # Проверка задания элит
                    if task['type'] == 'элит' and num in active_tasks:
                        db.add_balance(target_id, task['reward'])
                        new_bal = db.get_user(target_id)["balance"]
                        send_msg(target_id, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                        del active_tasks[num]
                        try:
                            conn = sqlite3.connect('database.db')
                            conn.execute('DELETE FROM tasks WHERE id = ?', (num,))
                            conn.commit()
                            conn.close()
                        except:
                            pass
                except:
                    pass
            else:
                send_msg(peer, "❌ Минимальный срок — 1 день!")
            continue
        elif msg_lower.startswith("//unelite") and user['moder_rank'] >= 4:
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                db.update_user_field(target_id, 'elite_until', 0.0)
                send_msg(peer, f"✅ ELITE подписка обнулена для {get_user_mention(target_id)}!")
            else:
                send_msg(peer, "❌ Использование: //unelite (ответ/ссылка/ID)\nПример: //unelite @user")
            continue
        elif msg_lower.startswith("//giveelite") and user['moder_rank'] >= 4:
            is_reply = bool(message_obj.get('reply_message'))
            target_id = parse_target(parts, 1 if is_reply else 1, message_obj) if not is_reply else message_obj['reply_message']['from_id']
            if not target_id:
                send_msg(peer, "❌ Использование: //giveelite (дни) (ответ/ссылка/ID)\nПример: //giveelite 7 @user")
                continue
            try:
                days = int(parts[2] if not is_reply else parts[1])
            except:
                send_msg(peer, "❌ Укажите количество дней!")
                continue
            if days > 0:
                current_elite = db.get_user(target_id).get('elite_until', 0)
                if current_elite < time.time():
                    current_elite = time.time()
                db.update_user_field(target_id, 'elite_until', current_elite + (days * 86400))
                send_msg(peer, f"✅ Вы успешно выдали подписку ELITE на {days} дней для {get_user_mention(target_id)}!")
            else:
                send_msg(peer, "❌ Минимальный срок — 1 день!")
            continue
        elif msg_lower.startswith("//moder") and user['moder_rank'] >= 3:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            try:
                rank = int(parts[1])
            except:
                send_msg(peer, "❌ Использование: //moder (ранг) (ответ/ссылка/ID)\nРанги: 1-модер, 2-админ, 3-гл.админ, 4-зам, 5-владелец, -1=снять")
                continue
            target_id = parse_target(parts, 1 if is_reply else 2, message_obj)
            if target_id:
                max_allowed = user['moder_rank'] if user['moder_rank'] == 5 else user['moder_rank'] - 1
                target_user = db.get_user(target_id)
                if target_user and target_user.get('moder_rank', 0) >= 4 and uid != OWNER_VK_ID:
                    send_msg(peer, "❌ Нельзя менять ранг заму и владельцу!")
                    continue
                if rank > max_allowed and uid != OWNER_VK_ID:
                    send_msg(peer, "❌ Вы не можете выдать этот ранг!")
                    continue
                final_rank = 0 if rank == -1 else max(0, rank)
                db.update_user_field(target_id, 'moder_rank', final_rank)
                send_msg(peer, "успешно!", reply_to=message_obj.get('id'))
            else:
                send_msg(peer, "❌ Использование: //moder (ранг) (ответ/ссылка/ID)")
            continue
        elif msg_lower.startswith("//pin") and user['moder_rank'] >= 1:
            if message_obj.get('reply_message'):
                try:
                    vk.messages.pin(peer_id=peer, conversation_message_id=message_obj['reply_message']['conversation_message_id'])
                    send_msg(peer, "✅ Сообщение закреплено!")
                except Exception as e:
                    send_msg(peer, f"❌ Ошибка: {e}")
            else:
                send_msg(peer, "❌ Использование: ответь на сообщение командой //pin")
            continue
        elif msg_lower.startswith("delpromo") and user['moder_rank'] >= 2:
            parts_cmd = msg.split()
            if len(parts_cmd) < 2:
                send_msg(peer, "❌ Использование: delpromo (название)\nПример: delpromo тест")
                continue
            promo_name = parts_cmd[1]
            if promo_name in promo_codes:
                del promo_codes[promo_name]
                send_msg(peer, f"✅ Промокод {promo_name} успешно удалён!")
            else:
                send_msg(peer, f"❌ Промокод {promo_name} не найден!")
            continue
        elif msg_lower.startswith("//newpromo") and user['moder_rank'] >= 4:
            parts_cmd = msg.split()
            if user['moder_rank'] == 2 and user.get('elite_until', 0) < time.time():
                send_msg(peer, "❌ Нужна ELITE подписка для создания промокодов!")
                continue
            if len(parts_cmd) < 4:
                send_msg(peer, "❌ Использование: //newpromo (название) (активаций) (сумма)\n- delpromo (название) — удалить промокод")
                continue
            promo_name = parts_cmd[1]
            try:
                activations = int(parts_cmd[2])
            except:
                send_msg(peer, "❌ Активаций должно быть числом!")
                continue
            reward_str = " ".join(parts_cmd[3:])
            reward = str_to_num(reward_str)
            if not reward:
                send_msg(peer, "❌ Неверная сумма!")
                continue
            # Ограничения для ELITE
            if user['moder_rank'] < 4:
                if user.get('elite_until', 0) < time.time():
                    send_msg(peer, "❌ Нужна ELITE подписка!")
                    continue
                if activations > 3:
                    send_msg(peer, "❌ Максимум 3 активации!")
                    continue
                if reward > 100000000000000:
                    send_msg(peer, "❌ Максимум 100 мк!")
                    continue
                if uid in promo_elite_used and time.time() - promo_elite_used[uid] < 86400:
                    send_msg(peer, "❌ Можно раз в день!")
                    continue
                promo_elite_used[uid] = time.time()
            promo_codes[promo_name] = {"amount": reward, "activations": activations, "used": [], "reward_str": reward_str}
            try:
                conn = sqlite3.connect('database.db')
                conn.execute("INSERT OR REPLACE INTO promos_save (code, amount, activations, reward_str) VALUES (?, ?, ?, ?)", (promo_name, reward, activations, reward_str))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Ошибка сохранения промо: {e}")
            send_msg(peer, f"✅ Промокод {promo_name} успешно создан!\nАктиваций: {activations}\nСумма: {reward_str}")
            continue
        elif msg_lower == "//przd" and user['moder_rank'] >= 4:
            txt = "📋 Типы заданий (переменные):\n\n"
            for key, desc in TASK_TYPES.items():
                txt += f"• {key} — {desc}\n"
            txt += "\nИспользование: //newzd (тип) (цель) (награда)\nПример: //newzd реф 2 1мм"
            send_msg(peer, txt)
            continue
        elif msg_lower.startswith("//cupon") and user['moder_rank'] >= 4:
            is_reply = bool(message_obj.get('reply_message'))
            if is_reply:
                target_id = message_obj.get('reply_message', {}).get('from_id')
                if not target_id:
                    send_msg(peer, "❌ Не удалось определить пользователя.")
                    continue
                try:
                    count = int(parts[1])
                except:
                    send_msg(peer, "❌ Использование: ответь на сообщение и напиши //cupon (кол-во)")
                    continue
            else:
                target_id = parse_target(parts, 1, message_obj)
                if not target_id or len(parts) < 3:
                    send_msg(peer, "❌ Использование: //cupon (ответ/ссылка/ID) (кол-во)")
                    continue
                try:
                    count = int(parts[2])
                except:
                    send_msg(peer, "❌ Укажите количество выводов!")
                    continue
            if count < 1:
                send_msg(peer, "❌ Минимум 1 вывод!")
                continue
            cupons[target_id] = cupons.get(target_id, 0) + count
            send_msg(peer, f"✅ {get_user_mention(target_id)} получил {count} бесплатных выводов!")
            continue
        elif msg_lower.startswith("//rangup") and user['moder_rank'] >= 4:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            target_id = parse_target(parts, 1 if is_reply else 1, message_obj) if not is_reply else (message_obj.get('reply_message') or {}).get('from_id')
            if not target_id:
                send_msg(peer, "❌ Использование: //rangup (ответ/ссылка)\nПример: //rangup @user")
                continue
            target_user = db.get_user(target_id)
            current_rank = target_user.get('moder_rank', 0)
            if current_rank >= 5:
                send_msg(peer, "❌ Нельзя повысить владельца!")
                continue
            if current_rank >= 4 and user['moder_rank'] < 5:
                send_msg(peer, "❌ Только владелец может повысить зама!")
                continue
            new_rank = current_rank + 1
            db.update_user_field(target_id, 'moder_rank', new_rank)
            ranks = {0: "Игрок", 1: "Модератор", 2: "Администратор", 3: "Гл. Администратор", 4: "Зам. Владельца", 5: "Владелец"}
            if user.get('is_glnish', 0) == 1:
                rank_name = "Разработчик @badbotik"
            else:
                rank_name = ranks[user['moder_rank']]
            send_msg(peer, f"✅ {get_user_mention(target_id)} повышен до {ranks[new_rank]}!")
            continue

        elif msg_lower.startswith("//newzd") and user['moder_rank'] >= 4:
            parts_cmd = msg.split(maxsplit=1)
            if len(parts_cmd) < 2:
                send_msg(peer, "❌ Использование: //newzd (описание) (награда)\nПример: //newzd Сделать 100 кликов 1мм")
                continue
            rest = parts_cmd[1].strip()
            # Ищем последнее слово как награду
            parts_rest = rest.split()
            reward_str = parts_rest[-1]
            reward = str_to_num(reward_str)
            if not reward:
                send_msg(peer, "❌ Неверная награда! Пример: //newzd Сделать 100 кликов 1мм")
                continue
            task_desc = " ".join(parts_rest[:-1])
            if not task_desc:
                send_msg(peer, "❌ Укажите описание задания!")
                continue
            if len(active_tasks) >= 10:
                send_msg(peer, "❌ Максимум 10 заданий!")
                continue
            active_tasks[task_next_id] = {"type": "custom", "desc": task_desc, "reward": reward, "reward_str": reward_str}
            try:
                conn = sqlite3.connect('database.db')
                conn.execute("INSERT INTO tasks_save (id, type, target, reward, reward_str) VALUES (?, 'custom', 0, ?, ?)", (task_next_id, reward, task_desc))
                conn.commit()
                conn.close()
            except:
                pass
            task_next_id += 1
            # Сбрасываем прогресс для всех
            for uid_key in task_progress:
                task_progress[uid_key][task_next_id] = 0
            try:
                conn = sqlite3.connect('database.db')
                conn.execute("DELETE FROM task_progress_save WHERE task_id = ?", (task_next_id,))
                conn.commit()
                conn.close()
            except:
                pass
            send_msg(peer, "успешно!", reply_to=message_obj.get('id'))
        elif msg_lower == "//przd" and user['moder_rank'] >= 4:
            txt = "📋 Типы заданий (переменные):\n\n"
            for key, desc in TASK_TYPES.items():
                txt += f"• {key} — {desc}\n"
            send_msg(peer, txt)
            continue
        elif msg_lower.startswith("//post") and user['moder_rank'] >= 4:
            text = " ".join(parts[1:])
            if not text:
                send_msg(peer, "❌ Использование: //post (текст)")
                continue
            try:
                vk.wall.post(owner_id=-GROUP_ID, from_group=1, message=text)
                send_msg(peer, "✅ Пост опубликован!")
            except Exception as e:
                send_msg(peer, f"❌ Ошибка: {e}")
            continue
        elif msg_lower.startswith("//delzd") and user['moder_rank'] >= 4:
            parts_cmd = msg.split()
            if len(parts_cmd) < 2:
                send_msg(peer, "❌ Использование: //delzd (номер)")
                continue
            try:
                task_num = int(parts_cmd[1])
            except:
                send_msg(peer, "❌ Номер должен быть числом!")
                continue
            if task_num in active_tasks:
                del active_tasks[task_num]
                try:
                    conn = sqlite3.connect('database.db')
                    conn.execute("DELETE FROM tasks_save WHERE id = ?", (task_num,))
                    conn.commit()
                    conn.close()
                except:
                    pass
                send_msg(peer, f"✅ Задание #{task_num} удалено!")
            else:
                send_msg(peer, f"❌ Задание #{task_num} не найдено!")
            continue

        elif msg_lower.startswith("//delzd") and user['moder_rank'] >= 4:
            parts_cmd = msg.split()
            if len(parts_cmd) < 2:
                send_msg(peer, "❌ Использование: //delzd (номер)")
                continue
            try:
                task_num = int(parts_cmd[1])
            except:
                send_msg(peer, "❌ Номер должен быть числом!")
                continue
            if task_num in active_tasks:
                del active_tasks[task_num]
                try:
                    conn = sqlite3.connect('database.db')
                    conn.execute("DELETE FROM tasks_save WHERE id = ?", (task_num,))
                    conn.commit()
                    conn.close()
                except:
                    pass
                send_msg(peer, f"✅ Задание #{task_num} удалено!")
            else:
                send_msg(peer, f"✅ Задание #{task_next_id} создано!\n📝 {task_desc}\n💰 Награда: {reward_str}")
            continue

        elif msg_lower.startswith("//set0") and user['moder_rank'] >= 4:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            if len(parts) < 2:
                send_msg(peer, "❌ Использование: //set0 (режим) (ответ/ссылка/ID)\nРежимы: nk(ник), cl(клики), bl(баланс), rg(дата), vv(вывод), all(всё)\nПример: //set0 all @user")
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
                if mode in ["all"]:
                    db.update_user_field(target_id, 'moder_rank', 0)
                    db.update_user_field(target_id, 'is_glnish', 0)
                    db.update_user_field(target_id, 'elite_until', 0)
                    db.update_user_field(target_id, 'vip_until', 0)
                    db.update_user_field(target_id, 'has_legendary', 0)
                    db.update_user_field(target_id, 'game_boost_until', 0)
                    db.update_user_field(target_id, 'x2_until', 0)
                    db.update_user_field(target_id, 'no_cd_until', 0)
                send_msg(peer, "успешно!", reply_to=message_obj.get('id'))
            else:
                send_msg(peer, "❌ Использование: //set0 (режим) (ответ/ссылка/ID)")
            continue
        elif msg_lower.startswith("уб") and user['moder_rank'] >= 4:
            is_reply = bool(message_obj.get('reply_message') or (message_obj.get('fwd_messages')))
            if is_reply or (len(parts) > 1 and not parts[1].isdigit() and not parts[1].startswith("-") and not parts[1].endswith("м") and not parts[1].endswith("к")):
                target_id = parse_target(parts, 1, message_obj)
                amt_idx = 1 if is_reply else 2
            else:
                target_id = uid
                amt_idx = 1
            if len(parts) > amt_idx:
                amt_text = " ".join(parts[amt_idx:])
                if amt_text.startswith("-"):
                    amount = str_to_num(amt_text[1:])
                    if amount and amount > 0:
                        target_bal = db.get_user(target_id)['balance']
                        db.add_balance(target_id, -amount)
                        send_msg(peer, f"✅ Вы успешно сняли {balance_to_str(amount)} у {get_user_mention(target_id)}")
                        send_msg(DONATE_CHAT_ID, f"💰 Снятие: {get_user_mention(uid)} снял {num_to_str(amount)} у {get_user_mention(target_id)}")
                    else:
                        send_msg(peer, "❌ Неверная сумма.")
                else:
                    amount = str_to_num(amt_text)
                    if amount and amount > 0:
                        new_bal = db.add_balance(target_id, amount)
                        if target_id == uid:
                            send_msg(peer, f"✅ Вы успешно выдали себе {balance_to_str(amount)}!\n💳 Ваш баланс: {balance_to_str(new_bal)}")
                        else:
                            send_msg(peer, f"✅ Вы успешно выдали {balance_to_str(amount)} для {get_user_mention(target_id)}")
                            send_msg(target_id, f"💰 Вам выдали {balance_to_str(amount)}!\n💳 Ваш баланс: {balance_to_str(new_bal)}")
                        send_msg(DONATE_CHAT_ID, f"💰 Выдача: {get_user_mention(uid)} выдал {num_to_str(amount)} -> {get_user_mention(target_id)}")
                    else:
                        send_msg(peer, "❌ Неверная сумма.")
            else:
                send_msg(peer, "❌ Использование: уб (сумма) — выдать себе\nуб (ответ/ссылка) (сумма) — выдать другому\nДля снятия: уб @user -сумма")
            continue
        elif msg_lower.startswith("//рассылка") and user['moder_rank'] == 5:
            text = " ".join(parts[1:])
            if not text:
                send_msg(peer, "❌ Использование: //рассылка (текст)")
                continue
            users = db.get_all_users()
            sent = 0
            failed = 0
            send_msg(peer, f"📨 Начинаю рассылку на {len(users)} пользователей...")
            for u in users:
                try:
                    send_msg(u['user_id'], text)
                    sent += 1
                    time.sleep(0.3)
                except:
                    failed += 1
            send_msg(peer, f"✅ Рассылка завершена!\nОтправлено: {sent}\nОшибок: {failed}")
            continue
        elif msg_lower == "//stop" and user['moder_rank'] == 5:
            send_msg(peer, "🛑 Бот остановлен!")
            os.system("pkill -9 -f main.py")
            sys.exit()
            continue
        elif msg_lower == "//chatid" and user['moder_rank'] == 5:
            send_msg(peer, f"⚙️ ID текущей беседы ВК: {peer}")
            continue
        elif msg_lower == "//update" and user['moder_rank'] == 5:
            send_msg(peer, "🔄 Перезагружаю данные и бота...")
            try:
                os.system("cd /root/bot-cl && git pull https://github.com/myaso-52/bot-cl.git main && sleep 2 && pkill -9 -f main.py && sleep 1 && cd /root/bot-cl && source venv/bin/activate && nohup python3 main.py > bot.log 2>&1 &")
                time.sleep(1)
                send_msg(peer, "✅ Бот успешно перезапущен!")
                sys.exit()
            except:
                pass
            continue
        elif msg_lower == "//fix" and user['moder_rank'] == 5:
            send_msg(peer, "🛠 Самодиагностика...")
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
                    send_msg(peer, f"⚙️ Исправлено багов: {fixes}. Перезапуск...")
                    subprocess.Popen(["bash", "-c", "sleep 1 && pkill -9 -f main.py && nohup python3 main.py > bot.log 2>&1 &"])
                    sys.exit()
                else:
                    compile(code, "main.py", "exec")
                    send_msg(peer, "✅ Ошибок не обнаружено!")
            except Exception as e:
                send_msg(peer, f"❌ Ошибка: {e}")
            continue
        elif msg_lower.startswith("//upcmd") and user['moder_rank'] == 5:
            text = " ".join(parts[1:])
            if not text:
                send_msg(peer, "❌ Использование: //upcmd (текст)\nПример: //upcmd Новый текст справки")
                continue
            try:
                conn = sqlite3.connect('database.db')
                conn.execute("DELETE FROM help_text")
                conn.execute("INSERT INTO help_text (id, text) VALUES (1, ?)", (text,))
                conn.commit()
                conn.close()
                send_msg(peer, "✅ Текст справки успешно обновлён!")
            except Exception as e:
                send_msg(peer, f"❌ Ошибка: {e}")
            continue
        elif msg_lower == "//clearfile" and user['moder_rank'] == 5:
            with open(os.path.basename(sys.argv[0]), "w") as f:
                f.write("")
            sys.exit()
        elif msg_lower in ["правила", "📜 правила", "правила проекта"]:
            txt = """🤖 ПРАВИЛА БОТА:

1. 🔒 Слив должности (модер/админ/зам/владелец) — бан навсегда во всех проектах
2. 🐛 Багоюз/эксплойты — обнуление баланса + бан
3. 🤖 Ботоводство (накрутка кликов, рефералов) — обнуление + бан (1-30)
4. 🔑 Передача/продажа аккаунта — бан (навсегда)
5. 💀 Попытка взлома/фишинга — бан навсегда
6. 📛 Обход бана (мультиаккаунты) — все твинки в бан навсегда
7. 🛡 Администрация всегда права, но можно подать репорт

Срок давности: отсутствует"""
            send_msg(peer, txt, get_main_keyboard())
            continue

        elif msg_lower in ["модер", "модератор", "стать модером"]:
            txt = """👑 Хочешь стать модератором?

📋 Что нужно:
• Быть активным игроком
• Знать правила бота и чата
• Помогать новичкам
• Выполнить задание от администрации

📩 Пиши @dimo4kaenergy с пометкой «Набор в модерацию»

Укажи:
• Твой ID
• Опыт (если есть)
• Почему именно ты?"""
            send_msg(peer, txt, get_main_keyboard())
            continue

        elif msg_lower in ["профиль", "👤 профиль", "проф", "я", "Я"]:
            ranks = {0: "Игрок", 1: "Модератор", 2: "Администратор", 3: "Гл. Администратор", 4: "Зам. Владельца", 5: "Владелец"}
            if user.get('is_glnish', 0) == 1:
                rank_name = "Разработчик @badbotik"
            else:
                rank_name = ranks[user['moder_rank']]
            now = time.time()
            name_val = user.get('nickname', 'Игрок')
            if name_val == 'Игрок' or not name_val:
                try:
                    if uid > 0:
                        vk_u = vk.users.get(user_ids=uid)[0]
                        name_val = f"{vk_u['first_name']} {vk_u['last_name']}"
                    else:
                        name_val = f"Сообщество {abs(uid)}"
                except:
                    name_val = f"ID {uid}"
            r_date = user.get('reg_date') if user.get('reg_date') else "24.07.2026"
            
            txt = f"👤 Профиль пользователя [id{uid}|{name_val}]\n"
            
            if user.get('vip_until', 0) > now:
                txt += "💎 VIP\n"
            if user.get('elite_until', 0) > now:
                txt += "⭐ ELITE\n"
            if user.get('has_legendary', 0) == 1:
                txt += "👑 THE LEGENDARY\n"
            if user.get('is_perm_banned', 0) == 1 or user.get('ban_until', 0) > time.time():
                txt += "🚫 ЗАБЛОКИРОВАН\n"
            
            fav_game = user.get('fav_game', 'Не выбрана')
            fav_artist = user.get('fav_artist', 'Не выбран')
            txt += (
                f"🏅 Ранг: {rank_name}\n"
                f"💰 Баланс: {num_to_str(user['balance'])}\n"
                f"👆 Кликов: {user.get('clicks_count', 0)}\n"
                f"💸 Выведено: {num_to_str(max(0, user.get('total_withdrawn', 0)))}\n"
                f"🎮 Игра: {fav_game}\n"
                f"🎤 Исполнитель: {fav_artist}\n"
                f"🆔 ID: {uid}\n"
                f"📅 Регистрация: {r_date}"
            )
            send_msg(peer, txt, get_main_keyboard())
            continue

        state = user_states.get(uid)
        if state and state.get("action") == "waiting_elite_days":
            try:
                days = int(msg)
            except:
                send_msg(peer, "❌ Введите число дней!")
                continue
            if days < 1:
                send_msg(peer, "❌ Минимальный срок — 1 день!")
                continue
            cost = days * 5000000000000
            fresh_user = db.get_user(uid)
            if fresh_user['balance'] < cost:
                send_msg(peer, f"❌ Недостаточно средств!\nНужно: {num_to_str(cost)}\nВаш баланс: {num_to_str(fresh_user['balance'])}\n\nПополните баланс командой: пополнить {num_to_str(cost)}")
                user_states.pop(uid, None)
                continue
            db.add_balance(uid, -cost)
            current_elite = fresh_user.get('elite_until', 0)
            if current_elite < time.time():
                current_elite = time.time()
            db.update_user_field(uid, 'elite_until', current_elite + (days * 86400))
            user_states.pop(uid, None)
            user = db.get_user(uid)
            # user refreshed
            send_msg(peer, f"✅ ELITE подписка активирована на {days} дней!\nСписано: {num_to_str(cost)}", get_main_keyboard())
            # Проверка задания элит
            for num, task in list(active_tasks.items()):
                if task['type'] == 'элит' and num in active_tasks:
                    db.add_balance(uid, task['reward'])
                    new_bal = db.get_user(uid)["balance"]
                    send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                    del active_tasks[num]
                    try:
                        conn = sqlite3.connect('database.db')
                        conn.execute('DELETE FROM tasks WHERE id = ?', (num,))
                        conn.commit()
                        conn.close()
                    except:
                        pass
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
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except:
                    pass

            if "donate_approve" in payload:
                data = payload["donate_approve"].split("_")
                target_uid = int(data[0])
                amount_str = "_".join(data[1:])
                amount = str_to_num(amount_str)
                try:
                    vk.messages.sendMessageEventAnswer(event_id=event.obj['event_id'], user_id=event.obj['user_id'], peer_id=event.obj['peer_id'])
                except:
                    pass
                if amount and amount > 0:
                    new_bal = db.add_balance(target_uid, amount)
                    try:
                        send_msg(target_uid, f"✅ Ваше пополнение успешно одобрено!\n💰 Ваш баланс: {num_to_str(new_bal)}")
                    except:
                        pass
                    send_msg(DONATE_CHAT_ID, f"✅ Пополнение одобрено!\nПользователь: {get_user_mention(target_uid)} (ID: {target_uid})\nСумма: {amount_str}")

            elif "donate_reject" in payload:
                target_uid = int(payload["donate_reject"])
                try:
                    vk.messages.sendMessageEventAnswer(event_id=event.obj['event_id'], user_id=event.obj['user_id'], peer_id=event.obj['peer_id'])
                except:
                    pass
                try:
                    send_msg(target_uid, "❌ Владелец отказал в поступлении денег в Бот Нищий.\nПерепроверьте перевод @badbotik")
                except:
                    pass
                send_msg(DONATE_CHAT_ID, f"❌ Пополнение отклонено для {get_user_mention(target_uid)} (ID: {target_uid})")

            if "rep_take" in payload:
                rep_id = payload["rep_take"]
                rep_data = active_reports.get(rep_id)
                try:
                    vk.messages.sendMessageEventAnswer(event_id=event.obj['event_id'], user_id=event.obj['user_id'], peer_id=event.obj['peer_id'])
                except:
                    pass
                if rep_data and rep_data["taken_by"] is None:
                    user_data = db.get_user(event.obj['user_id'])
                    rank_names = {1: "Модератор", 2: "Администратор", 3: "Гл. Администратор", 4: "Зам. Владельца", 5: "Владелец"}
                    rank = rank_names.get(user_data.get('moder_rank', 0), "Сотрудник")
                    rep_data["taken_by"] = event.obj['user_id']
                    send_msg(rep_data["uid"], f"✌️ {get_user_mention(rep_data['uid'])}, ваш репорт успешно взял {rank}, ожидайте.")
                    taken_keyboard = VkKeyboard(inline=True)
                    taken_keyboard.add_button(label="🔒 Закрыть репорт", color=VkKeyboardColor.NEGATIVE, payload=json.dumps({"rep_solve": rep_id}))
                    send_msg(REPORT_CHAT_ID, f"📋 Репорт {rep_id}\nВзял: {get_user_mention(event.obj['user_id'])} ({rank})\nНарушитель: {get_user_mention(rep_data['target_id'])}\nЗаявитель: {get_user_mention(rep_data['uid'])}", keyboard=taken_keyboard.get_keyboard())

            elif "rep_solve" in payload:
                rep_id = payload["rep_solve"]
                rep_data = active_reports.get(rep_id)
                try:
                    vk.messages.sendMessageEventAnswer(event_id=event.obj['event_id'], user_id=event.obj['user_id'], peer_id=event.obj['peer_id'])
                except:
                    pass
                if rep_data:
                    if rep_data["taken_by"] == event.obj['user_id'] or event.obj['user_id'] == OWNER_VK_ID:
                        send_msg(rep_data["uid"], "🔒 Ваш репорт успешно закрыт.")
                        send_msg(REPORT_CHAT_ID, f"✅ Репорт {rep_id} закрыт!\nЗакрыл: {get_user_mention(event.obj['user_id'])}")
                        active_reports.pop(rep_id, None)
                    else:
                        send_msg(event.obj['peer_id'], "❌ Закрыть репорт может только тот, кто его взял, или владелец.")
