"""Тесты для services/startup_checks.py — проверка интернета и места на диске."""
import shutil
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from services.startup_checks import (
    REQUIRED_SPACE_GB,
    check_disk_space,
    check_internet,
)


# ── check_internet ──────────────────────────────────────────────────────────


class TestCheckInternet:
    """Проверка доступности интернета через HEAD-запросы."""

    @patch("services.startup_checks.urllib.request.urlopen")
    def test_returns_true_when_host_reachable(self, mock_urlopen):
        """Если хотя бы один хост отвечает — True."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        assert check_internet() is True

    @patch("services.startup_checks.urllib.request.urlopen")
    def test_returns_false_when_all_hosts_fail(self, mock_urlopen):
        """Если все хосты недоступны — False."""
        mock_urlopen.side_effect = URLError("No internet")

        assert check_internet() is False

    @patch("services.startup_checks.urllib.request.urlopen")
    def test_returns_true_if_second_host_succeeds(self, mock_urlopen):
        """Первый хост падает, второй отвечает — True."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [URLError("fail"), mock_resp]

        assert check_internet() is True

    @patch("services.startup_checks.urllib.request.urlopen")
    def test_handles_timeout_error(self, mock_urlopen):
        """Таймаут тоже считается как нет интернета."""
        mock_urlopen.side_effect = TimeoutError("timeout")

        assert check_internet() is False

    @patch("services.startup_checks.urllib.request.urlopen")
    def test_handles_os_error(self, mock_urlopen):
        """OSError (DNS failure и т.п.) — False."""
        mock_urlopen.side_effect = OSError("DNS failed")

        assert check_internet() is False


# ── check_disk_space ────────────────────────────────────────────────────────


class TestCheckDiskSpace:
    """Проверка свободного места на диске."""

    @patch("services.startup_checks.shutil.disk_usage")
    def test_enough_space_returns_true(self, mock_usage, tmp_path):
        """2 ГБ свободно при пороге 1.5 — (True, 2.0)."""
        free_bytes = int(2.0 * 1024**3)
        mock_usage.return_value = shutil._ntuple_diskusage(
            total=int(100 * 1024**3),
            used=int(98 * 1024**3),
            free=free_bytes,
        )

        ok, free_gb = check_disk_space(tmp_path)
        assert ok is True
        assert free_gb == 2.0

    @patch("services.startup_checks.shutil.disk_usage")
    def test_not_enough_space_returns_false(self, mock_usage, tmp_path):
        """0.5 ГБ свободно при пороге 1.5 — (False, 0.5)."""
        free_bytes = int(0.5 * 1024**3)
        mock_usage.return_value = shutil._ntuple_diskusage(
            total=int(100 * 1024**3),
            used=int(99.5 * 1024**3),
            free=free_bytes,
        )

        ok, free_gb = check_disk_space(tmp_path)
        assert ok is False
        assert free_gb == 0.5

    @patch("services.startup_checks.shutil.disk_usage")
    def test_exact_threshold_returns_true(self, mock_usage, tmp_path):
        """Ровно 1.5 ГБ — (True, 1.5)."""
        free_bytes = int(1.5 * 1024**3)
        mock_usage.return_value = shutil._ntuple_diskusage(
            total=int(100 * 1024**3),
            used=int(98.5 * 1024**3),
            free=free_bytes,
        )

        ok, free_gb = check_disk_space(tmp_path)
        assert ok is True
        assert free_gb == 1.5

    def test_creates_directory_if_missing(self, tmp_path):
        """Если директории нет — создаёт её."""
        target = tmp_path / "nonexistent" / "subdir"
        assert not target.exists()

        # Реальный disk_usage — место точно > 1.5 ГБ на dev-машине
        ok, free_gb = check_disk_space(target)
        assert target.exists()
        assert ok is True
        assert free_gb > 0

    def test_required_space_constant(self):
        """Константа REQUIRED_SPACE_GB = 1.5."""
        assert REQUIRED_SPACE_GB == 1.5
