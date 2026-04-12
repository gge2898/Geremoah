"""Bluetooth RFCOMM server.

Listens for incoming connections from the Android app, receives tasks as
JSON, runs the Gemma 3 agent, and streams status updates back to the phone.

Each connection is handled in its own daemon thread so multiple phones
could theoretically connect (though typically only one at a time is useful).
"""

import json
import os
import threading

import bluetooth

from agent.agent import AgentLoop
from agent.display import Display

SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"
MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")

_display = Display()


def _handle_client(client_sock: bluetooth.BluetoothSocket, addr: str) -> None:
    _display.connected(addr)

    # makefile gives us a line-oriented text interface over the raw socket.
    try:
        rfile = client_sock.makefile("r", encoding="utf-8")
        wfile = client_sock.makefile("w", encoding="utf-8")
    except Exception as exc:
        _display.error(f"Could not wrap socket in file: {exc}")
        client_sock.close()
        return

    def send_status(msg: dict) -> None:
        try:
            wfile.write(json.dumps(msg) + "\n")
            wfile.flush()
        except Exception:
            pass  # connection dropped; let the for-loop handle it

    agent = AgentLoop(model=MODEL, status_callback=send_status)

    try:
        for raw_line in rfile:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                send_status({"type": "error", "message": "Invalid JSON received."})
                continue

            if data.get("type") == "task":
                task_text = data.get("text", "").strip()
                if task_text:
                    agent.run(task_text)
                else:
                    send_status({"type": "error", "message": "Empty task received."})
            else:
                send_status({"type": "error", "message": f"Unknown message type: {data.get('type')}"})

    except Exception as exc:
        _display.error(f"Client error: {exc}")
    finally:
        try:
            rfile.close()
            wfile.close()
            client_sock.close()
        except Exception:
            pass
        _display.disconnected()


def run_server() -> None:
    """Start the Bluetooth RFCOMM server and accept connections in a loop."""
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", bluetooth.PORT_ANY))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    bluetooth.advertise_service(
        server_sock,
        "AI Control Agent",
        service_id=SPP_UUID,
        service_classes=[SPP_UUID, bluetooth.SERIAL_PORT_CLASS],
        profiles=[bluetooth.SERIAL_PORT_PROFILE],
    )

    print(f"Bluetooth server listening on RFCOMM port {port}")
    print("Make sure the computer is paired and discoverable from your Android device.")
    print("Waiting for connection...\n")

    try:
        while True:
            client_sock, addr = server_sock.accept()
            t = threading.Thread(
                target=_handle_client,
                args=(client_sock, str(addr)),
                daemon=True,
            )
            t.start()
    except KeyboardInterrupt:
        print("\nShutting down Bluetooth server.")
    finally:
        server_sock.close()
