import os
import sys
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
PORT = int(os.environ.get("PORT", 8080))


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

        if not ANTHROPIC_API_KEY:
            self._json(500, {"error": "API ключ не настроен"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body)
        except Exception:
            self._json(400, {"error": "Неверный JSON"})
            return

        answers = payload.get("answers", {})
        lang = payload.get("lang", "ru")
        sat_name = answers.get('4', 'My Satellite')

        lang_instructions = {
            "ru": "Отвечай ТОЛЬКО на русском языке. Используй весёлый стиль для детей.",
            "uz": "Javobni FAQAT o'zbek tilida yoz. Bolalar uchun quvnoq uslubda yoz.",
            "en": "Respond ONLY in English. Use a fun, exciting style for kids.",
        }
        lang_instr = lang_instructions.get(lang, lang_instructions["ru"])

        prompt = f"""You are a fun AI assistant for kids aged 9-14. A child has designed a satellite!
Their choices:
1. Mission: {answers.get('0', '?')}
2. Orbit: {answers.get('1', '?')}
3. Colour: {answers.get('2', '?')}
4. Superpower: {answers.get('3', '?')}
5. Name chosen by the child: "{sat_name}"

{lang_instr}

Return ONLY valid JSON, no markdown, no extra text:
{{
  "name": "{sat_name}",
  "type": "mission type (2-3 words)",
  "description": "3 fun sentences for a child — exciting, with exclamations! Mention the satellite name.",
  "orbit_height": "e.g. 520 km",
  "speed": "e.g. 27 600 km/h",
  "weight": "e.g. 120 kg",
  "cameras": "e.g. 3 HD cameras",
  "tags": ["tag1", "tag2", "tag3"],
  "shape": "cube or small or cylinder or hex"
}}"""

        request_data = json.dumps({
            "model": ANTHROPIC_MODEL,
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
                raw = resp.read().decode("utf-8")
                result = json.loads(raw)
                print(f"Claude response type={result.get('type')} stop_reason={result.get('stop_reason')}")

                # Check for API-level error in response body
                if result.get("type") == "error":
                    err_msg = result.get("error", {}).get("message", "unknown")
                    print(f"API error in body: {err_msg}")
                    self._json(500, {"error": f"Claude: {err_msg}"})
                    return

                text = "".join(
                    block.get("text", "")
                    for block in result.get("content", [])
                    if block.get("type") == "text"
                )
                text = text.replace("```json", "").replace("```", "").strip()

                if not text:
                    print(f"Empty text. Full raw: {raw[:800]}")
                    self._json(500, {"error": "Пустой ответ от Claude"})
                    return

                satellite = json.loads(text)
                self._json(200, satellite)

        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8")
            print(f"Anthropic HTTP error {e.code}: {err}")
            self._json(500, {"error": f"Ошибка Anthropic: {e.code} — {err[:200]}"})
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            self._json(500, {"error": f"Ошибка парсинга: {e}"})
        except Exception as e:
            print(f"Ошибка: {e}")
            self._json(500, {"error": str(e)})

    def do_GET(self):
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
    print(f"Запуск на 0.0.0.0:{PORT}")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Сервер запущен на порту {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Сервер остановлен.")
