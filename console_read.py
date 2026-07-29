import vk_api
import time

TOKEN = "vk1.a.4NLW0LW3cobhYjBFzUQ1uvIF8Zn93a7G9W--YJ-URTkk9tf9Qt7TCXYFGv1pQ-o17M_1oRUhJMEV53edLMcBKwIB9F3JIRJl-Vi0YXAAT26pOvv3_XY5Yc6wj6PQmt8p2BVheWDb4GKoIsjBkTT9pyVWWTK3qv0LZwZJv7FOFqczW5BAc7X9Hub2eaYgeWt9txSLeBYlbB-MiTG47JBKkQ"
vk = vk_api.VkApi(token=TOKEN).get_api()

import sys
if len(sys.argv) < 2:
    print("Использование: python3 console_read.py ID_чата")
    sys.exit(1)

chat_id = int(sys.argv[1])
last_id = 0

# Получаем последнее сообщение
hist = vk.messages.getHistory(peer_id=chat_id, count=1)
if hist['items']:
    last_id = hist['items'][0]['id']

print(f"Слушаю чат {chat_id}... (Ctrl+C выход)")

while True:
    try:
        hist = vk.messages.getHistory(peer_id=chat_id, count=5)
        for msg in hist['items']:
            if msg['id'] <= last_id:
                break
            last_id = max(last_id, msg['id'])
            from_id = msg['from_id']
            text = msg['text']
            try:
                user = vk.users.get(user_ids=from_id)[0]
                name = f"{user['first_name']} {user['last_name']}"
            except:
                name = f"ID{from_id}"
            print(f"[{name}]: {text}")
        time.sleep(1)
    except KeyboardInterrupt:
        break
    except:
        pass
