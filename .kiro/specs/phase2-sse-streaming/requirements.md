# Phase 2 SSE Streaming — Requirements

## Overview
Server-Sent Events (SSE) provide real-time step-by-step execution feedback from the
Flask server to the browser. The SSE stream replaces the polling approach and enables
live progress display without WebSockets.

## Functional Requirements

### FR-1: SSE Wire Format
- Each event: `event: <type>\ndata: <json_string>\n\n`
- Helper `_sse(event, data)` formats the string
- Helper `_push(event, data)` puts the formatted string into `_sse_queue`

### FR-2: Event Types and Payloads
| Event | Payload | When |
|---|---|---|
| `start` | `{"total": int, "pattern": str}` | Before first step |
| `step` | `{"index": int, "action": str, "seconds": float\|null, "ok": bool, "message": str, "emergency": bool}` | After each step |
| `done` | `{"ok_count": int, "fail_count": int}` | After all steps complete |
| `stopped` | `{"message": str}` | On user abort or error abort |

### FR-3: Queue Management
- `_sse_queue: queue.Queue[str]` — module-level singleton
- `/execute` MUST drain the queue before starting a new execution
- Drain loop: `while not _sse_queue.empty(): _sse_queue.get_nowait()` with `queue.Empty` catch
- Queue is written by the execution thread, read by the `/stream` generator

### FR-4: Stream Lifecycle
1. Browser opens `GET /stream` connection
2. Server yields events as they arrive in `_sse_queue`
3. On 15 s timeout: yield `: heartbeat\n\n` (SSE comment, keeps connection alive)
4. On `done` or `stopped` event: yield the event, then break the generator

### FR-5: Heartbeat
- `_sse_queue.get(timeout=15)` — 15 second timeout
- On `queue.Empty`: yield `: heartbeat\n\n`
- Heartbeat is an SSE comment (starts with `:`) — browsers ignore it but connection stays open

### FR-6: Thread Safety
- `queue.Queue` is thread-safe — no additional locking needed
- Execution thread writes via `_push()`
- `/stream` generator reads via `_sse_queue.get(timeout=15)`
- `/execute` drains via `_sse_queue.get_nowait()`

### FR-7: Stream Termination
- Generator breaks after yielding `done` or `stopped` event
- Check: `if "event: done" in msg or "event: stopped" in msg: break`
- Browser EventSource will reconnect unless explicitly closed — frontend must close on done/stopped

## Non-Functional Requirements
- NFR-1: SSE requires `threaded=True` in Flask — single-threaded mode blocks the stream
- NFR-2: `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers prevent proxy buffering
- NFR-3: Queue drain prevents stale events from a previous execution appearing in a new stream
- NFR-4: Heartbeat prevents proxy/load-balancer timeouts on idle connections
