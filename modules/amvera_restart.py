import requests
import os
import json

AMVERA_TOKEN = os.getenv("AMVERA_API_TOKEN", "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJtVmV0T3hCQlJhcWNpZHdnYUJROEF4UjcwMkk4QmtrRjRseXJWazFKU1BjIn0.eyJleHAiOjE4ODU2MTk2NzAsImlhdCI6MTc5MTAxMTY3MCwiYXV0aF90aW1lIjoxNzkxMDEwNjU0LCJqdGkiOiJvbnJ0bmE6ZGZmYmY2NjEtNGNiNy00M2NmLTA1MjctMDQxMjJhZWYzNDkyIiwiaXNzIjoiaHR0cHM6Ly9pZC5hbXZlcmEucnUvYXV0aC9yZWFsbXMvYW12ZXJhIiwiYXVkIjpbImFjY291bnQiLCJvcGVubWNwIl0sInN1YiI6IjNjODVjOGUzLTg4ZDEtNDQ1Ni05NTJhLTQ1M2U1YTdhMmFlZCIsInR5cCI6IkJlYXJlciIsImF6cCI6ImFtdmVyYS1hcGkiLCJzaWQiOiJJTGo2dEFsWW4wRFY2YlpjRENDcmVybzMiLCJhY3IiOiIxIiwiYWxsb3dlZC1vcmlnaW5zIjpbIi8qIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJvZmZsaW5lX2FjY2VzcyIsInVtYV9hdXRob3JpemF0aW9uIiwiZGVmYXVsdC1yb2xlcy1hbXZlcmEiXX0sInJlc291cmNlX2FjY2VzcyI6eyJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCBlbWFpbCBwaG9uZSBwcm9maWxlIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInByZWZlcnJlZF91c2VybmFtZSI6InlhdGFnYW5ubiIsImVtYWlsIjoibGViZWRldi5hbGVrczEyQGdtYWlsLmNvbSJ9.MotH4MJnQMHFjc9w2vBiC8lHfPGlUlc_rJPucey-rV-hl-3pyWlkKRwanQ-19Zs-8YQ1A1Lv1Zv7Xg-zDVpINvw7XqysjtnDuQuIomTAPkT1IAT8CvDkbWh3AVwu8-sgReaIISoOozOsKNqrYg8y7IxrzD7K_3JwnjYctOKeknjbj8SnZKvLE8iGolN7h3-JRq4dnlkmwDCg9T2k08haSknYLwxcNhAdqV99q5EGnaqC_OKVKlldbJnnqFqdh_1ivRywiD8j5PyyzikEfQv6IeE5UduSt27BibTyOGqsdTtw1gbWDoH0xWFw5O1dq8EmxYqbpQ9auB3irBZeO-Q9LA")
AMVERA_URL = "https://openmcp.msk0.amvera.ru/mcp"
PROJECT_NAME = "bot-cl"


def _create_session():
    """Создаёт MCP-сессию, возвращает headers с session_id"""
    headers = {
        "Authorization": f"Bearer {AMVERA_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    resp = requests.post(AMVERA_URL, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "bot-cl", "version": "1.0"}
        }
    }, headers=headers, timeout=10)
    
    session_id = resp.headers.get("Mcp-Session-Id")
    if not session_id:
        return None
    
    headers["Mcp-Session-Id"] = session_id
    
    # Подтверждаем инициализацию
    requests.post(AMVERA_URL, json={
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }, headers=headers, timeout=10)
    
    return headers


def _call_tool(tool_name, arguments=None):
    """Вызывает инструмент MCP"""
    headers = _create_session()
    if not headers:
        return False, "Не удалось создать сессию MCP"
    
    resp = requests.post(AMVERA_URL, json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        }
    }, headers=headers, timeout=15)
    
    # Парсим SSE-ответ
    for line in resp.text.split('\n'):
        if line.startswith('data:'):
            try:
                data = json.loads(line[5:])
                if 'result' in data:
                    return True, data['result']
                elif 'error' in data:
                    return False, data['error']
            except:
                pass
    
    return False, resp.text[:300]


def restart_project():
    """Перезапускает проект bot-cl на Amvera"""
    return _call_tool("restartProject", {"slug": PROJECT_NAME})


def rebuild_project():
    """Пересобирает проект (полный rebuild)"""
    return _call_tool("rebuildProject", {"slug": PROJECT_NAME})
