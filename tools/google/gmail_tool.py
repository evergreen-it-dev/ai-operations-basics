#!/usr/bin/env python3
"""
Gmail: мітки, фільтри, список листів, зняття мітки непрочитаного, compose (draft/send).

За замовчуванням OAuth (особистий Gmail): спочатку один раз `python oauth_login.py`.
Альтернатива: `--auth service-account` і ключ SA + за потреби `--impersonate`.

Приклади:
  python oauth_login.py
  python gmail_tool.py labels
  python gmail_tool.py filters
  python gmail_tool.py labels --save
  python gmail_tool.py messages --preset unread --max 50 --save
  python gmail_tool.py messages --preset unread-24h --max 80 --save
  python gmail_tool.py messages --filter-match example.com --preset unread --save
  python gmail_tool.py mark-read --ids abc123 def456
  python gmail_tool.py forward --id abc123 --to colleague@example.com --note "Дивись нижче"
  python gmail_tool.py compose --to me@example.com --subject "Hi" --body "Text"
  python gmail_tool.py compose --to me@example.com --subject "Hi" --body-file letter.txt --mode send --apply
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from email import message_from_bytes
from email.header import Header
from email.mime.message import MIMEMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from _auth import get_credentials_for_tool
from _output import write_json_output

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.settings.basic",
]


def _service(args):
    creds = get_credentials_for_tool(
        SCOPES,
        auth=args.auth,
        oauth_client_secret=args.client_secret,
        oauth_token=args.token,
        sa_credentials=args.credentials,
        impersonate=args.impersonate,
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _maybe_save(args, stem: str, data: Any) -> None:
    if not getattr(args, "save", False):
        return
    path = write_json_output(data, stem, output_dir=getattr(args, "output_dir", None))
    print(path, file=sys.stderr)


def criteria_to_gmail_query(criteria: dict) -> str:
    """Критерії збереженого фільтра Gmail → рядок пошуку (оператори)."""
    if not criteria:
        return ""
    parts: list[str] = []
    q = (criteria.get("query") or "").strip()
    if q:
        parts.append(f"({q})" if (" OR " in q or " or " in q.lower()) else q)
    if fr := (criteria.get("from") or "").strip():
        parts.append(f"from:{fr}")
    if to := (criteria.get("to") or "").strip():
        parts.append(f"to:{to}")
    if sub := (criteria.get("subject") or "").strip():
        parts.append(f"subject:{sub}")
    if nq := (criteria.get("negatedQuery") or "").strip():
        parts.append(f"-({nq})" if (" " in nq or "OR" in nq.upper()) else f"-{nq}")
    if criteria.get("hasAttachment") is True:
        parts.append("has:attachment")
    if criteria.get("excludeChats") is True:
        parts.append("-in:chats")
    return " ".join(parts).strip()


QUERY_PRESETS: dict[str, str] = {
    "unread": "is:unread",
    "last-24h": "newer_than:1d",
    "unread-24h": "is:unread newer_than:1d",
}


def find_saved_filter(
    svc,
    filter_id: str | None,
    filter_match: str | None,
) -> dict | None:
    """Знаходить фільтр за точним id або підрядком у id/criteria JSON."""
    if filter_id is not None:
        filter_id = filter_id.strip() or None
    if filter_match is not None:
        filter_match = filter_match.strip() or None
    if not filter_id and not filter_match:
        return None
    res = svc.users().settings().filters().list(userId="me").execute()
    filters = res.get("filter", [])
    if filter_id:
        for f in filters:
            if f.get("id") == filter_id:
                return f
        raise SystemExit(f"Фільтр із таким id не знайдено: {filter_id!r}")
    needle = filter_match.strip().lower()
    for f in filters:
        if needle in (f.get("id") or "").lower():
            return f
        crit = json.dumps(f.get("criteria") or {}, ensure_ascii=False).lower()
        if needle in crit:
            return f
    raise SystemExit(f"Фільтр за підрядком не знайдено: {filter_match!r}")


def resolve_list_query(svc, args) -> tuple[str | None, dict | None]:
    """Підсумковий рядок q для messages.list і за потреби знайдений фільтр."""
    parts: list[str] = []
    fl = find_saved_filter(svc, args.filter_id, args.filter_match)
    if fl:
        cq = criteria_to_gmail_query(fl.get("criteria") or {})
        if cq:
            parts.append(cq)
    if getattr(args, "preset", None):
        parts.append(QUERY_PRESETS[args.preset])
    if args.query:
        parts.append(args.query.strip())
    q = " ".join(parts).strip()
    return (q or None), fl


def cmd_labels(svc, args) -> int:
    res = svc.users().labels().list(userId="me").execute()
    labels = res.get("labels", [])
    _maybe_save(
        args,
        "gmail_labels",
        {"labels": labels, "source": "users.labels.list"},
    )
    for lab in labels:
        print(f"{lab.get('id', '')}\t{lab.get('name', '')}\t{type_label(lab)}")
    return 0


def type_label(lab: dict) -> str:
    if lab.get("type") == "system":
        return "системна"
    return "користувацька"


def cmd_filters(svc, args) -> int:
    res = svc.users().settings().filters().list(userId="me").execute()
    filters = res.get("filter", [])
    _maybe_save(
        args,
        "gmail_filters",
        {"filters": filters, "source": "users.settings.filters.list"},
    )
    if args.json:
        print(json.dumps(filters, ensure_ascii=False, indent=2))
        return 0
    for f in filters:
        fid = f.get("id", "")
        crit = f.get("criteria", {})
        action = f.get("action", {})
        crit_s = json.dumps(crit, ensure_ascii=False)
        act_s = json.dumps(action, ensure_ascii=False)
        print(f"{fid}\t{crit_s}\t{act_s}")
    return 0


def resolve_label_id(svc, label_id: str | None, label_name: str | None) -> str | None:
    if label_id:
        return label_id
    if not label_name:
        return None
    res = svc.users().labels().list(userId="me").execute()
    name_lower = label_name.strip().lower()
    for lab in res.get("labels", []):
        if lab.get("name", "").lower() == name_lower or lab.get("id", "").lower() == name_lower:
            return lab["id"]
    raise SystemExit(f"Мітку не знайдено: {label_name!r}")


def cmd_messages(svc, args) -> int:
    label_ids: list[str] = []
    lid = resolve_label_id(svc, args.label, args.label_name)
    if lid:
        label_ids.append(lid)

    q, used_filter = resolve_list_query(svc, args)

    req = svc.users().messages().list(
        userId="me",
        q=q,
        labelIds=label_ids or None,
        maxResults=args.max,
    )
    res = req.execute()
    msgs = res.get("messages", [])
    fmt = args.format
    collected: list[Any] = []
    for m in msgs:
        mid = m["id"]
        if fmt == "ids":
            collected.append({"id": mid})
            print(mid)
            continue
        api_format = fmt if fmt in ("full", "raw", "metadata") else "metadata"
        full = (
            svc.users()
            .messages()
            .get(
                userId="me",
                id=mid,
                format=api_format,
                metadataHeaders=["Subject", "From", "Date"],
            )
            .execute()
        )
        if fmt == "json":
            collected.append(full)
            print(json.dumps(full, ensure_ascii=False, indent=2))
        else:
            hdrs = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
            subj = hdrs.get("Subject", "")
            frm = hdrs.get("From", "")
            unread = "UNREAD" in full.get("labelIds", [])
            collected.append(
                {
                    "id": mid,
                    "from": frm,
                    "subject": subj,
                    "snippet": full.get("snippet", ""),
                    "unread": unread,
                    "labelIds": full.get("labelIds", []),
                }
            )
            print(f"{mid}\t{'U' if unread else ' '}\t{frm[:60]}\t{subj[:80]}")
    save_params = {
        "label": args.label,
        "label_name": args.label_name,
        "query": args.query,
        "preset": getattr(args, "preset", None),
        "filter_id": getattr(args, "filter_id", None),
        "filter_match": getattr(args, "filter_match", None),
        "resolved_query": q,
        "max": args.max,
        "format": args.format,
    }
    if used_filter:
        save_params["matched_filter"] = {
            "id": used_filter.get("id"),
            "criteria": used_filter.get("criteria"),
        }
    _maybe_save(
        args,
        "gmail_messages",
        {
            "params": save_params,
            "items": collected,
        },
    )
    return 0


def cmd_mark_read(svc, args) -> int:
    body: dict[str, Any] = {"removeLabelIds": ["UNREAD"]}
    for mid in args.ids:
        svc.users().messages().modify(userId="me", id=mid, body=body).execute()
        print(mid, "готово")
    _maybe_save(
        args,
        "gmail_mark_read",
        {"removed_unread_from": list(args.ids)},
    )
    return 0


def _encode_subject(subject: str) -> str:
    subject = (subject or "").strip() or "(no subject)"
    try:
        subject.encode("ascii")
        return subject
    except UnicodeEncodeError:
        return str(Header(subject, "utf-8"))


def cmd_forward(svc, args) -> int:
    """Пересилання існуючого листа як вкладення message/rfc822 (як у клієнті Gmail)."""
    prof = svc.users().getProfile(userId="me").execute()
    me = prof["emailAddress"]

    orig_wrap = (
        svc.users()
        .messages()
        .get(userId="me", id=args.message_id.strip(), format="raw")
        .execute()
    )
    raw_bytes = base64.urlsafe_b64decode(orig_wrap["raw"].encode("ascii"))
    original = message_from_bytes(raw_bytes)

    subj = original.get("Subject", "") or ""
    if not subj.strip().lower().startswith("fwd:"):
        subj = "Fwd: " + subj.strip()

    msg = MIMEMultipart("mixed")
    msg["Subject"] = _encode_subject(subj)
    msg["To"] = args.to.strip()
    msg["From"] = me

    if getattr(args, "note", None) and args.note.strip():
        msg.attach(MIMEText(args.note.strip() + "\n\n", "plain", "utf-8"))

    enc = MIMEMessage(original)
    enc["Content-Disposition"] = "inline"
    msg.attach(enc)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(sent["id"], "надіслано ->", args.to.strip())
    _maybe_save(
        args,
        "gmail_forward",
        {"from_message_id": args.message_id, "to": args.to.strip(), "sent_id": sent.get("id")},
    )
    return 0


def _read_compose_body(args) -> str:
    file_path = getattr(args, "body_file", None)
    inline = getattr(args, "body", None)
    if file_path:
        text = Path(file_path).expanduser().read_text(encoding="utf-8")
        if inline:
            raise SystemExit("Вкажіть або --body, або --body-file, не обидва.")
        return text
    if inline is None:
        raise SystemExit("Потрібен --body або --body-file.")
    return inline


def _build_compose_raw(
    *,
    me: str,
    to: str,
    subject: str,
    body: str,
    html: bool,
    cc: str | None,
) -> str:
    msg = MIMEText(body, "html" if html else "plain", "utf-8")
    msg["To"] = to.strip()
    msg["From"] = me
    msg["Subject"] = _encode_subject(subject)
    if cc and cc.strip():
        msg["Cc"] = cc.strip()
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def cmd_compose(svc, args) -> int:
    """Draft або send. Без --apply — лише dry-run (нічого не створює)."""
    prof = svc.users().getProfile(userId="me").execute()
    me = prof["emailAddress"]
    body = _read_compose_body(args)
    to = args.to.strip()
    subject = args.subject
    raw = _build_compose_raw(
        me=me,
        to=to,
        subject=subject,
        body=body,
        html=bool(args.html),
        cc=getattr(args, "cc", None),
    )
    payload = {
        "mode": args.mode,
        "from": me,
        "to": to,
        "cc": (getattr(args, "cc", None) or "").strip() or None,
        "subject": subject,
        "html": bool(args.html),
        "body_chars": len(body),
    }
    if not args.apply:
        print("DRY-RUN: додайте --apply щоб створити draft або надіслати")
        preview = dict(payload)
        preview["body_preview"] = body[:800]
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        _maybe_save(args, "gmail_compose_dry_run", preview)
        return 0
    if args.mode == "draft":
        created = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        msg = created.get("message") or {}
        print(created.get("id"), "draft", msg.get("id") or "")
        payload["draft_id"] = created.get("id")
        payload["message_id"] = msg.get("id")
        _maybe_save(args, "gmail_compose_draft", payload)
        return 0
    sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(sent["id"], "надіслано ->", to)
    payload["sent_id"] = sent.get("id")
    _maybe_save(args, "gmail_compose_send", payload)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Gmail через API (OAuth або service account)")
    p.add_argument(
        "--auth",
        choices=("oauth", "service-account"),
        default="oauth",
        help="Спосіб входу (за замовчуванням OAuth для особистої пошти)",
    )
    p.add_argument(
        "--client-secret",
        default=None,
        help="JSON OAuth client (Desktop); інакше workspace/keys/client_secret_*.json або GOOGLE_OAUTH_CLIENT_SECRET",
    )
    p.add_argument(
        "--token",
        default=None,
        help="Файл збереженого токена; інакше workspace/keys/google_oauth_token.json або GOOGLE_OAUTH_TOKEN",
    )
    p.add_argument(
        "--credentials",
        help="Лише для --auth service-account: JSON сервісного акаунта",
    )
    p.add_argument(
        "--impersonate",
        help="Лише для service account + Workspace: user@domain (або GOOGLE_IMPERSONATE_USER)",
    )
    _save = argparse.ArgumentParser(add_help=False)
    _save.add_argument(
        "--save",
        action="store_true",
        help="Додатково зберегти результат у JSON у каталозі output (шлях — у stderr)",
    )
    _save.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Каталог для JSON (за замовчуванням tools/google/output)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("labels", parents=[_save], help="Список міток (id, назва)")
    sp.set_defaults(func=cmd_labels)

    sp = sub.add_parser("filters", parents=[_save], help="Список фільтрів Gmail")
    sp.add_argument("--json", action="store_true", help="Повний JSON")
    sp.set_defaults(func=cmd_filters)

    sp = sub.add_parser("messages", parents=[_save], help="Список повідомлень")
    sp.add_argument("--label", help="ID мітки (наприклад INBOX)")
    sp.add_argument("--label-name", help="Назва мітки (пошук без урахування регістру)")
    sp.add_argument(
        "--preset",
        choices=tuple(QUERY_PRESETS.keys()),
        default=None,
        help="Готовий запит: unread | last-24h | unread-24h (разом із -q і фільтром)",
    )
    sp.add_argument(
        "--filter-id",
        default=None,
        help="ID збереженого фільтра Gmail (перша колонка у filters)",
    )
    sp.add_argument(
        "--filter-match",
        metavar="SUBSTR",
        default=None,
        help="Підрядок у id фільтра або в JSON критеріїв (перше збіг)",
    )
    sp.add_argument("--query", "-q", help="Додатковий пошуковий запит Gmail")
    sp.add_argument("--max", type=int, default=20)
    sp.add_argument("--format", choices=["summary", "ids", "json", "metadata"], default="summary")
    sp.set_defaults(func=cmd_messages)

    sp = sub.add_parser("mark-read", parents=[_save], help="Зняти UNREAD із повідомлень")
    sp.add_argument("--ids", nargs="+", required=True, metavar="ID")
    sp.set_defaults(func=cmd_mark_read)

    sp = sub.add_parser("forward", parents=[_save], help="Переслати лист на адресу (потрібен scope gmail.send)")
    sp.add_argument("--id", dest="message_id", required=True, metavar="MSG_ID", help="id повідомлення Gmail API")
    sp.add_argument("--to", required=True, help="Email отримувача")
    sp.add_argument("--note", default="", help="Короткий текст перед пересланим листом")
    sp.set_defaults(func=cmd_forward)

    sp = sub.add_parser(
        "compose",
        parents=[_save],
        help="Створити draft або надіслати лист (без --apply — dry-run)",
    )
    sp.add_argument("--to", required=True, help="Email отримувача")
    sp.add_argument("--subject", required=True, help="Тема")
    sp.add_argument("--body", help="Текст листа (plain або HTML з --html)")
    sp.add_argument("--body-file", help="Файл з тілом листа")
    sp.add_argument("--cc", default="", help="Копія (необовʼязково)")
    sp.add_argument("--html", action="store_true", help="Тіло як text/html")
    sp.add_argument(
        "--mode",
        choices=("draft", "send"),
        default="draft",
        help="draft (чернетка) або send (надіслати); за замовчуванням draft",
    )
    sp.add_argument(
        "--apply",
        action="store_true",
        help="Реально створити draft / надіслати (інакше лише preview)",
    )
    sp.set_defaults(func=cmd_compose)

    args = p.parse_args()
    try:
        svc = _service(args)
        return args.func(svc, args)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    except HttpError as e:
        print(e, file=sys.stderr)
        if e.resp.status == 403:
            print(
                "\nПідказка: для особистого Gmail використовуйте --auth oauth і `python oauth_login.py`. "
                "Для service account потрібні delegation та --impersonate.",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
