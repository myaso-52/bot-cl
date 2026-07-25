import requests
import json

API_URL = "https://api.badbotik.ru/api/"
API_TOKEN = "e79014a73e87a11c41a1c631bc9012b4"

def get_balance():
    try:
        r = requests.post(f"{API_URL}balance", json={"token": API_TOKEN}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("answer", {}).get("balance", 0)
    except Exception as e:
        print(f"BadBotik API (баланс): {e}")
    return None

def pay_user(user_id, amount):
    try:
        r = requests.post(f"{API_URL}pay", json={"token": API_TOKEN, "user": user_id, "count": amount}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("answer") == "success":
                return True
    except Exception as e:
        print(f"BadBotik API (платёж): {e}")
    return False

def get_history(count=5):
    try:
        r = requests.post(f"{API_URL}getHistory", json={"token": API_TOKEN, "count": count}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("answer", {}).get("history", [])
    except Exception as e:
        print(f"BadBotik API (история): {e}")
    return []
