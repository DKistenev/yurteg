"""ЮрТэг — запуск как десктопное приложение (нативное окно)."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# Отключить tkinter в дочернем Streamlit-процессе (конфликтует с pywebview)
os.environ["YURTEG_DESKTOP"] = "1"


def _find_free_port() -> int:
    """Найти свободный порт."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 30.0) -> bool:
    """Ждать пока Streamlit сервер станет доступен."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def main():
    import webview  # noqa: late import — тяжёлый

    port = _find_free_port()
    app_dir = Path(__file__).parent

    # Запуск Streamlit в фоновом процессе
    streamlit_proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            str(app_dir / "main.py"),
            f"--server.port={port}",
            "--server.headless=true",
            "--server.address=localhost",
            "--browser.gatherUsageStats=false",
            "--browser.serverAddress=localhost",
        ],
        cwd=str(app_dir),
    )

    # Ждём сервер в отдельном потоке, потом открываем окно
    url = f"http://localhost:{port}"

    def on_closed():
        streamlit_proc.terminate()
        streamlit_proc.wait(timeout=5)

    # Ждём пока сервер поднимется
    if not _wait_for_server(port):
        print("Streamlit не запустился за 30 секунд")
        streamlit_proc.terminate()
        sys.exit(1)

    # Нативное окно
    window = webview.create_window(
        "ЮрТэг",
        url,
        width=1280,
        height=800,
        min_size=(900, 600),
    )
    window.events.closed += on_closed
    webview.start()


if __name__ == "__main__":
    main()
