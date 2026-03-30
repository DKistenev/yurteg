"""Regression tests for desktop startup guards and lock UX."""

from __future__ import annotations

import sys
import types


def test_should_start_llama_on_regular_launch():
    """Completed onboarding should allow normal llama startup path."""
    from services.app_boot import should_start_llama_on_startup

    assert should_start_llama_on_startup({"first_run_completed": True}) is True


def test_should_not_start_llama_during_first_run():
    """First-run onboarding owns llama boot/download flow."""
    from services.app_boot import should_start_llama_on_startup

    assert should_start_llama_on_startup({}) is False
    assert should_start_llama_on_startup({"first_run_completed": False}) is False


def test_show_already_running_message_uses_gui_when_available(monkeypatch):
    """Packaged desktop build should show a visible message box."""
    from services import instance_lock

    events: list[object] = []

    class FakeTk:
        def withdraw(self):
            events.append("withdraw")

        def attributes(self, *args):
            events.append(("attributes", args))

        def destroy(self):
            events.append("destroy")

    fake_messagebox = types.SimpleNamespace(
        showinfo=lambda title, message, parent=None: events.append(
            ("showinfo", title, message, parent is not None)
        )
    )
    fake_tk_module = types.SimpleNamespace(
        Tk=lambda: FakeTk(),
        messagebox=fake_messagebox,
    )

    monkeypatch.setitem(sys.modules, "tkinter", fake_tk_module)

    instance_lock._show_already_running_message()

    assert "withdraw" in events
    assert "destroy" in events
    assert any(
        event == ("showinfo", "ЮрТэг", "ЮрТэг уже запущен.\nПереключитесь в открытое окно приложения.", True)
        for event in events
    )


def test_show_already_running_message_falls_back_to_stderr(monkeypatch, capsys):
    """If GUI dialog is unavailable, the user still gets a message."""
    from services import instance_lock

    original_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tkinter":
            raise RuntimeError("tk unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)

    instance_lock._show_already_running_message()

    captured = capsys.readouterr()
    assert "ЮрТэг уже запущен." in captured.err


def test_acquire_instance_lock_exits_cleanly_when_lock_is_busy(monkeypatch):
    """Busy lock should show message, close fd, and exit with code 1."""
    from services import instance_lock

    monkeypatch.setattr(
        instance_lock.Path,
        "mkdir",
        lambda self, parents=True, exist_ok=True: None,
    )
    monkeypatch.setattr(instance_lock.os, "open", lambda path, flags: 123)

    closed_fds: list[int] = []
    monkeypatch.setattr(instance_lock.os, "close", lambda fd: closed_fds.append(fd))

    shown_messages: list[str] = []
    monkeypatch.setattr(
        instance_lock,
        "_show_already_running_message",
        lambda: shown_messages.append("shown"),
    )

    if sys.platform == "win32":
        fake_msvcrt = types.SimpleNamespace(
            LK_NBLCK=1,
            locking=lambda fd, mode, size: (_ for _ in ()).throw(OSError("busy")),
        )
        monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    else:
        fake_fcntl = types.SimpleNamespace(
            LOCK_EX=1,
            LOCK_NB=2,
            flock=lambda fd, flags: (_ for _ in ()).throw(OSError("busy")),
        )
        monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)

    try:
        instance_lock.acquire_instance_lock()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("Expected SystemExit when lock is busy")

    assert closed_fds == [123]
    assert shown_messages == ["shown"]
