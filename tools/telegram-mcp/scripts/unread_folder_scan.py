#!/usr/bin/env python3
"""
Повний скан непрочитаного по папках Telegram MCP (див. skill telegram-mcp).
Вихідні (fromMe: true) не потрапляють у dump і MD.
Папки-виключення і дайджест-боти — workspace/telegram-access.yaml.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = ROOT / "output" / "telegram"
DEFAULT_MCP = "http://localhost:3700/mcp"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
def _load_telegram_access() -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """exclude_folder_titles, digest_chat_names, digest_chat_ids from workspace YAML."""
    path = ROOT / "workspace" / "telegram-access.yaml"
    buckets = {
        "exclude_folder_titles": set(),
        "digest_chat_names": set(),
        "digest_chat_ids": set(),
    }
    section = None
    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            if not line.startswith((" ", "\t")) and line.strip().endswith(":"):
                section = line.strip()[:-1]
                continue
            item = line.strip()
            if item.startswith("- ") and section in buckets:
                buckets[section].add(item[2:].strip().strip("'\""))
    return (
        frozenset(buckets["exclude_folder_titles"]),
        frozenset(buckets["digest_chat_names"]),
        frozenset(buckets["digest_chat_ids"]),
    )


EXCLUDED_TITLES, DIGEST_SUMMARY_NAMES, DIGEST_SUMMARY_CHAT_IDS = _load_telegram_access()
PAUSE_S = 0.15
MAX_RETRIES = 4


def call_tool(mcp_url: str, name: str, arguments: dict, req_id: int) -> dict:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    ).encode()
    req = urllib.request.Request(mcp_url, data=body, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def parse_tool_result(resp: dict):
    if resp.get("error"):
        return None, resp["error"]
    result = resp.get("result") or {}
    if result.get("isError"):
        parts = result.get("content") or []
        text = parts[0].get("text", "") if parts else "isError"
        return None, text
    content = result.get("content") or []
    if not content:
        return None, "empty content"
    text = content[0].get("text", "")
    low = text.lower()
    if "wait of" in low and "second" in low and "required" in low:
        return None, text
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        return None, text


def floodwait_seconds(msg: str) -> int | None:
    m = re.search(r"wait\s+of\s+(\d+)\s+second", msg, re.I)
    return int(m.group(1)) if m else None


def is_digest_summary_chat(chat_id: str, name: str) -> bool:
    return chat_id in DIGEST_SUMMARY_CHAT_IDS or (name or "").strip() in DIGEST_SUMMARY_NAMES


def split_messages(
    messages: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """incoming (fromMe is False), outgoing (True), ambiguous (key missing)."""
    incoming: list[dict] = []
    outgoing: list[dict] = []
    ambiguous: list[dict] = []
    for m in messages:
        if "fromMe" not in m:
            ambiguous.append(m)
            continue
        if m["fromMe"]:
            outgoing.append(m)
        else:
            incoming.append(m)
    return incoming, outgoing, ambiguous


def build_analysis_lines(
    *,
    prefix: str,
    meta: dict,
    unique_chat_count: int,
    digest_blocks: list[dict],
    other_incoming: list[dict],
    ambiguous_only: list[dict],
    errors: list[dict],
    any_from_me_missing_global: bool,
) -> list[str]:
    lines = [
        f"# Telegram непрочитане (лише вхідні) — {prefix}",
        "",
        f"- Час старту (UTC): {meta['run_started_iso']}",
        f"- Унікальних чатів у скані: {unique_chat_count}",
        f"- Чатів з **вхідними** непрочитаними: **{meta['chats_with_incoming_unread']}**",
    ]
    if meta["chats_ambiguous_missing_fromMe_only"]:
        lines.append(
            f"- Чатів лише з повідомленнями **без поля fromMe** (потрібен оновлений MCP): **{meta['chats_ambiguous_missing_fromMe_only']}**"
        )
    if any_from_me_missing_global:
        lines.append(
            "- Увага: частина повідомлень без поля `fromMe` не класифікована як вхідні — оновіть образ telegram-mcp і перескануйте."
        )

    if digest_blocks:
        lines.extend(
            [
                "",
                "## Дайджест — саммарі одним повідомленням",
                "",
                "_У відповіді користувачу в чаті не переліковувати кожну новину: прочитати всі вхідні з цього бота з дампу й видати **одне цікаве стисле повідомлення** (теми, інсайти, що відкрити детальніше)._",
                "",
            ]
        )
        for block in sorted(digest_blocks, key=lambda x: x["name"].lower()):
            folders_s = ", ".join(block["folders"][:3])
            if len(block["folders"]) > 3:
                folders_s += "…"
            lines.append(f"### {block['name']} (`{block['chatId']}`)")
            lines.append(f"- Папки: {folders_s}")
            lines.append(
                f"- Вхідних у вибірці: **{block['incoming_unread_count']}** — звести в **1 саммарі**; повний текст у `*_telegram_dump.json`."
            )
            lines.append("")

    if other_incoming:
        lines.extend(["", "## Інші вхідні повідомлення", ""])

        for block in sorted(
            other_incoming,
            key=lambda x: (-x["incoming_unread_count"], x["name"].lower()),
        ):
            folders_s = ", ".join(block["folders"][:3])
            if len(block["folders"]) > 3:
                folders_s += "…"
            lines.append(f"### {block['name']} (`{block['chatId']}`)")
            lines.append(f"- Папки: {folders_s}")
            lines.append(
                f"- Вхідних непрочитаних у вибірці: {block['incoming_unread_count']}"
            )
            inc_msgs = [m for m in block["messages"] if m.get("fromMe") is False]
            for m in inc_msgs[:8]:
                sender = m.get("sender") or "?"
                text = (m.get("text") or "").replace("\n", " ").strip()
                if len(text) > 180:
                    text = text[:177] + "…"
                lines.append(f"  - {sender}: {text or '(без тексту / медіа)'}")
            if len(inc_msgs) > 8:
                lines.append(f"  - … ще {len(inc_msgs) - 8} вхідних у дампі JSON")
            lines.append("")

    if not digest_blocks and not other_incoming and not ambiguous_only:
        lines.extend(["", "_Немає вхідних непрочитаних у покритих чатах._", ""])

    if ambiguous_only:
        lines.extend(
            [
                "## Повідомлення без поля fromMe",
                "",
                "_Не зараховані як вхідні; потрібен оновлений telegram-mcp у відповіді `get_messages`._",
                "",
            ]
        )
        for block in sorted(ambiguous_only, key=lambda x: x["name"].lower()):
            lines.append(
                f"- **{block['name']}** `{block['chatId']}` — без `fromMe`: {block['ambiguous_missing_fromMe_count']}"
            )
        lines.append("")

    if errors:
        lines.extend(["", "## Помилки скану", ""])
        for e in errors:
            lines.append(f"- `{e['chatId']}` {e['name']}: {str(e['error'])[:200]}")

    return lines


def enrich_block_for_report(block: dict) -> dict | None:
    """Відкидає чати лише з вихідніми в непрочитаному; нормалізує лічильники."""
    msgs = block.get("messages", [])
    inc, outg, amb = split_messages(msgs)
    if len(inc) == 0 and len(amb) == 0:
        return None
    cid = str(block["chatId"])
    name = block.get("name") or cid
    digest = block.get("digest_summarize_as_one_message")
    if digest is None:
        digest = is_digest_summary_chat(cid, name)
    return {
        **block,
        "chatId": cid,
        "incoming_unread_count": len(inc),
        "outgoing_unread_in_batch": len(outg),
        "ambiguous_missing_fromMe_count": len(amb),
        "digest_summarize_as_one_message": digest,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mcp-url", default=DEFAULT_MCP)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--prefix",
        help="YYYY-MM-DD_HH-mm-ss (за замовчуванням — зараз локально)",
        default=None,
    )
    ap.add_argument(
        "--from-dump",
        type=Path,
        help="Перегенерувати лише MD з існуючого *_telegram_dump.json (без MCP)",
        default=None,
    )
    ap.add_argument(
        "--no-personal-dms",
        action="store_true",
        help="Не додавати особисті 1:1 з list_dialogs (за замовчуванням — додавати)",
    )
    args = ap.parse_args()

    if args.from_dump is not None:
        dump_path = args.from_dump.expanduser().resolve()
        if not dump_path.is_file():
            print(json.dumps({"error": "file not found", "path": str(dump_path)}), file=sys.stderr)
            return 1
        stem = dump_path.name
        if not stem.endswith("_telegram_dump.json"):
            print(
                json.dumps({"error": "expected *_telegram_dump.json", "path": str(dump_path)}),
                file=sys.stderr,
            )
            return 1
        prefix = stem[: -len("_telegram_dump.json")]
        with open(dump_path, encoding="utf-8") as f:
            dump = json.loads(f.read())

        meta = dict(dump["meta"])
        enriched = [enrich_block_for_report(b) for b in dump.get("chats_with_unread", [])]
        raw_blocks = [b for b in enriched if b is not None]

        blocks_incoming = [b for b in raw_blocks if b["incoming_unread_count"] > 0]
        ambiguous_only = [
            b
            for b in raw_blocks
            if b["incoming_unread_count"] == 0 and b.get("ambiguous_missing_fromMe_count", 0) > 0
        ]
        any_miss = bool(meta.get("fromMe_missing_in_some_messages"))
        if not any_miss:
            any_miss = any(b.get("ambiguous_missing_fromMe_count", 0) > 0 for b in raw_blocks)

        meta["chats_with_incoming_unread"] = len(blocks_incoming)
        meta["chats_ambiguous_missing_fromMe_only"] = len(ambiguous_only)
        meta.pop("chats_with_any_unread", None)
        meta.pop("chats_outgoing_only_unread", None)
        meta["fromMe_missing_in_some_messages"] = any_miss

        digest_blocks = [b for b in blocks_incoming if b.get("digest_summarize_as_one_message")]
        other_incoming = [b for b in blocks_incoming if not b.get("digest_summarize_as_one_message")]

        chat_idx = dump.get("chat_index") or []
        lines = build_analysis_lines(
            prefix=prefix,
            meta=meta,
            unique_chat_count=len(chat_idx) or meta.get("unique_chat_count", 0),
            digest_blocks=digest_blocks,
            other_incoming=other_incoming,
            ambiguous_only=ambiguous_only,
            errors=dump.get("scan_errors", []),
            any_from_me_missing_global=any_miss,
        )
        md_path = dump_path.with_name(f"{prefix}_telegram_analysis.md")
        md_path.write_text("\n".join(lines), encoding="utf-8")
        print(md_path)
        return 0

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    mcp_url: str = args.mcp_url

    meta: dict = {
        "run_started_iso": datetime.now(timezone.utc).isoformat(),
        "timezone_note": "UTC in meta; user TZ Europe/Kyiv typical",
        "excluded_folder_titles": sorted(EXCLUDED_TITLES),
        "mcp_url": mcp_url,
        "fromMe_note": "У дампі лише чати з вхідними або ambiguous; вихідні лише (fromMe: true) відкидаються повністю.",
    }
    rid = 0

    rid += 1
    raw = call_tool(mcp_url, "list_folders", {}, rid)
    folders_data, err = parse_tool_result(raw)
    if err:
        print(json.dumps({"error": "list_folders", "detail": err}), file=sys.stderr)
        return 1

    folders = [f for f in folders_data["folders"] if f["title"] not in EXCLUDED_TITLES]
    meta["folders_scanned"] = [{"id": f["id"], "title": f["title"]} for f in folders]

    chat_to_name: dict[str, str] = {}
    chat_to_folders: dict[str, list[str]] = {}

    for folder in folders:
        fid = folder["id"]
        title = folder["title"]
        rid += 1
        raw = call_tool(mcp_url, "get_folder_chats", {"folderId": fid, "limit": 500}, rid)
        data, err = parse_tool_result(raw)
        if err:
            print(json.dumps({"error": "get_folder_chats", "folder": title, "detail": err}), file=sys.stderr)
            return 1
        for c in data.get("chats", []):
            cid = str(c["id"])
            name = c.get("name") or cid
            if cid not in chat_to_name:
                chat_to_name[cid] = name
            chat_to_folders.setdefault(cid, []).append(title)

    personal_added = 0
    if not args.no_personal_dms:
        rid += 1
        raw = call_tool(
            mcp_url,
            "list_dialogs",
            {"type": "user", "limit": 800, "unreadOnly": False},
            rid,
        )
        dms_data, err = parse_tool_result(raw)
        if err:
            wait = floodwait_seconds(err)
            if wait:
                time.sleep(wait + 3)
                rid += 1
                raw = call_tool(
                    mcp_url,
                    "list_dialogs",
                    {"type": "user", "limit": 800, "unreadOnly": False},
                    rid,
                )
                dms_data, err = parse_tool_result(raw)
            if err:
                print(json.dumps({"error": "list_dialogs", "detail": err}), file=sys.stderr)
                return 1
        truncated = bool((dms_data or {}).get("truncated"))
        meta["personal_dms"] = {
            "included": True,
            "listed": (dms_data or {}).get("count", 0),
            "truncated": truncated,
        }
        for d in (dms_data or {}).get("dialogs") or []:
            cid = str(d["id"])
            name = d.get("name") or cid
            if cid not in chat_to_name:
                chat_to_name[cid] = name
                personal_added += 1
            folders = chat_to_folders.setdefault(cid, [])
            if "personal_dm" not in folders:
                folders.append("personal_dm")
        meta["personal_dms"]["added_not_in_folders"] = personal_added
    else:
        meta["personal_dms"] = {"included": False}

    chat_ids = sorted(chat_to_name.keys(), key=lambda x: (len(x), x))
    meta["unique_chat_count"] = len(chat_ids)

    raw_blocks: list[dict] = []
    errors: list[dict] = []
    any_from_me_missing_global = False

    for i, chat_id in enumerate(chat_ids):
        name = chat_to_name[chat_id]
        attempt = 0
        while attempt < MAX_RETRIES:
            rid += 1
            raw = call_tool(
                mcp_url,
                "get_messages",
                {
                    "chatId": chat_id,
                    "limit": 15,
                    "onlyUnread": True,
                    "markAsRead": False,
                },
                rid,
            )
            data, err = parse_tool_result(raw)
            if data is not None:
                cnt = data.get("count", 0)
                msgs = data.get("messages", [])
                if cnt:
                    inc, outg, amb = split_messages(msgs)
                    # Лише вихідні в непрочитаному — повністю ігноруємо (ні dump, ні MD).
                    if len(inc) == 0 and len(amb) == 0:
                        break
                    raw_blocks.append(
                        {
                            "chatId": chat_id,
                            "name": name,
                            "folders": chat_to_folders.get(chat_id, []),
                            "api_unread_returned": cnt,
                            "incoming_unread_count": len(inc),
                            "outgoing_unread_in_batch": len(outg),
                            "ambiguous_missing_fromMe_count": len(amb),
                            "digest_summarize_as_one_message": is_digest_summary_chat(
                                chat_id, name
                            ),
                            "messages": msgs,
                        }
                    )
                    if amb:
                        any_from_me_missing_global = True
                break
            err_s = err if isinstance(err, str) else json.dumps(err)
            fw = floodwait_seconds(err_s)
            if fw is not None:
                attempt += 1
                time.sleep(fw + 3)
                continue
            errors.append({"chatId": chat_id, "name": name, "error": err_s})
            break
        time.sleep(PAUSE_S)
        if (i + 1) % 40 == 0:
            print(f"... {i + 1}/{len(chat_ids)}", file=sys.stderr)

    blocks_incoming = [b for b in raw_blocks if b["incoming_unread_count"] > 0]
    ambiguous_only = [
        b
        for b in raw_blocks
        if b["incoming_unread_count"] == 0 and b.get("ambiguous_missing_fromMe_count", 0) > 0
    ]

    meta["chats_with_incoming_unread"] = len(blocks_incoming)
    meta["chats_ambiguous_missing_fromMe_only"] = len(ambiguous_only)
    meta["fromMe_missing_in_some_messages"] = any_from_me_missing_global

    digest_blocks = [b for b in blocks_incoming if b.get("digest_summarize_as_one_message")]
    other_incoming = [b for b in blocks_incoming if not b.get("digest_summarize_as_one_message")]

    dump = {
        "meta": meta,
        "chats_with_unread": raw_blocks,
        "scan_errors": errors,
        "chat_index": [
            {"chatId": k, "name": chat_to_name[k], "folders": chat_to_folders[k]} for k in chat_ids
        ],
    }

    dump_path = out_dir / f"{prefix}_telegram_dump.json"
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(dump, f, ensure_ascii=False, indent=2)

    lines = build_analysis_lines(
        prefix=prefix,
        meta=meta,
        unique_chat_count=len(chat_ids),
        digest_blocks=digest_blocks,
        other_incoming=other_incoming,
        ambiguous_only=ambiguous_only,
        errors=errors,
        any_from_me_missing_global=any_from_me_missing_global,
    )

    md_path = out_dir / f"{prefix}_telegram_analysis.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(dump_path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
