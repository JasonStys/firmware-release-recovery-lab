"""File: Owns the native workspace chooser, browser and normally drained loopback application.

run opens one explicit workspace; Window retains its lock while server/engine work completes.
No timer declares a still-running child finished. Variables/locations: docs/code-index.md.
"""

import argparse
import json
import threading
import webbrowser
from pathlib import Path

from firmware_studio import __version__
from firmware_studio.resources import load_resources
from firmware_studio.server import Host
from firmware_studio.store import Profile, default_directory


def ready(host: Host):
    "Emit readiness for this actual prebound owner only; the capability is never printed to logs."
    print(
        json.dumps(
            {
                "event": "ready",
                "product": "firmware-release-recovery-lab",
                "version": __version__,
                "url": host.origin,
                "nonce": host.nonce,
                "engine": host.engine.identity,
            }
        ),
        flush=True,
    )


def start(directory: Path, engine, assets) -> Host:
    """Acquire the admitted workspace only after packaged engine/resources were verified."""
    profile = Profile(directory)
    try:
        host = Host(profile, engine, assets)
        host.start()
    except BaseException:
        profile.close()
        raise
    ready(host)
    return host


class Window:
    """The native owner remains visible until normal work actually releases socket and workspace."""

    def __init__(self, directory: Path, engine, assets, no_browser: bool):
        """Create bounded profile/Open/Help/Exit controls without initializing a default profile."""
        import tkinter as tk
        from tkinter import filedialog, ttk

        self.root = tk.Tk()
        self.root.title("Firmware Release Recovery Workbench | Jason Stys | 0.2.0")
        self.root.geometry("680x390")
        self.root.minsize(560, 350)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.host = None
        self.no_browser = no_browser
        self.closing = False
        self.close_done = threading.Event()
        self.close_error = None
        self.engine, self.assets = engine, assets
        content = ttk.Frame(self.root, padding=18)
        content.pack(fill="both", expand=True)
        ttk.Label(
            content, text="Firmware Release Recovery Workbench", font=("Segoe UI", 18, "bold")
        ).pack(anchor="w")
        ttk.Label(
            content,
            text="Jason Stys | offline A/B release, rollback and recovery rehearsals",
        ).pack(anchor="w", pady=8)
        ttk.Label(
            content,
            text="Workspace outside application files (empty folder or this app's saved workspace)",
            wraplength=610,
        ).pack(anchor="w")
        self.path = tk.StringVar(value=str(directory))
        self.entry = ttk.Entry(content, textvariable=self.path)
        self.entry.pack(fill="x", pady=8)
        self.choose = ttk.Button(
            content,
            text="Choose workspace folder",
            command=lambda: self.select(filedialog.askdirectory(parent=self.root)),
        )
        self.choose.pack(anchor="w")
        self.status = tk.StringVar(
            value=(
                "Open starts this actual app. No compiler, Docker, accounts or "
                "remote service is required."
            )
        )
        ttk.Label(content, textvariable=self.status, wraplength=610).pack(fill="x", pady=14)
        controls = ttk.Frame(self.root, padding=(18, 8, 18, 16))
        controls.pack(side="bottom", fill="x")
        self.open_button = ttk.Button(controls, text="Open application", command=self.open)
        self.open_button.pack(side="left")
        ttk.Button(controls, text="Help and privacy", command=self.help).pack(side="left", padx=12)
        self.exit_button = ttk.Button(controls, text="Exit", command=self.quit)
        self.exit_button.pack(side="right")
        self.root.after(100, self.poll)

    def select(self, value: str):
        if value:
            self.path.set(value)

    def open(self):
        "Retry failed initialization; reopen the existing owned app without replacing it."
        from tkinter import messagebox

        if self.closing:
            return
        try:
            if self.host is None:
                self.host = start(Path(self.path.get()), self.engine, self.assets)
                self.entry.configure(state="disabled")
                self.choose.configure(state="disabled")
            if not self.no_browser:
                webbrowser.open(self.host.url)
            self.status.set(
                "App is running on its own loopback listener. Open reconnects "
                "this browser session; Exit waits for pending work."
            )
        except (OSError, ValueError) as error:
            messagebox.showerror("Workspace could not open", str(error), parent=self.root)

    def help(self):
        from tkinter import messagebox

        messagebox.showinfo(
            "Help and privacy",
            (
                "Choose an empty external workspace, then Open. Edit fictional devices, "
                "inert release images and ordered A/B transitions; inspect actual states "
                "and interruption evidence. Export records and back up the stopped "
                "workspace. Imported results are rerun, not trusted. History is "
                "plaintext for this OS user; no accounts, telemetry, live hardware "
                "or firmware flashing. The demonstration signing key is public. "
                "Keep this window open while work finishes."
                " Source/contact: github.com/JasonStys/firmware-release-recovery-lab"
            ),
            parent=self.root,
        )

    def quit(self):
        "Repeated Close cannot release a draining server; completion closes the window."
        if self.closing:
            return
        if self.host is None:
            self.root.destroy()
            return
        self.closing = True
        self.open_button.configure(state="disabled")
        self.exit_button.configure(state="disabled")
        self.status.set(
            "Closing safely: waiting for owned experiments and HTTP handlers. "
            "Saved workspace ownership is retained."
        )
        threading.Thread(target=self.drain, name="firmware-drain").start()

    def drain(self):
        """The GUI thread stays responsive while the actual server closes; failures stay visible."""
        try:
            self.host.close()
        except (OSError, RuntimeError) as error:
            self.close_error = error
        finally:
            self.close_done.set()

    def poll(self):
        if self.closing and self.close_done.is_set():
            if self.close_error is None:
                self.root.destroy()
                return
            self.status.set(
                "Close did not complete. Keep this window open; workspace was "
                "not reset. Reopen the app only after this owner has exited."
            )
            self.root.title("Firmware Release Recovery Workbench | close failed")
            return
        if self.host is not None and self.host.stop_requested.is_set():
            self.quit()
        self.root.after(100, self.poll)


def run():
    "Normal launch presents the owner; no-window acceptance requires an explicit path."
    parser = argparse.ArgumentParser(
        description="Firmware Release Recovery Workbench native application"
    )
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-window", action="store_true")
    args = parser.parse_args()
    engine, assets, _metadata = load_resources()
    if args.no_window:
        if args.profile is None:
            parser.error("--no-window requires an explicit isolated --profile")
        host = start(args.profile, engine, assets)
        # Test helpers learn the owned capability via this explicit test-only stdout record;
        # ordinary launch logs/readiness omit it. It is never written to saved workspace data.
        print(json.dumps({"event": "test-session", "capability": host.capability}), flush=True)
        try:
            host.stop_requested.wait()
        except KeyboardInterrupt:
            host.stop_requested.set()
        finally:
            host.close()
    else:
        window = Window(args.profile or default_directory(), engine, assets, args.no_browser)
        window.root.mainloop()
        if window.close_error is not None:
            raise SystemExit(1)


if __name__ == "__main__":
    run()
