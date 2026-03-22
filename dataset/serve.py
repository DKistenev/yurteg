"""Локальный сервер для ревьюера датасета.

Раздаёт статические файлы (review.html, labeled_data.jsonl)
и принимает POST /save для сохранения проверенного датасета обратно в папку.

Запуск:
    cd yurteg/dataset
    python serve.py

Откроется автоматически: http://localhost:8080/review.html
"""
import json
import webbrowser
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PORT = 8080
DIR = Path(__file__).parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIR), **kwargs)

    def do_POST(self):
        if self.path == "/save":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")

            # Имя файла из заголовка, по умолчанию reviewed
            filename = self.headers.get("X-Filename", "labeled_data_reviewed.jsonl")
            # Защита от path traversal
            filename = Path(filename).name
            out_path = DIR / filename
            out_path.write_text(body, encoding="utf-8")

            # Считаем сколько записей
            count = sum(1 for line in body.strip().split("\n") if line.strip())

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {"ok": True, "count": count, "path": str(out_path)}
            self.wfile.write(json.dumps(resp).encode())

            print(f"  Сохранено {count} записей → {out_path.name}")
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        # Тихий лог — только важное
        if "POST" in str(args):
            super().log_message(format, *args)


def main():
    server = HTTPServer(("localhost", PORT), Handler)
    url = f"http://localhost:{PORT}/review.html"
    print(f"Сервер запущен: {url}")
    print("Для остановки: Ctrl+C")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлен.")
        server.server_close()


if __name__ == "__main__":
    main()
