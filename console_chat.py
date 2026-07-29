import vk_api, time, sys, threading

TOKEN = "vk1.a.4NLW0LW3cobhYjBFzUQ1uvIF8Zn93a7G9W--YJ-URTkk9tf9Qt7TCXYFGv1pQ-o17M_1oRUhJMEV53edLMcBKwIB9F3JIRJl-Vi0YXAAT26pOvv3_XY5Yc6wj6PQmt8p2BVheWDb4GKoIsjBkTT9pyVWWTK3qv0LZwZJv7FOFqczW5BAc7X9Hub2eaYgeWt9txSLeBYlbB-MiTG47JBKkQ"
vk = vk_api.VkApi(token=TOKEN).get_api()

chats = {
    "1": 2000000001,
    "2": 2000000004,
    "3": 2000000003,
    "4": 2000000004
}

if len(sys.argv) < 2:
    print("python3 console_chat.py номер_чата (1-4)")
    print("1-Работяги 2-Модеры (2000000004) 3-Консоль 4-Жалобы")
    sys.exit(1)

key = sys.argv[1]
if key not in chats:
    print("1-Работяги 2-Модеры (2000000004) 3-Консоль 4-Жалобы")
    sys.exit(1)

chat_id = chats[key]
last_id = 0
try:
    hist = vk.messages.getHistory(peer_id=chat_id, count=1)
    if hist['items']:
        last_id = hist['items'][0]['id']
except:
    print(f"Нет доступа к чату {chat_id}")
    sys.exit(1)

print(f"Чат {chat_id}. /exit выход.")

def reader():
    global last_id
    while True:
        try:
            hist = vk.messages.getHistory(peer_id=chat_id, count=5)
            for msg in hist['items']:
                if msg['id'] <= last_id: break
                last_id = max(last_id, msg['id'])
                try:
                    user = vk.users.get(user_ids=msg['from_id'])[0]
                    name = f"{user['first_name']} {user['last_name']}"
                except:
                    name = f"ID{msg['from_id']}"
                print(f"\n[{name}]: {msg['text']}\n> ", end="", flush=True)
            time.sleep(1)
        except: pass

threading.Thread(target=reader, daemon=True).start()

while True:
    try:
        text = input()
        if text == "/exit": break
        if text: vk.messages.send(peer_id=chat_id, message=text, random_id=0)
    except KeyboardInterrupt: break
