"""Telegram bot — enqueue jobs via chat, get status updates.

Customer sends `/yap NASA Artemis` to the bot; it enqueues a job against
their account. They get status updates as replies.

Runs as a long-poll loop (no webhook required). Start it from the worker
or a separate service.

Usage from CLI:
    python -m pipeline telegram-bot --token <BOT_TOKEN>

Commands the bot understands:
    /start           — welcome + help
    /yap <topic>     — create a new video from topic
    /durum [id]      — show queue status (or a specific job)
    /iptal <id>      — cancel a job
    /kuyruk          — list recent jobs
    /stat            — today + MTD cost summary
"""

from __future__ import annotations

import json
import time
from typing import Any

from .log import log


TELEGRAM_API = "https://api.telegram.org"


def _send(bot_token: str, chat_id: str | int, text: str,
           parse_mode: str | None = "Markdown") -> bool:
    try:
        import requests
        payload = {"chat_id": chat_id, "text": text[:4000]}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        r = requests.post(
            f"{TELEGRAM_API}/bot{bot_token}/sendMessage",
            json=payload, timeout=10,
        )
        return r.ok
    except Exception as e:
        log(f"[tg] send failed: {e}")
        return False


def _handle_command(bot_token: str, chat_id: int, user_id: int,
                     text: str, allowed_users: list[int] | None) -> None:
    # Authorization — only allow configured user IDs
    if allowed_users and user_id not in allowed_users:
        _send(bot_token, chat_id,
              "❌ Bu bot'u kullanma yetkin yok. Yöneticiyle konuş.")
        return

    text = text.strip()
    if not text.startswith("/"):
        return

    parts = text.split(maxsplit=1)
    cmd = parts[0].lower().lstrip("/")
    arg = parts[1] if len(parts) > 1 else ""

    try:
        if cmd in ("start", "help", "yardim"):
            _send(bot_token, chat_id,
                  "🎬 *RE-Tube Bot*\n\n"
                  "*/yap* `<konu>` — yeni video üret\n"
                  "*/durum* `[id]` — kuyruk durumu\n"
                  "*/iptal* `<id>` — işi iptal et\n"
                  "*/kuyruk* — son 10 iş\n"
                  "*/stat* — günlük + aylık harcama\n")

        elif cmd in ("yap", "new", "produce"):
            if not arg:
                _send(bot_token, chat_id, "Konu gerekli: `/yap NASA Artemis`")
                return
            from . import queue as qmod
            job = qmod.enqueue(topic=arg, lang="tr", mode="full",
                                extra={"via": "telegram",
                                       "chat_id": chat_id})
            _send(bot_token, chat_id,
                  f"✅ Kuyruğa eklendi\n`{job['id']}`\n_{arg[:60]}_\n\n"
                  f"Durumu öğrenmek için `/durum {job['id']}`")

        elif cmd == "durum" or cmd == "status":
            from . import queue as qmod
            if arg:
                job = qmod.load_job(arg)
                if not job:
                    _send(bot_token, chat_id, f"❓ `{arg}` bulunamadı")
                    return
                _send(bot_token, chat_id,
                      f"*{job['topic'][:60]}*\n"
                      f"`{job['id']}`\n"
                      f"Durum: *{job['status']}*\n"
                      f"Aşama: {job.get('stage', '-')}\n"
                      f"İlerleme: {job.get('progress_pct', 0)}%\n"
                      f"Hata: {job.get('error') or '-'}")
            else:
                counts = qmod.counts()
                _send(bot_token, chat_id,
                      f"📊 *Kuyruk*\n"
                      f"Bekleyen: {counts['pending']}\n"
                      f"Üretiliyor: {counts['producing']}\n"
                      f"Yükleniyor: {counts['uploading']}\n"
                      f"✅ Tamamlanan: {counts['done']}\n"
                      f"❌ Hata: {counts['failed']}")

        elif cmd == "iptal" or cmd == "cancel":
            if not arg:
                _send(bot_token, chat_id, "İş ID'si gerekli: `/iptal q17...`")
                return
            from . import queue as qmod
            qmod.cancel_job(arg)
            _send(bot_token, chat_id, f"🚫 İptal sinyali: `{arg}`")

        elif cmd == "kuyruk" or cmd == "queue":
            from . import queue as qmod
            jobs = qmod.list_jobs()[-10:]
            if not jobs:
                _send(bot_token, chat_id, "Kuyruk boş.")
                return
            lines = ["📋 *Son 10 iş*\n"]
            for j in jobs:
                icon = {"pending": "⏳", "producing": "⚙️",
                        "uploading": "📤", "done": "✅",
                        "failed": "❌", "cancelled": "🚫"}.get(j["status"], "?")
                lines.append(f"{icon} `{j['id'][-8:]}` {j['topic'][:40]}")
            _send(bot_token, chat_id, "\n".join(lines))

        elif cmd == "stat":
            from . import cost
            _send(bot_token, chat_id,
                  f"💰 *Harcama*\n"
                  f"Bugün: ${cost.today_usd():.2f}\n"
                  f"Bu Ay: ${cost.month_to_date_usd():.2f}\n"
                  f"Son 30g: ${cost.summary(days=30)['total_usd']:.2f}")

        else:
            _send(bot_token, chat_id, f"❓ Bilinmeyen komut: `/{cmd}`\n`/yardim` ile komut listesi.")

    except Exception as e:
        _send(bot_token, chat_id, f"⚠️ Hata: {e}")


def poll_loop(
    bot_token: str,
    *,
    allowed_user_ids: list[int] | None = None,
    poll_interval: int = 2,
    stop_event=None,
) -> None:
    """Long-poll Telegram for updates. Runs until stop_event.set() or Ctrl-C."""
    import requests
    offset = 0
    log(f"[tg] bot started (allowed_users={allowed_user_ids})")
    while True:
        if stop_event and stop_event.is_set():
            break
        try:
            r = requests.get(
                f"{TELEGRAM_API}/bot{bot_token}/getUpdates",
                params={"offset": offset, "timeout": 25},
                timeout=30,
            )
            if not r.ok:
                time.sleep(5)
                continue
            data = r.json()
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue
                chat_id = msg["chat"]["id"]
                user_id = msg.get("from", {}).get("id", 0)
                text = msg.get("text", "") or ""
                if text.startswith("/"):
                    _handle_command(bot_token, chat_id, user_id, text,
                                     allowed_user_ids)
        except requests.RequestException:
            time.sleep(5)
        except Exception as e:
            log(f"[tg] unexpected: {e}")
            time.sleep(5)


def start_background(bot_token: str, allowed_user_ids: list[int] | None = None):
    """Start the bot in a background thread. Returns (thread, stop_event)."""
    import threading
    stop = threading.Event()
    th = threading.Thread(
        target=poll_loop,
        args=(bot_token,),
        kwargs={"allowed_user_ids": allowed_user_ids, "stop_event": stop},
        daemon=True, name="retube-tg-bot",
    )
    th.start()
    return th, stop
