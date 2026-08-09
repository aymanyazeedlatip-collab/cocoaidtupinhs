from __future__ import annotations

import socket
import threading
import time
import urllib.request
import webbrowser

import uvicorn

from app.core.config import settings
from app.workflows.auto_phase_runner import kick as kick_auto_phase_workflow


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def auto_phase_workflow_loop() -> None:
    # Phase 9/10 only run when the required forecast/evidence records exist.
    # The loop keeps checking in the background so the user never has to paste UUIDs.
    time.sleep(4.0)
    base_url = f"http://127.0.0.1:{settings.port}"
    while True:
        try:
            kick_auto_phase_workflow(base_url)
        except Exception as exc:
            print(f"Automatic Phase 9/10 workflow check skipped: {exc}")
        time.sleep(90.0)


def open_browser_when_ready() -> None:
    url = f"http://{settings.host}:{settings.port}"
    health = f"{url}/api/health"
    for _ in range(40):
        try:
            with urllib.request.urlopen(health, timeout=0.5) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except Exception:
            time.sleep(0.25)
    print(f"The browser did not open automatically. Open {url} manually.")


if __name__ == "__main__":
    if not port_is_available(settings.host, settings.port):
        raise SystemExit(
            f"Port {settings.port} is already in use. Close the other COCO-AID window/server, "
            "or change PORT in .env."
        )
    threading.Thread(target=open_browser_when_ready, daemon=True).start()
    threading.Thread(target=auto_phase_workflow_loop, daemon=True).start()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
