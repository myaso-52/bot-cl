import vk_api
import sys

TOKEN = "vk1.a.4NLW0LW3cobhYjBFzUQ1uvIF8Zn93a7G9W--YJ-URTkk9tf9Qt7TCXYFGv1pQ-o17M_1oRUhJMEV53edLMcBKwIB9F3JIRJl-Vi0YXAAT26pOvv3_XY5Yc6wj6PQmt8p2BVheWDb4GKoIsjBkTT9pyVWWTK3qv0LZwZJv7FOFqczW5BAc7X9Hub2eaYgeWt9txSLeBYlbB-MiTG47JBKkQ"

if len(sys.argv) < 3:
    print("Использование: python3 console_send.py ID_чата текст")
    sys.exit(1)

peer_id = int(sys.argv[1])
text = " ".join(sys.argv[2:])

vk = vk_api.VkApi(token=TOKEN).get_api()
vk.messages.send(peer_id=peer_id, message=text, random_id=0)
print(f"✅ Отправлено в {peer_id}: {text}")
