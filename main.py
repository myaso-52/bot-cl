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
OWNER_VK_ID = 827888215
DONATE_CHAT_ID = 2000000006
REPORT_CHAT_ID = 2000000007

ALLOWED_KICK_CHATS = [TARGET_CHAT_ID, TEST_CHAT_ID, CONSOLE_CHAT_ID, MODER_CHAT_ID]
ADD_CHATS = [TARGET_CHAT_ID, TEST_CHAT_ID, REPORT_CHAT_ID]

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

db.init_db()
print("⚠️ База данных успешно синхронизирована!")

ban_notified_users = {}
user_states = {}
pending_donations = {}
pending_withdrawals = {}
active_games = {}
active_reports = {}

# Задания
active_tasks = {}  # {номер: {"type": тип, "target": цель, "reward": награда}}
task_progress = {}  # {uid: {номер: прогресс}}
task_next_id = 1

# Промокоды
promo_codes = {}
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
    {"id": 0, "title": "Снятие задержки кликера (12ч)", "cost_coins": 50000000000000, "cost_str": "50 мм", "desc": "Убирает задержку кликера полностью."},
    {"id": 1, "title": "Множитель х2 клика (12ч)", "cost_coins": 100000000000000, "cost_str": "100 мм", "desc": "Удваивает награду за клик."},
    {"id": 2, "title": "Множитель игр х2 (12ч)", "cost_coins": 85000000000000, "cost_str": "85 мм", "desc": "Все награды в мини-играх удваиваются!"},
    {"id": 3, "title": "🌟 ELITE подписка", "cost_coins": 5000000000000, "cost_str": "5 мм/день", "desc": "Премиум подписка. Команда: купэлит (дни)"},
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
    if num >= 1000000000000000:
        return f"{int(num / 1000000000000000)}ммк"
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
        kb.add_line()
        kb.add_button('Назад', color=VkKeyboardColor.PRIMARY, payload={"cmd": "игры2"})
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
    if len(opened) > 0 and len(opened) < (5 if game_state.get("elite") else 3):
        kb.add_button("💰 Забрать куш", color=VkKeyboardColor.POSITIVE, payload={"cmd": "куш"})
    else:
        kb.add_button("⬅ Назад", color=VkKeyboardColor.SECONDARY, payload={"cmd": "назад"})
    return kb.get_keyboard()


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
                        "кнб": "кнб", "вордли": "вордли", "сейф": "сейф", "бомба": "бомба", "виселица": "виселица", "рефка": "рефка",
                        "задания": "задания"
                    }
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
                            msg = "получить множитель"
                        elif item_id == 2:
                            msg = "получить множитель игр"
                        elif item_id == 3:
                            msg = "купэлит"
                        msg_lower = msg.lower()
                    parts = msg.split()
            except:
                pass

        user = db.get_user(uid)
        if user and (user.get('nickname') == 'Игрок' or not user.get('nickname')):
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
        if active_tasks:
            if uid not in task_progress:
                task_progress[uid] = {}
            for num, task in list(active_tasks.items()):
                if num not in task_progress[uid]:
                    task_progress[uid][num] = 0
                current = task_progress[uid][num]
                if current >= task['target']:
                    continue
                ttype = task['type']
                # Проверка разных типов
                if ttype == "реф" and user.get('referrer_id', 0) != 0:
                    task_progress[uid][num] = 1 if task['target'] <= 1 else task_progress[uid].get(num, 0)
                elif ttype == "клик":
                    task_progress[uid][num] = user.get('clicks_count', 0)
                elif ttype == "баланс":
                    fresh = db.get_user(uid)
                    bal_mm = int(fresh.get('balance', 0) / 1000000000000)
                    if task_progress[uid].get(num, 0) != bal_mm:
                        task_progress[uid][num] = bal_mm
                        send_msg(peer, f"📊 Прогресс задания #{num} обновлён: {bal_mm}/{task['target']} мм")
                        if bal_mm >= task['target'] and num in active_tasks:
                            db.add_balance(uid, task['reward'])
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
                elif ttype == "вход":
                    task_progress[uid][num] = task_progress[uid].get("daily_login", 0)
                elif ttype == "магазин":
                    task_progress[uid][num] = task_progress[uid].get("shop_buys", 0)
                elif ttype == "элит" and user.get('elite_until', 0) > time.time():
                    task_progress[uid][num] = 1
                # Проверка выполнения
                if num in task_progress.get(uid, {}) and task_progress[uid][num] >= task['target']:
                    db.add_balance(uid, task['reward'])
                    new_bal = db.get_user(uid)["balance"]
                    send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task["type"]]}!\n+{task["reward_str"]}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                    del task_progress[uid][num]

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

        if contest_active and not contest_winner_found and peer == TARGET_CHAT_ID:
            try:
                guess = int(msg)
                if 1 <= guess <= 50:
                    if guess == contest_secret:
                        contest_winner_found = True
                        contest_active = False
                        db.add_balance(uid, 1000000000000000)
                        send_msg(peer, f"🎉 {get_user_mention(uid)} угадал число {contest_secret}!\nПриз: 1 мм зачислен на баланс!")
            except:
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
                                done = "🟢" * wins + "⚪" * (task['target'] - wins)
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
                if uid not in task_progress:
                        task_progress[uid] = {}
                if uid not in task_progress:
                    task_progress[uid] = {}
                task_progress[uid]["knb_wins"] = task_progress[uid].get("knb_wins", 0) + 1
                result = f"🎉 Ты победил! +{num_to_str(reward)}"
                for num, task in list(active_tasks.items()):
                    if task['type'] == 'кнб':
                        wins = task_progress[uid].get("knb_wins", 0)
                        done = "🟢" * wins + "⚪" * (task['target'] - wins)
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
            send_msg(peer, f"👋 Привет, {get_user_mention(uid)}! Я бот с крутыми играми для заработка! Кликер, сапёр, Вордли, КНБ, Сейф и многое другое. Зарабатывай и выводи прямо сейчас! 🚀\n\nИспользуй кнопки ниже:", get_main_keyboard())
            continue
        elif msg_lower in ["💰 баланс", "баланс"]:
            send_msg(peer, f"👀 Ваш баланс: {balance_to_str(db.get_user(uid)['balance'])}", get_main_keyboard())
            continue
        elif msg_lower in ["🕹 mini-игры", "мини-игры"]:
            send_msg(peer, "Мини-игры (стр. 1/3):\n\n💣 Сапер\n🕵 Загадки\n🧮 Математика\n📱 Кликер\n🎲 Угадай число\n❌⭕ Крестики-нолики\n✂️ КНБ\n🟩 Вордли", get_games_keyboard(1))
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
            new_bal = db.add_balance(uid, reward)
            send_msg(peer, f"🎯 Клик! +{num_to_str(reward)}\n💰 Баланс: {num_to_str(new_bal)}", get_games_keyboard(1))
            continue
        elif msg_lower in ["💣 мины", "мины", "сапер", "💣 сапер"]:
            if not is_dm:
                send_msg(peer, "❌ Сапер доступен только в Личных Сообщениях!", get_games_keyboard(1))
                continue
            is_elite = user.get('elite_until', 0) > time.time()
            if is_elite:
                f = [1, 1, 1, 0, 0, 0, 0, 0, 0]
            else:
                f = [1, 1, 1, 1, 1, 1, 0, 0, 0]
            random.shuffle(f)
            active_games[uid] = {"game": "mines", "field": f, "opened": [], "current_bank": 0, "elite": is_elite}
            diamonds = "6" if is_elite else "3"
            send_msg(peer, f"💣 Сапер (3х3)\nНа поле {diamonds} алмаза. Каждая чистая коробка: +40 мк в куш!", keyboard=get_mines_keyboard(active_games[uid]))
            continue
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
                        done = "🟢" * wins + "⚪" * (task['target'] - wins)
                        send_msg(peer, f"📋 Задание #{num}: {done} {wins}/{task['target']}")
                        if wins >= task['target'] and num in active_tasks:
                            new_bal = db.get_user(uid)["balance"]
                            send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                            del active_tasks[num]
                            if uid in task_progress and num in task_progress[uid]:
                                del task_progress[uid][num]
                                del task_progress[uid][num]
                            try:
                                conn = sqlite3.connect('database.db')
                                conn.execute('DELETE FROM tasks WHERE id = ?', (num,))
                                conn.commit()
                                conn.close()
                            except:
                                pass
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
        elif msg_lower.startswith("+ник"):
            send_msg(peer, "❌ Использование: +ник (новое имя)\nПример: +ник КрутойИгрок")
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
                name = r['nickname'] if r['nickname'] and r['nickname'] != 'Игрок' else f"Игрок {r['user_id']}"
                txt += f"{i}. [id{r['user_id']}|{name}] — {r['clicks_count']} кл.\n"
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
                progress = task_progress.get(uid, {}).get(num, 0)
                txt += f"#{num} {TASK_TYPES[task['type']]}: {progress}/{task['target']} | Награда: {task['reward_str']}\n"
            txt += "\nКоманда: прогресс — детальный прогресс"
            send_msg(peer, txt, get_games_keyboard(1))
            continue
        elif msg_lower in ["прогресс"]:
            if not active_tasks:
                send_msg(peer, "📋 Нет активных заданий.", get_main_keyboard())
                continue
            txt = "📊 Ваш прогресс:\n\n"
            has_any = False
            for num, task in list(active_tasks.items()):
                progress = task_progress.get(uid, {}).get(num, 0)
                done = "🟢" * progress
                left = "⚪" * (task['target'] - progress)
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
                    done = "🟢" * logins + "⚪" * (task['target'] - logins)
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
            txt += "\nДля активации просто напиши название промокода в чат!"
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
        elif msg_lower.startswith("репорт") and len(parts) > 1:
            target_id = parse_target(parts, 1, message_obj)
            if not target_id:
                send_msg(peer, "❌ Использование: репорт (ссылка/ответ/ID) (причина)\nОбязательно перешлите сообщения нарушителя!")
                continue
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Не указана"
            if not message_obj.get('fwd_messages'):
                send_msg(peer, "❌ Обязательно перешлите сообщения нарушителя!")
                continue
            rep_id = f"rep_{uid}_{int(time.time())}"
            active_reports[rep_id] = {"uid": uid, "target_id": target_id, "reason": reason, "taken_by": None}
            rep_keyboard = VkKeyboard(inline=True)
            rep_keyboard.add_button(label="📋 Взять на рассмотрение", color=VkKeyboardColor.POSITIVE, payload=json.dumps({"rep_take": rep_id}))
            send_msg(REPORT_CHAT_ID, f"📋 Новый репорт!\n\nОт: {get_user_mention(uid)} (ID: {uid})\nНарушитель: {get_user_mention(target_id)} (ID: {target_id})\nПричина: {reason}\n\nID репорта: {rep_id}", keyboard=rep_keyboard.get_keyboard())
            send_msg(peer, "✅ Ваш репорт отправлен на рассмотрение!")
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
            db.update_user_field(uid, 'no_cd_until', time.time() + 43200)
            user = db.get_user(uid)
            send_msg(peer, f"✅ Услуга '{item['title']}' успешно куплена на 12 часов!", get_main_keyboard())
            if uid not in task_progress:
                task_progress[uid] = {}
            task_progress[uid]["shop_buys"] = task_progress[uid].get("shop_buys", 0) + 1
            for num, task in list(active_tasks.items()):
                if task['type'] == 'магазин':
                    buys = task_progress[uid].get("shop_buys", 0)
                    done = "🟢" * buys + "⚪" * (task['target'] - buys)
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
            db.update_user_field(uid, 'x2_until', time.time() + 43200)
            send_msg(peer, f"✅ Услуга '{item['title']}' успешно куплена на 12 часов!", get_main_keyboard())
            if uid not in task_progress:
                task_progress[uid] = {}
            task_progress[uid]["shop_buys"] = task_progress[uid].get("shop_buys", 0) + 1
            for num, task in list(active_tasks.items()):
                if task['type'] == 'магазин':
                    buys = task_progress[uid].get("shop_buys", 0)
                    done = "🟢" * buys + "⚪" * (task['target'] - buys)
                    send_msg(peer, f"📋 Задание #{num}: {done} {buys}/{task['target']}")
                    if buys >= task['target'] and num in active_tasks:
                        db.add_balance(uid, task['reward'])
                        new_bal = db.get_user(uid)["balance"]
                        send_msg(peer, f"🎉 Ты успешно выполнил задание #{num} — {TASK_TYPES[task['type']]}!\n+{task['reward_str']}\n💳 Текущий баланс: {num_to_str(new_bal)}")
                        del active_tasks[num]
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
            db.update_user_field(uid, 'game_boost_until', time.time() + 43200)
            send_msg(peer, f"✅ Услуга '{item['title']}' успешно куплена на 12 часов!", get_main_keyboard())
            if uid not in task_progress:
                task_progress[uid] = {}
            task_progress[uid]["shop_buys"] = task_progress[uid].get("shop_buys", 0) + 1
            for num, task in list(active_tasks.items()):
                if task['type'] == 'магазин':
                    buys = task_progress[uid].get("shop_buys", 0)
                    done = "🟢" * buys + "⚪" * (task['target'] - buys)
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
                history = badbot.get_history(3)
                found = False
                for tx in history:
                    if tx.get("amount", 0) >= amount and tx.get("id"):
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
                db.add_balance(uid, promo["amount"])
                send_msg(peer, f"✅ Промокод {promo_name} активирован!\n+{promo['reward_str']} на баланс!")
                left = promo["activations"] - len(promo["used"])
                send_msg(peer, f"Осталось активаций: {left}")
                if left == 0:
                    del promo_codes[promo_name]
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
                msg_out = f"✅ {get_user_mention(target_id)} получил доступ к команде: {command}"
            else:
                conn.execute("DELETE FROM custom_perms WHERE user_id = ? AND command = ?", (target_id, command))
                msg_out = f"✅ У {get_user_mention(target_id)} забран доступ к команде: {command}"
            conn.commit()
            conn.close()
            send_msg(peer, msg_out)
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
        elif msg_lower in ["помощь", "список команд", "//help", "команды", "Команды", "Помощь", "команды", "Команды", "Помощь"]:
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
                txt = "Нет сохранённого текста. Используйте //upcmd"
            send_msg(peer, txt, get_main_keyboard())
            continue
            continue
        elif msg_lower in ["администрация", "👑 администрация"]:
            txt = "@badbotikzarabotok\n👑 Администрация бота:\n\n"
            txt += f"🎱 Владелец: {get_user_mention(827888215)}\n"
            try:
                conn = sqlite3.connect('database.db')
                c = conn.cursor()
                c.execute("SELECT user_id FROM users WHERE moder_rank = 4")
                zam = c.fetchone()
                if zam:
                    txt += f"🏆 Зам. Владельца: {get_user_mention(zam[0])}\n"
                c.execute("SELECT user_id FROM users WHERE moder_rank = 3")
                glav = c.fetchall()
                if glav:
                    txt += "👹 Гл. Администраторы:\n"
                    for g in glav:
                        txt += f"  • {get_user_mention(g[0])}\n"
                conn.close()
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
            if target_id:
                target_user = db.get_user(target_id)
                if target_user:
                    ranks = {0: "Игрок", 1: "Модератор", 2: "Администратор", 3: "Гл. Администратор", 4: "Зам. Владельца", 5: "Владелец"}
                    now = time.time()
                    name_val = target_user.get('nickname', 'Игрок')
                    if name_val == 'Игрок':
                        name_val = f"Игрок {target_id}"
                    r_date = target_user.get('reg_date', 'Неизвестно')
                    txt = f"🌎 Профиль [id{target_id}|{name_val}]\n"
                    if target_user.get('vip_until', 0) > now:
                        txt += "👑 VIP\n"
                    if target_user.get('elite_until', 0) > now:
                        txt += "🌟 ELITE\n"
                    if target_user.get('has_legendary', 0) == 1:
                        txt += "♠️ THE LEGENDARY\n"
                    txt += (
                        f"👹 Ранг: {ranks[target_user['moder_rank']]}\n"
                        f"🍻 Баланс: {num_to_str(target_user['balance'])}\n"
                        f"🏀 Кликов: {target_user.get('clicks_count', 0)}\n"
                        f"🧠 Выведено: {num_to_str(target_user.get('total_withdrawn', 0))}\n"
                        f"💀 Регистрация: {r_date}"
                    )
                    send_msg(peer, txt)
                else:
                    send_msg(peer, "❌ Пользователь не найден.")
            else:
                send_msg(peer, "❌ Использование: //prof (ответ/ссылка/ID)")
            continue
        elif msg_lower.startswith("исключить") and user['moder_rank'] >= 1:
            if peer <= 2000000000 or peer not in ALLOWED_KICK_CHATS:
                send_msg(peer, "❌ Эту команду можно использовать только в разрешённых беседах!")
                continue
            target_id = parse_target(parts, 1, message_obj)
            if target_id:
                try:
                    vk.messages.removeChatUser(chat_id=peer-2000000000, user_id=target_id)
                    send_msg(peer, "успешно!")
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
                send_msg(peer, "успешно!")
            else:
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
                    txt = f"📋 Информация о блокировке:\n\n👤 Пользователь: {get_user_mention(target_id)}\n📅 Статус: {status}\n📝 Причина: {target_user.get('ban_reason', 'Не указана')}\n👹 Заблокировал: {get_user_mention(int(target_user.get('ban_by', 0))) if target_user.get('ban_by', '').isdigit() else target_user.get('ban_by', 'Неизвестно')}"
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
                send_msg(peer, "❌ Использование: //ban (дни) (ответ/ссылка/ID)\n-1 = навсегда, 0 = разбан")
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
                    send_msg(peer, "успешно!")
                    user = db.get_user(uid) if uid == target_id else user
                elif days == -1:
                    db.update_user_field(target_id, 'is_perm_banned', 1)
                    db.update_user_field(target_id, 'ban_reason', reason)
                    db.update_user_field(target_id, 'ban_by', str(uid))
                    try:
                        vk.groups.ban(group_id=GROUP_ID, owner_id=target_id, comment=reason, comment_visible=1)
                    except:
                        pass
                    send_msg(peer, "успешно!")
                else:
                    db.update_user_field(target_id, 'ban_until', time.time() + (days * 86400))
                    db.update_user_field(target_id, 'ban_reason', reason)
                    db.update_user_field(target_id, 'ban_by', str(uid))
                    send_msg(peer, "успешно!")
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
            send_msg(peer, "успешно!")
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
                if rank > max_allowed and uid != OWNER_VK_ID:
                    send_msg(peer, "❌ Вы не можете выдать этот ранг!")
                    continue
                final_rank = 0 if rank == -1 else max(0, rank)
                db.update_user_field(target_id, 'moder_rank', final_rank)
                send_msg(peer, "успешно!")
            else:
                send_msg(peer, "❌ Использование: //moder (ранг) (ответ/ссылка/ID)")
            continue
        elif msg_lower.startswith("//pin") and user['moder_rank'] >= 2:
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
        elif msg_lower.startswith("//newpromo") and user['moder_rank'] >= 2:
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
            if user['moder_rank'] == 2:
                if activations > 3:
                    send_msg(peer, "❌ ELITE: максимум 3 активации!")
                    continue
                if reward > 100000000000000:
                    send_msg(peer, "❌ ELITE: максимум 100 мк!")
                    continue
                if uid in promo_elite_used and time.time() - promo_elite_used[uid] < 86400:
                    send_msg(peer, "❌ ELITE: можно создать промокод раз в день!")
                    continue
                promo_elite_used[uid] = time.time()
            promo_codes[promo_name] = {"amount": reward, "activations": activations, "used": [], "reward_str": reward_str}
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
            send_msg(peer, f"✅ {get_user_mention(target_id)} повышен до {ranks[new_rank]}!")
            continue

        elif msg_lower.startswith("//newzd") and user['moder_rank'] >= 4:
            parts_cmd = msg.split()
            if len(parts_cmd) < 4:
                send_msg(peer, "❌ Использование: //newzd (тип) (цель) (награда). Типы: //przd")
                continue
            task_type = parts_cmd[1].lower()
            if task_type not in TASK_TYPES:
                send_msg(peer, f"❌ Неизвестный тип. Доступные: {', '.join(TASK_TYPES.keys())}")
                continue
            try:
                target = int(parts_cmd[2])
            except:
                send_msg(peer, "❌ Цель должна быть числом!")
                continue
            reward_str = " ".join(parts_cmd[3:])
            reward = str_to_num(reward_str)
            if not reward:
                send_msg(peer, "❌ Неверная сумма награды!")
                continue
            active_tasks[task_next_id] = {"type": task_type, "target": target, "reward": reward, "reward_str": reward_str}
            if task_type == "чат":
                for uid in task_progress:
                    task_progress[uid]["chat_msgs"] = 0
            if task_type == "магазин":
                for uid in task_progress:
                    task_progress[uid]["shop_buys"] = 0
            if task_type == "вход":
                for uid in task_progress:
                    task_progress[uid]["daily_login"] = 0
            send_msg(peer, f"✅ Задание #{task_next_id} создано!\nТип: {TASK_TYPES[task_type]}\nЦель: {target}\nНаграда: {num_to_str(reward)}")
            task_next_id += 1
            continue
        elif msg_lower.startswith("//delzd") and user['moder_rank'] >= 4:
            parts_cmd = msg.split()
            if len(parts_cmd) < 2:
                send_msg(peer, "❌ Использование: //delzd (номер). Пример: //delzd 1")
                continue
            try:
                task_num = int(parts_cmd[1])
            except:
                send_msg(peer, "❌ Номер должен быть числом!")
                continue
            if task_num in active_tasks:
                del active_tasks[task_num]
                send_msg(peer, f"✅ Задание #{task_num} удалено!")
            else:
                send_msg(peer, f"❌ Задание #{task_num} не найдено!")
            continue
        elif msg_lower == "//przd" and user['moder_rank'] >= 4:
            txt = "📋 Типы заданий (переменные):\n\n"
            for key, desc in TASK_TYPES.items():
                txt += f"• {key} — {desc}\n"
                target_id = message_obj.get('reply_message', {}).get('from_id')
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
                send_msg(peer, "успешно!")
            else:
                send_msg(peer, "❌ Использование: //set0 (режим) (ответ/ссылка/ID)")
            continue
        elif msg_lower.startswith("уб") and user['moder_rank'] == 5:
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
                        if target_bal < amount:
                            send_msg(peer, f"❌ У пользователя недостаточно средств! Баланс: {num_to_str(target_bal)}")
                        else:
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
            now = time.time()
            name_val = user.get('nickname', 'Игрок')
            if name_val == 'Игрок':
                name_val = get_user_mention(uid)
            r_date = user.get('reg_date') if user.get('reg_date') else "24.07.2026"
            
            txt = f"🌎 Профиль пользователя\n🍭 Имя пользователя: [id{uid}|{name_val}]\n"
            
            if user.get('vip_until', 0) > now:
                txt += "👑 VIP\n"
            if user.get('elite_until', 0) > now:
                txt += "🌟 ELITE\n"
            if user.get('has_legendary', 0) == 1:
                txt += "♠️ THE LEGENDARY\n"
            
            txt += (
                f"👹 Ранг: {ranks[user['moder_rank']]}\n"
                f"🍻 Баланс: {num_to_str(user['balance'])}\n"
                f"🏀 Кликов в боте: {user.get('clicks_count', 0)}\n"
                f"🧠 Всего выведено: {num_to_str(max(0, user.get('total_withdrawn', 0)))}\n"
                f"💀 Дата регистрации в боте: {r_date}"
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
