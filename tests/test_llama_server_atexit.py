"""Tests: atexit.register вызывается ровно один раз в LlamaServerManager.start()."""
from unittest.mock import patch, MagicMock


def test_atexit_registered_once_on_first_attempt():
    """atexit.register вызывается ровно 1 раз при успешном старте на первой попытке."""
    from services.llama_server import LlamaServerManager
    mgr = LlamaServerManager(port=19090)
    with patch("subprocess.Popen") as mock_popen, \
         patch("urllib.request.urlopen") as mock_url, \
         patch("atexit.register") as mock_atexit, \
         patch.object(mgr, "is_running", return_value=False):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        mock_url.return_value = mock_resp
        mgr.start()
        assert mock_atexit.call_count == 1


def test_atexit_not_registered_on_failure():
    """atexit.register НЕ вызывается если сервер не запустился ни на одном порту."""
    from services.llama_server import LlamaServerManager
    mgr = LlamaServerManager(port=19091)
    with patch("subprocess.Popen") as mock_popen, \
         patch("urllib.request.urlopen", side_effect=Exception("refused")), \
         patch("atexit.register") as mock_atexit, \
         patch.object(mgr, "is_running", return_value=False), \
         patch("time.sleep"):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        mgr.start()
        assert mock_atexit.call_count == 0
