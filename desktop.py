from __future__ import annotations

import socket
import threading
import time

import webview

from server import APP_HOST, APP_PORT, run_server


def wait_for_server(timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((APP_HOST, APP_PORT), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main() -> None:
    server_thread = threading.Thread(target=run_server, daemon=True, name="LiteTube-Flask")
    server_thread.start()

    if not wait_for_server():
        raise RuntimeError(
            f"LiteTube server did not start on http://{APP_HOST}:{APP_PORT}."
        )

    window = webview.create_window(
        "LiteTube",
        f"http://{APP_HOST}:{APP_PORT}",
        width=1280,
        height=820,
        min_size=(980, 650),
        resizable=True,
        text_select=True,
        confirm_close=True,
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()
