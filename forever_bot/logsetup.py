"""
Logging for the bot. One line per event, consistent fields, secrets scrubbed.

  LOG_LEVEL   DEBUG | INFO (default) | WARNING
  LOG_FORMAT  text (default)  ->  2026-10-25 16:41:12 INFO  fetch  event=source_ok source=news:Wowhead items=3 ms=412
              json            ->  {"ts": "...", "level": "INFO", "logger": "fetch", "event": "source_ok", ...}

Search tips (Render > Logs): event=post_sent · event=source_down · level=ERROR · guild=<id>
"""
import json
import logging
import os
import sys
import time
import uuid

_SECRET_ENV = ("DISCORD_TOKEN", "TWITCH_CLIENT_SECRET", "TWITCH_CLIENT_ID", "YOUTUBE_API_KEY")


class RedactFilter(logging.Filter):
    """Masks any configured secret if it ever ends up in a log line (URLs, exceptions, etc.)."""

    def __init__(self):
        super().__init__()
        self.secrets = [v for k in _SECRET_ENV if len(v := os.getenv(k, "").strip()) >= 8]

    def filter(self, record):
        if self.secrets:
            msg = record.getMessage()
            red = msg
            for s in self.secrets:
                red = red.replace(s, "***")
            if red != msg:
                record.msg, record.args = red, ()
        return True


def _fmt_val(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.0f}" if abs(v) >= 10 else f"{v:.2f}"
    s = str(v)
    if any(c in s for c in ' "='):
        s = '"' + s.replace('"', "'") + '"'
    return s


class TextFormatter(logging.Formatter):
    def format(self, record):
        base = f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} {record.levelname:<5} {record.name.replace('forever.', ''):<6} "
        fields = getattr(record, "fields", None)
        if fields:
            body = " ".join(f"{k}={_fmt_val(v)}" for k, v in fields.items())
        else:
            body = record.getMessage()
        if record.exc_info:
            body += "\n" + self.formatException(record.exc_info)
        return base + body


class JsonFormatter(logging.Formatter):
    def format(self, record):
        out = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"), "level": record.levelname,
               "logger": record.name}
        fields = getattr(record, "fields", None)
        if fields:
            out.update({k: v for k, v in fields.items()})
        else:
            out["msg"] = record.getMessage()
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


def setup_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if os.getenv("LOG_FORMAT", "text").lower() == "json" else TextFormatter())
    handler.addFilter(RedactFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # discord.py is chatty at DEBUG; keep its noise down unless asked
    logging.getLogger("discord").setLevel(os.getenv("DISCORD_LOG_LEVEL", "INFO").upper())
    logging.getLogger("discord.client").addFilter(_DropVoiceWarnings())


class _DropVoiceWarnings(logging.Filter):
    def filter(self, record):
        return "voice will NOT be supported" not in record.getMessage()


def ev(logger: logging.Logger, event: str, level: int = logging.INFO, exc_info=None, **fields):
    """Log one structured event: ev(log, "post_sent", guild=1, key="launch:2026-10-25:0")."""
    if logger.isEnabledFor(level):
        logger.log(level, event, extra={"fields": {"event": event, **fields}}, exc_info=exc_info)


def new_run_id() -> str:
    return uuid.uuid4().hex[:6]


class Timer:
    def __enter__(self):
        self.t = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.ms = (time.perf_counter() - self.t) * 1000

    @property
    def elapsed_ms(self):
        return (time.perf_counter() - self.t) * 1000
