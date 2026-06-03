"""PySide6 desktop wrapper around the local Flask app."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import webbrowser
import os
from pathlib import Path


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server(port: int) -> subprocess.Popen[str]:
    env_python = Path(sys.executable)
    root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    src_path = str(root / "src")
    existing_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not existing_path else f"{src_path}{os.pathsep}{existing_path}"
    command = [str(env_python), "-m", "battery_pack_designer.web.app", "--port", str(port)]
    return subprocess.Popen(command, cwd=root, env=env)


def main() -> None:
    port = _find_free_port()
    server = _start_server(port)
    url = f"http://127.0.0.1:{port}"
    time.sleep(1.2)

    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtWidgets import QApplication, QMainWindow

        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            QWebEngineView = None

        app = QApplication(sys.argv)
        if QWebEngineView is None:
            webbrowser.open(url)
            print(f"Desktop shell fallback opened in browser: {url}")
            sys.exit(app.exec())

        view = QWebEngineView()
        view.setUrl(QUrl(url))
        window = QMainWindow()
        window.setWindowTitle("Battery Pack Designer")
        window.resize(1440, 960)
        window.setCentralWidget(view)
        window.show()
        exit_code = app.exec()
        server.terminate()
        sys.exit(exit_code)
    finally:
        if server.poll() is None:
            server.terminate()


if __name__ == "__main__":
    main()
