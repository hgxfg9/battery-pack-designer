"""PySide6 desktop wrapper around the local Flask app."""

from __future__ import annotations

import socket
import sys
import time
import webbrowser
from threading import Thread

from werkzeug.serving import make_server

from ..web.app import create_app


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _LocalServer(Thread):
    def __init__(self, host: str, port: int) -> None:
        super().__init__(daemon=True)
        self._server = make_server(host, port, create_app(), threaded=True)

    def run(self) -> None:
        self._server.serve_forever()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def main() -> None:
    port = _find_free_port()
    server = _LocalServer("127.0.0.1", port)
    server.start()
    url = f"http://127.0.0.1:{port}"
    time.sleep(1.0)

    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            QWebEngineView = None

        app = QApplication(sys.argv)
        if QWebEngineView is None:
            webbrowser.open(url)
            fallback_window = QMainWindow()
            fallback_window.setWindowTitle("Battery Pack Designer")
            container = QWidget()
            layout = QVBoxLayout(container)
            message = QLabel(
                f"Qt WebEngine is unavailable.\nThe planner was opened in your default browser:\n{url}"
            )
            message.setWordWrap(True)
            layout.addWidget(message)
            fallback_window.setCentralWidget(container)
            fallback_window.resize(720, 180)
            fallback_window.show()
            sys.exit(app.exec())

        view = QWebEngineView()
        view.setUrl(QUrl(url))
        window = QMainWindow()
        window.setWindowTitle("Battery Pack Designer")
        window.resize(1440, 960)
        window.setCentralWidget(view)
        window.show()
        sys.exit(app.exec())
    finally:
        server.stop()


if __name__ == "__main__":
    main()
