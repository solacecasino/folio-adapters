"""folio.py: write a Folio adapter in a few lines of Python.

Copy this one file next to your main.py. No installing, no dependencies.

    import folio

    @folio.command("count")            # the `id` of a [[commands]] entry in adapter.toml
    def count():
        folio.notify(f"{len(folio.text().split())} words")

    @folio.on("changed")               # an event listed in adapter.toml's `events`
    def changed(event):
        folio.status(f"{event['words']} words")

    folio.run()

The protocol underneath is documented at
https://github.com/solacecasino/folio/blob/main/docs/adapters.md
"""

import json
import sys

__all__ = [
    "FolioError", "command", "on", "run", "request", "send",
    "text", "document", "insert", "replace", "notify", "status", "panel",
    "confirm", "save_dialog", "log", "info",
]

#: What Folio said when it started this adapter: version, protocol, permissions.
info = {}

_commands = {}
_events = {}
_next_id = 0
_backlog = []


class FolioError(Exception):
    """Folio refused a request, e.g. for a missing permission."""


# ---- Registering handlers ---------------------------------------------------


def command(command_id):
    """Runs the decorated function when that command is chosen."""
    def register(fn):
        _commands[command_id] = fn
        return fn
    return register


def on(kind):
    """Runs the decorated function with the event's fields as a dict, for
    "changed", "saved", "opened" or "snapshot", plus "undo" and "redo"."""
    def register(fn):
        _events[kind] = fn
        return fn
    return register


# ---- Talking to Folio -------------------------------------------------------


def send(method, **params):
    """Sends a notification (no reply)."""
    _write({"method": method, "params": params})


def request(method, **params):
    """Sends a request and waits for Folio's answer."""
    global _next_id
    _next_id += 1
    my_id = _next_id
    _write({"id": my_id, "method": method, "params": params})
    for line in sys.stdin:
        message = json.loads(line)
        if message.get("id") == my_id and "method" not in message:
            if "error" in message:
                raise FolioError(message["error"])
            return message.get("result")
        _backlog.append(message)  # handled once this request is answered
    sys.exit(0)  # Folio closed the connection


def text():
    """The whole document as plain text, paragraphs separated by newlines."""
    return request("doc.text")["text"]


def document():
    """The document with formatting, plus its "path" and "theme"."""
    return request("doc.get")


def insert(text):
    """Inserts text at the caret, replacing any selection. One undo step."""
    request("doc.insert", text=text)


def replace(paragraphs):
    """Replaces the whole document, e.g. [{"style": "body", "runs": [{"text": "Hi"}]}]."""
    request("doc.replace", paragraphs=paragraphs)


def notify(text):
    """Shows a short message for a few seconds."""
    request("notify", text=text)


def status(text):
    """Shows text in the status line; None clears it."""
    request("status.set", text=text)


def panel(panel_id, lines):
    """Fills one of your [[panels]]. A line is a string, or
    {"text": ..., "command": ...} to run one of your commands when clicked."""
    request("panel.set", id=panel_id, lines=lines)


def confirm(title, message):
    """Asks a yes/no question in a native dialog. Returns True or False."""
    return request("ui.confirm", title=title, message=message)


def save_dialog(title="Save", file_name="", extension=""):
    """Asks where to save a file. Returns the path, or None if cancelled."""
    return request("ui.save_dialog", title=title, file_name=file_name, extension=extension)


def log(message):
    """Prints a line in Folio's log, for debugging."""
    send("log", message=str(message))


# ---- The loop ----------------------------------------------------------------


def run():
    """Answers Folio until it quits. Call it last."""
    # Folio speaks UTF-8, whatever the system's code page.
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    while True:
        if _backlog:
            message = _backlog.pop(0)
        else:
            line = sys.stdin.readline()
            if not line:
                return
            message = json.loads(line)
        if not _handle(message):
            return


def _handle(message):
    method = message.get("method")
    params = message.get("params") or {}
    try:
        if method == "initialize":
            info.update(params)
        elif method == "command" and params.get("command") in _commands:
            _commands[params["command"]]()
        elif method == "event" and params.get("kind") in _events:
            _events[params["kind"]](params)
        elif method in ("undo", "redo") and method in _events:
            _events[method](params)
        elif method == "shutdown":
            return False
    except FolioError as e:
        log(f"Folio said no: {e}")
    except Exception as e:  # keep running; show what broke
        log(f"{type(e).__name__}: {e}")
        try:
            notify(f"Adapter error: {e}")
        except Exception:
            pass
    return True


def _write(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()
