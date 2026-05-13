"""
Telegram sender — the ONLY module that talks to Telegram Bot API.

Two targets are exposed:
  - send_to_group(text)  →  Finzora signal/report group
  - send_to_dm(text)     →  Zeynel's personal DM (system/maintenance/alerts)

Photo and split-message helpers are provided. All messages are sent as Telegram
HTML (parse_mode=HTML); a markdown-to-HTML helper covers our typical report
style.

Per Finzora convention:
  - Group receives ONLY: trade actions, open/close reports, daily summary
  - DM receives EVERYTHING ELSE: system maintenance, alerts, audit, technical

Message text is the only place we use Turkish (per language convention,
13 May 2026).
"""
from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path
from typing import Optional

import requests

# ---------- Configuration ----------

BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI",
)
GROUP_CHAT_ID = int(os.environ.get("TELEGRAM_GROUP_CHAT_ID", "-1003827034395"))
DM_CHAT_ID    = int(os.environ.get("TELEGRAM_DM_CHAT_ID",    "1403072107"))

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
MAX_MESSAGE_LEN = 4000   # Telegram hard limit is 4096; leave headroom
MAX_CAPTION_LEN = 1024   # Telegram caption limit


# ---------- Public API ----------

def send_to_group(
    text: str,
    parse_mode: str = "HTML",
    disable_preview: bool = True,
) -> bool:
    """Send a text message to the Finzora group chat."""
    return _send_message(text, GROUP_CHAT_ID, parse_mode, disable_preview)


def send_to_dm(
    text: str,
    parse_mode: str = "HTML",
    disable_preview: bool = True,
) -> bool:
    """Send a text message to Zeynel's DM (system/alerts/maintenance)."""
    return _send_message(text, DM_CHAT_ID, parse_mode, disable_preview)


def send_photo(
    image_path: str | Path,
    caption: Optional[str] = None,
    target: str = "group",
    parse_mode: str = "HTML",
) -> bool:
    """
    Send a photo (PNG/JPG) to either 'group' or 'dm'.
    Caption is capped at 1024 chars by Telegram.
    """
    chat_id = _resolve_target(target)
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"[telegram] Image not found: {image_path}", file=sys.stderr)
        return False

    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption[:MAX_CAPTION_LEN]
        data["parse_mode"] = parse_mode

    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                f"{API_BASE}/sendPhoto",
                data=data,
                files={"photo": f},
                timeout=60,
            )
        resp = r.json()
        if resp.get("ok"):
            return True

        # Parse-mode failure → retry as plain text
        desc = resp.get("description", "").lower()
        if "can't parse" in desc and caption:
            data.pop("parse_mode", None)
            with open(image_path, "rb") as f:
                r = requests.post(
                    f"{API_BASE}/sendPhoto",
                    data=data,
                    files={"photo": f},
                    timeout=60,
                )
            return r.json().get("ok", False)

        print(f"[telegram] sendPhoto failed: {resp.get('description')}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[telegram] sendPhoto exception: {e}", file=sys.stderr)
        return False


# ---------- Markdown → Telegram HTML ----------

def md_to_telegram(text: str) -> str:
    """
    Convert a small subset of Markdown to Telegram HTML.

    Supports:
      **bold**, __bold__       → <b>...</b>
      *italic*, _italic_       → <i>...</i>
      `code`                   → <code>...</code>
      ```block```              → <pre>...</pre>
      [text](url)              → <a href="url">text</a>
      # Header                 → <b>Header</b>

    Everything else is HTML-escaped. Order of operations matters to avoid
    eating raw HTML.
    """
    # Step 1: escape any existing HTML
    out = html.escape(text)

    # Step 2: code blocks first (so their contents don't get further parsed)
    out = re.sub(r"```([\s\S]*?)```", r"<pre>\1</pre>", out)

    # Step 3: inline code
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)

    # Step 4: bold (both ** and __)
    out = re.sub(r"\*\*([^\*]+)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"__([^_]+)__", r"<b>\1</b>", out)

    # Step 5: italic (single * or _) — careful not to match list bullets
    out = re.sub(r"(?<!\*)\*(?!\*)([^\*\n]+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", out)
    out = re.sub(r"(?<!_)_(?!_)([^_\n]+?)(?<!_)_(?!_)", r"<i>\1</i>", out)

    # Step 6: links
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)

    # Step 7: headers → bold lines (Telegram has no native headers)
    out = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", out, flags=re.MULTILINE)

    return out


# ---------- Internal helpers ----------

def _resolve_target(target: str) -> int:
    """Map 'group' / 'dm' to the corresponding chat_id."""
    if target == "group":
        return GROUP_CHAT_ID
    if target == "dm":
        return DM_CHAT_ID
    raise ValueError(f"Invalid target: {target!r} (must be 'group' or 'dm')")


def _send_message(
    text: str,
    chat_id: int,
    parse_mode: str,
    disable_preview: bool,
) -> bool:
    """Send a message, splitting if necessary. Returns True iff all chunks ok."""
    chunks = _split_message(text, MAX_MESSAGE_LEN)
    all_ok = True
    for chunk in chunks:
        if not _send_chunk(chunk, chat_id, parse_mode, disable_preview):
            all_ok = False
    return all_ok


def _send_chunk(
    chunk: str,
    chat_id: int,
    parse_mode: str,
    disable_preview: bool,
) -> bool:
    """Send a single message chunk; retry as plain text if parse fails."""
    payload = {
        "chat_id": chat_id,
        "text": chunk,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_preview,
    }
    try:
        r = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=30)
        data = r.json()
        if data.get("ok"):
            return True

        desc = data.get("description", "")
        if "can't parse" in desc.lower():
            # Retry as plain text
            payload.pop("parse_mode", None)
            r = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=30)
            return r.json().get("ok", False)

        print(f"[telegram] sendMessage failed: {desc}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[telegram] sendMessage exception: {e}", file=sys.stderr)
        return False


def _split_message(text: str, max_len: int) -> list[str]:
    """Split a long message at line boundaries, falling back to char splits."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > max_len:
            if current:
                chunks.append(current)
                current = ""
            # A single line longer than max_len → hard split
            while len(line) > max_len:
                chunks.append(line[:max_len])
                line = line[max_len:]
        current += line
    if current:
        chunks.append(current)
    return chunks


# ---------- CLI for manual testing ----------

def _cli():
    import argparse
    p = argparse.ArgumentParser(description="Send a Telegram message (test).")
    p.add_argument("--target", choices=["group", "dm"], default="dm",
                   help="Send to group or DM (default: dm)")
    p.add_argument("--text", help="Message text (markdown allowed)")
    p.add_argument("--photo", help="Path to image file")
    p.add_argument("--caption", help="Caption for photo")
    p.add_argument("--plain", action="store_true",
                   help="Send as plain text (skip markdown conversion)")
    args = p.parse_args()

    if args.photo:
        ok = send_photo(args.photo, args.caption, target=args.target)
        sys.exit(0 if ok else 1)

    if not args.text:
        print("Either --text or --photo is required", file=sys.stderr)
        sys.exit(2)

    text = args.text if args.plain else md_to_telegram(args.text)
    send = send_to_group if args.target == "group" else send_to_dm
    ok = send(text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    _cli()
