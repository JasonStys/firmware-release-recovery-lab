"""File: Exercises the real Tk owner and actual loopback lifecycle with isolated workspaces.

No default browser or ordinary user profile opens. Modal messages/opener calls are observed;
widgets, listeners, SQLite locks and completion signals are real. Locations: docs/code-index.md.
"""

import json
import sys
import threading
import tkinter as tk

import pytest

from firmware_studio import desktop, resources
from firmware_studio.store import Profile


@pytest.fixture
def window(tmp_path, monkeypatch):
    engine, assets, _metadata = resources.load_resources()
    owner = desktop.Window(tmp_path / "workspace", engine, assets, no_browser=True)
    owner.root.withdraw()
    try:
        yield owner
    finally:
        if owner.host is not None and not owner.host.closed:
            owner.host.close()
        try:
            owner.root.destroy()
        except tk.TclError as error:
            assert "application has been destroyed" in str(error)


def test_real_owner_open_reopen_help_choice_and_completion(window, monkeypatch, tmp_path):
    from tkinter import messagebox

    opened, messages = [], []
    monkeypatch.setattr(desktop.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(messagebox, "showinfo", lambda *args, **kwargs: messages.append(args))
    assert not (tmp_path / "workspace").exists()
    window.select("")
    assert window.path.get() == str(tmp_path / "workspace")
    window.select(str(tmp_path / "chosen"))
    window.no_browser = False
    window.open_button.invoke()
    host = window.host
    assert host is not None and host.thread.is_alive()
    assert window.entry.instate(["disabled"]) and window.choose.instate(["disabled"])
    assert opened == [host.url]
    window.open()
    assert window.host is host and opened == [host.url, host.url]
    window.help()
    assert "plaintext" in messages[0][1] and "Export" in messages[0][1]
    window.quit()
    window.quit()
    window.open()
    assert window.closing and window.exit_button.instate(["disabled"])
    assert window.close_done.wait(3)
    assert host.closed and host.profile.descriptor == -1
    window.poll()
    reopened = Profile(tmp_path / "chosen")
    reopened.close()


def test_real_owner_failed_workspace_keeps_controls_retryable(window, tmp_path, monkeypatch):
    from tkinter import messagebox

    messages = []
    monkeypatch.setattr(messagebox, "showerror", lambda *args, **kwargs: messages.append(args))
    unknown = tmp_path / "unknown"
    unknown.mkdir()
    (unknown / "retained").write_text("inert")
    window.select(str(unknown))
    window.open()
    assert window.host is None and not window.entry.instate(["disabled"])
    assert "Unknown nonempty workspace" in messages[0][1]
    window.select(str(tmp_path / "corrected"))
    window.open()
    assert window.host is not None
    window.host.stop_requested.set()
    window.poll()
    assert window.closing and window.close_done.wait(3)
    window.poll()


def test_actual_gui_exit_waits_for_host_completion_not_a_timer(window, monkeypatch):
    window.open()
    actual_close = window.host.close
    entered, release = threading.Event(), threading.Event()

    def held():
        entered.set()
        if not release.wait(3):
            raise AssertionError("Test failed to release owned close")
        actual_close()

    monkeypatch.setattr(window.host, "close", held)
    window.quit()
    assert entered.wait(1)
    window.poll()
    assert window.root.winfo_exists() and not window.close_done.is_set()
    assert window.host.profile.descriptor >= 0
    release.set()
    assert window.close_done.wait(3)
    assert window.host.closed
    window.poll()


def test_owner_close_failure_stays_visible_non_success(window, monkeypatch):
    window.open()

    def failed():
        raise OSError("inert test close failure")

    monkeypatch.setattr(window.host, "close", failed)
    window.quit()
    assert window.close_done.wait(2)
    window.poll()
    assert window.root.winfo_exists() and window.host.profile.descriptor >= 0
    assert "did not complete" in window.status.get() and window.close_error is not None
    window.host.profile.close()
    window.host.server.shutdown()
    window.host.thread.join()
    window.host.server.server_close()
    window.host.closed = True


def test_exit_without_start_does_not_create_a_workspace(window, tmp_path):
    window.quit()
    assert not (tmp_path / "workspace").exists()


def test_real_minimum_window_keeps_open_help_exit_controls_visible(window):
    assert window.root.title() == "Firmware Release Recovery Workbench | Jason Stys | 0.2.1"
    window.root.deiconify()
    window.root.geometry("560x350")
    window.root.update()
    window.root.update_idletasks()
    for button in (window.open_button, window.exit_button):
        assert button.winfo_ismapped()
        assert button.winfo_rooty() >= window.root.winfo_rooty()
        assert (
            button.winfo_rooty() + button.winfo_height()
            <= window.root.winfo_rooty() + window.root.winfo_height()
        )
    window.root.withdraw()


def test_source_no_window_requires_explicit_profile(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["firmware", "--no-window", "--no-browser"])
    with pytest.raises(SystemExit) as error:
        desktop.run()
    assert error.value.code == 2


def test_real_no_window_entry_uses_owned_quit_and_explicit_workspace(tmp_path, monkeypatch, capsys):
    actual_start = desktop.start
    observed = []

    def start(*args):
        host = actual_start(*args)
        observed.append(host)
        host.stop_requested.set()
        return host

    monkeypatch.setattr(desktop, "start", start)
    monkeypatch.setattr(
        sys,
        "argv",
        ["firmware", "--no-window", "--no-browser", "--profile", str(tmp_path / "workspace")],
    )
    desktop.run()
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert rows[0]["event"] == "ready" and "capability" not in rows[0]
    assert rows[1]["event"] == "test-session" and rows[1]["capability"] == observed[0].capability
    assert observed[0].closed and observed[0].profile.descriptor == -1


def test_keyboard_interrupt_requests_actual_owned_drain_not_silent_success(tmp_path, monkeypatch):
    actual_start = desktop.start
    observed = []

    def start(*args):
        host = actual_start(*args)
        observed.append(host)

        def interrupted():
            raise KeyboardInterrupt

        monkeypatch.setattr(host.stop_requested, "wait", interrupted)
        return host

    monkeypatch.setattr(desktop, "start", start)
    monkeypatch.setattr(
        sys,
        "argv",
        ["firmware", "--no-window", "--no-browser", "--profile", str(tmp_path / "workspace")],
    )
    desktop.run()
    assert observed[0].stop_requested.is_set()
    assert observed[0].closed and observed[0].profile.descriptor == -1
