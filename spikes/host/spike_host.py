#!/usr/bin/env python3
"""Spike-Host: beantwortet Native-Messaging-Nachrichten und protokolliert sie.

Schreibt jede Nachricht nach ~/kuchenmail-spike.log. Bei {"type": "hold", "seconds": n}
wartet er n Sekunden, um einen offenen Passwortdialog zu simulieren.
"""

import json
import pathlib
import struct
import sys
import time

LOG = pathlib.Path.home() / "kuchenmail-spike.log"


def read_message():
    raw_len = sys.stdin.buffer.read(4)
    if len(raw_len) < 4:
        return None
    (length,) = struct.unpack("=I", raw_len)
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def send_message(obj):
    data = json.dumps(obj).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("=I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def main():
    while (msg := read_message()) is not None:
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')} {json.dumps(msg, ensure_ascii=False)}\n")
        if msg.get("type") == "hold":
            time.sleep(float(msg.get("seconds", 0)))
        send_message({"ok": True, "echo": msg.get("type")})


if __name__ == "__main__":
    main()
