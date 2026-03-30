"""Менеджер загрузки и запуска llama-server для локальной LLM."""
import atexit
import logging
import platform
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ── Константы ────────────────────────────────────────────────────────────────

YURTEG_DIR = Path.home() / ".yurteg"

MODEL_REPO = "SuperPuperD/yurteg-1.5b-v3-gguf"
MODEL_FILENAME = "yurteg-v3-Q4_K_M.gguf"

DEFAULT_PORT = 8080

# Актуальный релиз llama.cpp (b5606 — стабильный, проверен на macOS/Linux/Windows)
_LLAMA_RELEASE = "b5606"
_LLAMA_BASE_URL = (
    f"https://github.com/ggerganov/llama.cpp/releases/download/{_LLAMA_RELEASE}"
)

# Карта платформа → архив → имя бинарника внутри архива
_PLATFORM_MAP = {
    ("Darwin", "arm64"):  (f"llama-{_LLAMA_RELEASE}-bin-macos-arm64.zip",   "llama-server"),
    ("Darwin", "x86_64"): (f"llama-{_LLAMA_RELEASE}-bin-macos-x64.zip",     "llama-server"),
    ("Linux",  "x86_64"): (f"llama-{_LLAMA_RELEASE}-bin-ubuntu-x64.zip",    "llama-server"),
    ("Windows","AMD64"):   (f"llama-{_LLAMA_RELEASE}-bin-win-avx2-x64.zip",  "llama-server.exe"),
    ("Windows","x86_64"):  (f"llama-{_LLAMA_RELEASE}-bin-win-avx2-x64.zip",  "llama-server.exe"),
}

_BINARY_NAME = "llama-server.exe" if platform.system() == "Windows" else "llama-server"


def _health_endpoint(port: int) -> str:
    return f"http://localhost:{port}/health"


def _download_with_progress(
    url: str,
    dest: Path,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> None:
    """Скачивает файл с URL в dest, вызывает on_progress(fraction, msg)."""
    logger.info("Скачиваю: %s → %s", url, dest)
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk = 65536  # 64 KB
        with open(dest, "wb") as f:
            while True:
                data = resp.read(chunk)
                if not data:
                    break
                f.write(data)
                downloaded += len(data)
                if on_progress and total > 0:
                    on_progress(downloaded / total, f"Скачано {downloaded // 1_048_576} МБ")
    if on_progress:
        on_progress(1.0, "Загрузка завершена")


class LlamaServerManager:
    """Управляет скачиванием модели/бинарника и lifecycle llama-server процесса."""

    def __init__(self, port: int = DEFAULT_PORT) -> None:
        self._port = port
        self._process: Optional[subprocess.Popen] = None  # type: ignore[type-arg]
        self._yurteg_dir = YURTEG_DIR
        self._yurteg_dir.mkdir(parents=True, exist_ok=True)

    # ── Публичные свойства ───────────────────────────────────────────────────

    @property
    def base_url(self) -> str:
        """OpenAI-совместимый endpoint llama-server."""
        return f"http://localhost:{self._port}/v1"

    # ── Скачивание модели ────────────────────────────────────────────────────

    def ensure_model(
        self,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """Проверяет наличие GGUF модели в ~/.yurteg/, скачивает если отсутствует.

        Использует huggingface_hub для надёжного скачивания с кешированием.

        Returns:
            Path к файлу модели.
        """
        model_path = self._yurteg_dir / MODEL_FILENAME
        if model_path.exists():
            logger.info("Модель уже скачана: %s", model_path)
            return model_path

        logger.info("Модель не найдена, скачиваю с HuggingFace: %s/%s", MODEL_REPO, MODEL_FILENAME)
        if on_progress:
            on_progress(0.0, "Подготовка к загрузке модели (~940 МБ)...")

        try:
            from huggingface_hub import hf_hub_download  # type: ignore[import-untyped]

            downloaded = hf_hub_download(
                repo_id=MODEL_REPO,
                filename=MODEL_FILENAME,
                local_dir=str(self._yurteg_dir),
            )
            result = Path(downloaded)
        except Exception as exc:
            logger.error("Ошибка загрузки модели через huggingface_hub: %s", exc)
            raise RuntimeError(f"Не удалось скачать модель: {exc}") from exc

        if on_progress:
            on_progress(1.0, "Модель загружена")

        logger.info("Модель скачана: %s", result)
        return result

    # ── Скачивание бинарника ─────────────────────────────────────────────────

    def ensure_server_binary(
        self,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """Проверяет наличие llama-server бинарника, скачивает с GitHub Releases если нет.

        Returns:
            Path к бинарнику.
        """
        binary_path = self._yurteg_dir / _BINARY_NAME
        if binary_path.exists():
            logger.info("llama-server бинарник уже скачан: %s", binary_path)
            return binary_path

        system = platform.system()
        machine = platform.machine()
        key = (system, machine)

        if key not in _PLATFORM_MAP:
            raise RuntimeError(
                f"Платформа {system}/{machine} не поддерживается. "
                "Скачайте llama-server вручную: https://github.com/ggerganov/llama.cpp/releases"
            )

        archive_name, binary_in_archive = _PLATFORM_MAP[key]
        url = f"{_LLAMA_BASE_URL}/{archive_name}"

        logger.info("Скачиваю llama-server: %s", url)
        if on_progress:
            on_progress(0.0, f"Загрузка llama-server для {system}/{machine}...")

        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_path = Path(tmp_dir) / archive_name
            _download_with_progress(url, archive_path, on_progress)

            # Распаковываем и ищем бинарник
            with zipfile.ZipFile(archive_path) as zf:
                # Бинарник может лежать в build/bin/ или в корне архива
                names = zf.namelist()
                matched = [
                    n for n in names
                    if n.endswith(f"/{binary_in_archive}") or n == binary_in_archive
                ]
                if not matched:
                    raise RuntimeError(
                        f"Бинарник {binary_in_archive!r} не найден в архиве {archive_name}. "
                        f"Файлы в архиве: {names[:10]}"
                    )
                src_name = matched[0]
                zf.extract(src_name, tmp_dir)
                extracted = Path(tmp_dir) / src_name

            shutil.copy2(extracted, binary_path)

        # chmod +x на Unix
        if system != "Windows":
            binary_path.chmod(binary_path.stat().st_mode | 0o111)

        # macOS: снимаем quarantine флаг, иначе Gatekeeper блокирует запуск
        if system == "Darwin":
            subprocess.run(
                ["xattr", "-dr", "com.apple.quarantine", str(binary_path)],
                capture_output=True,
            )
            logger.info("Quarantine флаг снят: %s", binary_path)

        if on_progress:
            on_progress(1.0, "llama-server готов")

        logger.info("llama-server установлен: %s", binary_path)
        return binary_path

    # ── Управление процессом ─────────────────────────────────────────────────

    def start(self) -> None:
        """Запускает llama-server как subprocess.

        Ожидает готовности через /health endpoint (таймаут 30 сек).
        При порте занятом пробует port+1 (до 3 раз).
        Регистрирует atexit handler для корректного завершения.
        Грамматика передаётся через тело запроса (per-request), не через флаг сервера.
        """
        if self.is_running():
            logger.info("llama-server уже запущен на порту %d", self._port)
            return

        try:
            model_path = self._yurteg_dir / MODEL_FILENAME
            binary_path = self._yurteg_dir / _BINARY_NAME
        except Exception as exc:
            logger.warning("Ошибка при подготовке путей llama-server: %s", exc)
            return

        if not model_path.exists():
            logger.warning("Модель не найдена: %s — llama-server не запущен", model_path)
            return

        if not binary_path.exists():
            logger.warning("Бинарник не найден: %s — llama-server не запущен", binary_path)
            return

        cmd_base = [
            str(binary_path),
            "-m", str(model_path),
            "-c", "4096",
            "-n", "512",
            "--temp", "0.05",
            "--min-p", "0.05",
            "--top-p", "1.0",
            "--repeat-penalty", "1.1",
        ]

        # Попытки с резервными портами
        for attempt in range(3):
            port = self._port + attempt
            cmd = cmd_base + ["--port", str(port)]

            logger.info("Запускаю llama-server (попытка %d) на порту %d", attempt + 1, port)
            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                # Ожидание готовности
                health_url = _health_endpoint(port)
                deadline = time.time() + 30.0
                started = False
                while time.time() < deadline:
                    if self._process.poll() is not None:
                        logger.warning("llama-server завершился неожиданно (код %d)", self._process.returncode)
                        break
                    try:
                        with urllib.request.urlopen(health_url, timeout=2) as resp:  # noqa: S310
                            if resp.status == 200:
                                started = True
                                break
                    except Exception:
                        pass
                    time.sleep(0.5)

                if started:
                    self._port = port
                    atexit.register(self.stop)
                    logger.info("llama-server запущен на порту %d (PID %d)", port, self._process.pid)
                    return
                else:
                    logger.warning("llama-server не ответил за 30 сек на порту %d", port)
                    self.stop()

            except OSError as exc:
                logger.warning("Ошибка запуска llama-server на порту %d: %s", port, exc)
                self._process = None

        logger.warning(
            "llama-server не удалось запустить ни на одном порту (%d–%d). "
            "Будет использован облачный провайдер.",
            self._port,
            self._port + 2,
        )

    def stop(self) -> None:
        """Останавливает llama-server процесс."""
        if self._process is None:
            return
        try:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
        except Exception as exc:
            logger.warning("Ошибка при остановке llama-server: %s", exc)
        finally:
            self._process = None
            logger.info("llama-server остановлен")

    def is_running(self) -> bool:
        """Проверяет что llama-server запущен и отвечает на /health."""
        if self._process is None:
            return False
        if self._process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(_health_endpoint(self._port), timeout=2) as resp:  # noqa: S310
                return resp.status == 200
        except Exception:
            # Процесс мог умереть между poll() и health check
            if self._process is not None and self._process.poll() is not None:
                self._process = None
            return False
