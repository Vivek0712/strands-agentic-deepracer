---
inclusion: fileMatch
fileMatchPattern: "use_cases/pipeline_crawler.py"
---

# Use Cases — TCP JSON Robots Reference (pipeline_crawler, camera_dolly)

## Shared Pattern
Both use cases communicate via a raw TCP socket sending newline-delimited JSON commands.

```python
_SOCK = None

def _get_sock():
    global _SOCK
    if _SOCK is None:
        _SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _SOCK.settimeout(5)
        _SOCK.connect((HOST, PORT))
    return _SOCK

def _send_cmd(cmd: dict) -> str:
    sock = _get_sock()
    sock.sendall((json.dumps(cmd) + "\n").encode())
    try:
        return sock.recv(256).decode().strip()
    except socket.timeout:
        return "ok"  # timeout treated as success

def reset_client() -> None:
    global _SOCK
    if _SOCK:
        try: _SOCK.close()
        except Exception: pass
    _SOCK = None
```

## pipeline_crawler.py
- Movement is 1D only — forward/backward inside the pipe
- `turn_left/right` → camera pan, NOT vehicle rotation (`{"cmd": "pan", "direction": "left/right"}`)
- `stop()` → `{"cmd": "stop"}`
- `activate_camera()` → `{"cmd": "camera_on"}` — returns True if response contains "ok"
- Physics: `PHYSICS_MIN_TURN_RADIUS_M = float("inf")` — robot cannot turn

```
CRAWLER_HOST    192.168.1.200
CRAWLER_PORT    8888
CRAWLER_SPEED   0.3   (0.0–1.0)
CRAWLER_PAN_SPD 30.0  (deg/s)
```

Rotation (camera pan): `deg = PAN_SPEED * seconds`

## camera_dolly.py
- `move_forward/backward` → dolly slides along track
- `turn_left/right` → pan head rotation (the camera itself pans)
- `stop()` → `{"cmd": "stop"}`
- Physics: `PHYSICS_MIN_TURN_RADIUS_M = float("inf")` — dolly moves on a fixed track

```
DOLLY_HOST      192.168.1.201
DOLLY_PORT      8889
DOLLY_SPEED     0.3
DOLLY_PAN_SPD   45.0  (deg/s)
```

## is_error() for TCP use cases
```python
def is_error(message: str) -> bool:
    m = str(message).lower()
    return m.startswith("error") or "exception" in m or "cannot connect" in m
```

## Safety
- `socket.timeout` on `recv()` is treated as success ("ok") — the command was sent
- `stop()` MUST call `_send_cmd({"cmd": "stop"})` — socket errors MUST be caught and logged, not raised
- `reset_client()` MUST close the socket before clearing `_SOCK` — prevents fd leak
- `_get_sock()` sets `settimeout(5)` — never use blocking socket without timeout
