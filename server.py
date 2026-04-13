#!/usr/bin/env python3
"""
Сервер для игры "Построй свой спутник!"
Запуск: python server.py
"""

import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

# ============================================================
#  ВСТАВЬ СВОЙ API КЛЮЧ СЮДА
# ============================================================
ANTHROPIC_API_KEY = "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"
# ============================================================

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
PORT = 8080


class Handler(SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/generate":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body)
        except Exception:
            self._json(400, {"error": "Неверный JSON"})
            return

        # Собираем промпт из ответов ребёнка
        answers = payload.get("answers", {})
        prompt = f"""Ты — весёлый AI для детей 9–14 лет из Узбекистана. Ребёнок придумал спутник!
Ответы:
1. Миссия: {answers.get('0', '?')}
2. Орбита: {answers.get('1', '?')}
3. Форма: {answers.get('2', '?')}
4. Суперсила: {answers.get('3', '?')}
5. Характер: {answers.get('4', '?')}

Верни ТОЛЬКО JSON без markdown и без лишних слов:
{{
  "name": "Название спутника (2-3 слова, звучит круто и по-космически, на русском)",
  "type": "Тип миссии (2-3 слова)",
  "description": "3 предложения для ребёнка — весело, с восклицаниями! Что делает, чем уникален и почему это круто.",
  "orbit_height": "например 520 км",
  "speed": "например 27 600 км/ч",
  "weight": "например 120 кг",
  "cameras": "например 3 HD-камеры",
  "tags": ["тег1", "тег2", "тег3"],
  "color1": "#hex яркий цвет корпуса",
  "color2": "#hex контрастный цвет панелей",
  "shape": "cube или small или cylinder или hex"
}}"""

        request_data = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(
            ANTHROPIC_URL,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text = "".join(
                    block.get("text", "")
                    for block in result.get("content", [])
                    if block.get("type") == "text"
                )
                text = text.replace("```json", "").replace("```", "").strip()
                satellite = json.loads(text)
                self._json(200, satellite)
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8")
            print(f"Anthropic error {e.code}: {err}")
            self._json(500, {"error": f"Ошибка Anthropic: {e.code}"})
        except Exception as e:
            print(f"Ошибка: {e}")
            self._json(500, {"error": str(e)})

    def do_GET(self):
        # Отдаём index.html для всех GET запросов кроме /api/
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
        super().do_GET()

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")


if __name__ == "__main__":
    if ANTHROPIC_API_KEY.startswith("sk-ant-XXX"):
        print("=" * 55)
        print("  ВНИМАНИЕ: вставь API ключ в переменную")
        print("  ANTHROPIC_API_KEY в файле server.py!")
        print("=" * 55)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n  Сервер запущен!")
    print(f"  Открой в браузере: http://localhost:{PORT}")
    print(f"  Для остановки нажми Ctrl+C\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Сервер остановлен.")
