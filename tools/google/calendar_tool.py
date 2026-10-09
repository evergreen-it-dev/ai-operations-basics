#!/usr/bin/env python3
"""
Події Google Calendar (у т.ч. needsAction — запрошення без відповіді).

За замовчуванням OAuth: один раз `python oauth_login.py`.
Service account: надайте доступ до календаря для SA або `--auth service-account --impersonate`.

Приклади:
  python oauth_login.py
  python calendar_tool.py events --preset today --save
  python calendar_tool.py events --preset week --save
  python calendar_tool.py events --calendar primary --needs-action
  python calendar_tool.py create --summary "Інтервʼю" --start 2026-07-22T15:00 --end 2026-07-22T16:00 --attendees a@x.com
  python calendar_tool.py create ... --meet --apply
  python calendar_tool.py update --event-id EVENT_ID --start 2026-07-22T16:00 --end 2026-07-22T17:00 --apply
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from _auth import get_credentials_for_tool
from _output import write_json_output


def _maybe_save(args, stem: str, data) -> None:
    if not getattr(args, "save", False):
        return
    path = write_json_output(data, stem, output_dir=getattr(args, "output_dir", None))
    print(path, file=sys.stderr)


READ_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
WRITE_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
WRITE_COMMANDS = frozenset({"create", "update", "get"})


def _local_tz_name() -> str:
    tz = datetime.now().astimezone().tzinfo
    key = getattr(tz, "key", None)
    if key:
        return key
    try:
        tz_path = Path("/etc/localtime").resolve()
        parts = tz_path.parts
        if "zoneinfo" in parts:
            idx = parts.index("zoneinfo")
            return "/".join(parts[idx + 1 :])
    except (OSError, ValueError):
        pass
    return "UTC"


def _parse_date_or_datetime(value: str) -> datetime | None:
    value = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    if len(value) == 10:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None
    return None


def _event_time_field(value: str, *, all_day: bool, tz_name: str) -> dict[str, str]:
    if all_day:
        if len(value) != 10:
            raise SystemExit(f"Помилка: для all-day очікується YYYY-MM-DD, отримано: {value!r}")
        return {"date": value}
    parsed = _parse_date_or_datetime(value)
    if parsed is None:
        raise SystemExit(f"Помилка: не вдалося розпарсити дату/час: {value!r}")
    if parsed.tzinfo is not None:
        return {"dateTime": parsed.isoformat()}
    return {"dateTime": parsed.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": tz_name}


def _parse_attendees(raw: str | None) -> list[dict[str, str]]:
    if not raw:
        return []
    return [{"email": email.strip()} for email in raw.split(",") if email.strip()]


def _build_event_body(args, *, existing: dict[str, Any] | None = None, patch: bool = False) -> dict[str, Any]:
    existing = existing or {}
    tz_name = args.timezone or _local_tz_name()
    all_day = bool(args.all_day)
    body: dict[str, Any] = {}

    if args.summary is not None or (not patch and existing.get("summary")):
        summary = args.summary if args.summary is not None else existing.get("summary")
        if summary is not None:
            body["summary"] = summary

    if args.description is not None:
        body["description"] = args.description
    elif not patch and existing.get("description"):
        body["description"] = existing["description"]

    if args.location is not None:
        body["location"] = args.location
    elif not patch and existing.get("location"):
        body["location"] = existing["location"]

    if args.start is not None:
        body["start"] = _event_time_field(args.start, all_day=all_day, tz_name=tz_name)
    elif not patch and existing.get("start"):
        body["start"] = existing["start"]

    if args.end is not None:
        body["end"] = _event_time_field(args.end, all_day=all_day, tz_name=tz_name)
    elif not patch and existing.get("end"):
        body["end"] = existing["end"]

    if args.attendees is not None:
        body["attendees"] = _parse_attendees(args.attendees)
    elif not patch and existing.get("attendees"):
        body["attendees"] = existing["attendees"]

    if getattr(args, "meet", False):
        body["conferenceData"] = {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    if args.reminder_minutes is not None:
        body["reminders"] = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": int(args.reminder_minutes)}],
        }
    elif not patch and existing.get("reminders"):
        body["reminders"] = existing["reminders"]

    if not patch:
        missing = [field for field in ("summary", "start", "end") if not body.get(field)]
        if missing:
            raise SystemExit(f"Помилка: бракує полів події: {', '.join(missing)}")
    elif not body:
        raise SystemExit("Помилка: для update вкажіть хоча б одне поле для зміни")
    return body


def _emit_result(payload: dict[str, Any], args) -> int:
    _maybe_save(args, "calendar_event", payload)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    action = payload.get("action", "")
    if action == "dry_run":
        print("DRY-RUN: подію не створено/не оновлено. Додайте --apply для запису в календар.")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _range_iso(from_day: str, to_day: str) -> tuple[str, str]:
    """
    Межі для events.list: початок першого дня та виключаючий кінець після останнього дня.
    Дати YYYY-MM-DD трактуються в локальній часовій зоні системи.
    """
    tz = datetime.now().astimezone().tzinfo or timezone.utc
    d0 = datetime.strptime(from_day, "%Y-%m-%d").date()
    d1 = datetime.strptime(to_day, "%Y-%m-%d").date()
    if d1 < d0:
        raise SystemExit("Помилка: --to раніше за --from")
    start_local = datetime.combine(d0, datetime.min.time(), tzinfo=tz)
    end_exclusive_local = datetime.combine(d1 + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    return (
        start_local.astimezone(timezone.utc).isoformat(),
        end_exclusive_local.astimezone(timezone.utc).isoformat(),
    )


def apply_preset(args) -> None:
    """Підставляє --from / --to за локальною датою (часовий пояс машини)."""
    if not getattr(args, "preset", None):
        return
    loc = datetime.now().astimezone().date()
    if args.preset == "today":
        s = loc.isoformat()
        args.from_day = s
        args.to_day = s
    elif args.preset == "week":
        mon = loc - timedelta(days=loc.weekday())
        sun = mon + timedelta(days=6)
        args.from_day = mon.isoformat()
        args.to_day = sun.isoformat()


def _service(args, *, write: bool = False):
    scopes = WRITE_SCOPES if write else READ_SCOPES
    creds = get_credentials_for_tool(
        scopes,
        auth=args.auth,
        oauth_client_secret=args.client_secret,
        oauth_token=args.token,
        sa_credentials=args.credentials,
        impersonate=args.impersonate,
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _add_write_event_args(sp: argparse.ArgumentParser, *, require_core: bool = False) -> None:
    sp.add_argument("--calendar", default="primary", help="ID календаря або primary")
    sp.add_argument(
        "--summary",
        required=require_core,
        default=None,
        help="Тема події",
    )
    sp.add_argument("--description", default=None, help="Опис")
    sp.add_argument("--location", default=None, help="Локація")
    sp.add_argument(
        "--start",
        required=require_core,
        default=None,
        help="Початок: YYYY-MM-DD або YYYY-MM-DDTHH:MM[:SS]",
    )
    sp.add_argument(
        "--end",
        required=require_core,
        default=None,
        help="Кінець: YYYY-MM-DD або YYYY-MM-DDTHH:MM[:SS]",
    )
    sp.add_argument(
        "--timezone",
        default=None,
        help="IANA timezone для start/end без offset (за замовч. — локальна зона машини)",
    )
    sp.add_argument("--all-day", action="store_true", help="Цілоденна подія (start/end як YYYY-MM-DD)")
    sp.add_argument("--attendees", default=None, help="Email гостей через кому")
    sp.add_argument("--meet", action="store_true", help="Додати Google Meet (лише create)")
    sp.add_argument("--reminder-minutes", type=int, default=None, help="Popup-нагадування за N хвилин")
    sp.add_argument(
        "--send-updates",
        choices=("none", "all", "externalOnly"),
        default="none",
        help="Надсилати запрошення гостям при --apply (за замовч. none)",
    )
    sp.add_argument(
        "--apply",
        action="store_true",
        help="Записати в календар (без цього прапорця — лише dry-run)",
    )
    sp.add_argument("--json", action="store_true")


def cmd_create(svc, args) -> int:
    body = _build_event_body(args)
    payload: dict[str, Any] = {
        "action": "dry_run",
        "calendar": args.calendar,
        "body": body,
        "sendUpdates": args.send_updates,
    }
    if not args.apply:
        return _emit_result(payload, args)

    insert_kwargs: dict[str, Any] = {
        "calendarId": args.calendar,
        "body": body,
        "sendUpdates": args.send_updates,
    }
    if args.meet:
        insert_kwargs["conferenceDataVersion"] = 1
    created = svc.events().insert(**insert_kwargs).execute()
    payload = {
        "action": "created",
        "calendar": args.calendar,
        "id": created.get("id"),
        "htmlLink": created.get("htmlLink"),
        "hangoutLink": created.get("hangoutLink"),
        "event": created,
    }
    return _emit_result(payload, args)


def cmd_update(svc, args) -> int:
    if not args.event_id:
        raise SystemExit("Помилка: для update потрібен --event-id")
    existing = svc.events().get(calendarId=args.calendar, eventId=args.event_id).execute()
    body = _build_event_body(args, existing=existing, patch=True)
    payload: dict[str, Any] = {
        "action": "dry_run",
        "calendar": args.calendar,
        "event_id": args.event_id,
        "body": body,
        "sendUpdates": args.send_updates,
    }
    if not args.apply:
        return _emit_result(payload, args)

    updated = (
        svc.events()
        .patch(
            calendarId=args.calendar,
            eventId=args.event_id,
            body=body,
            sendUpdates=args.send_updates,
        )
        .execute()
    )
    payload = {
        "action": "updated",
        "calendar": args.calendar,
        "id": updated.get("id"),
        "htmlLink": updated.get("htmlLink"),
        "hangoutLink": updated.get("hangoutLink"),
        "event": updated,
    }
    return _emit_result(payload, args)


def cmd_get(svc, args) -> int:
    if not args.event_id:
        raise SystemExit("Помилка: для get потрібен --event-id")
    event = svc.events().get(calendarId=args.calendar, eventId=args.event_id).execute()
    payload = {"action": "get", "calendar": args.calendar, "event": event}
    return _emit_result(payload, args)


def attendees_need_action(event: dict, own_email: str | None) -> bool:
    for a in event.get("attendees") or []:
        if not a.get("self"):
            continue
        st = a.get("responseStatus")
        if st == "needsAction":
            return True
        if own_email and a.get("email", "").lower() == own_email.lower() and st == "needsAction":
            return True
    return False


def cmd_events(svc, args) -> int:
    apply_preset(args)
    t_min, t_max = _range_iso(args.from_day, args.to_day)

    cal_id = args.calendar
    body_params = {
        "calendarId": cal_id,
        "timeMin": t_min,
        "timeMax": t_max,
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": args.max,
        "showDeleted": False,
    }
    events_result = svc.events().list(**body_params).execute()
    items = events_result.get("items", [])

    out: list[dict] = []
    for ev in items:
        status = ev.get("status")
        if args.only_tentative and status != "tentative":
            continue
        if args.needs_action and not attendees_need_action(ev, args.own_email):
            continue
        out.append(ev)

    save_payload = {
        "params": {
            "calendar": cal_id,
            "preset": getattr(args, "preset", None),
            "from": args.from_day,
            "to": args.to_day,
            "max": args.max,
            "needs_action": args.needs_action,
            "only_tentative": args.only_tentative,
            "own_email": args.own_email,
        },
        "events": out,
    }
    _maybe_save(args, "calendar_events", save_payload)

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    for ev in out:
        start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", "")
        summ = ev.get("summary", "(без теми)")
        st = ev.get("status", "")
        att_self = next((a for a in (ev.get("attendees") or []) if a.get("self")), None)
        rsp = att_self.get("responseStatus", "") if att_self else ""
        print(f"{start}\t{st}\t{rsp}\t{summ[:100]}")

    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Google Calendar (OAuth або service account)")
    p.add_argument(
        "--auth",
        choices=("oauth", "service-account"),
        default="oauth",
        help="За замовчуванням OAuth",
    )
    p.add_argument("--client-secret", default=None)
    p.add_argument("--token", default=None)
    p.add_argument("--credentials", default=None, help="JSON SA для --auth service-account")
    p.add_argument("--impersonate", default=None)
    _save = argparse.ArgumentParser(add_help=False)
    _save.add_argument(
        "--save",
        action="store_true",
        help="Зберегти події у JSON у каталозі output",
    )
    _save.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Каталог для JSON (за замовчуванням tools/google/output)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    today = datetime.now().astimezone().date()
    default_from = today.isoformat()
    default_to = (today + timedelta(days=30)).isoformat()

    sp = sub.add_parser("events", parents=[_save], help="Список подій за період")
    sp.add_argument("--calendar", default="primary", help="ID календаря або primary при delegation")
    sp.add_argument(
        "--preset",
        choices=("today", "week"),
        default=None,
        help="Діапазон за локальною датою: today (сьогодні), week (пн–нд поточного тижня); перекриває --from/--to",
    )
    sp.add_argument("--from", dest="from_day", default=default_from, help="Початок періоду YYYY-MM-DD (локальний календарний день)")
    sp.add_argument("--to", dest="to_day", default=default_to, help="Кінець періоду YYYY-MM-DD включно (локально)")
    sp.add_argument("--max", type=int, default=250)
    sp.add_argument("--needs-action", action="store_true", help="Лише запрошення без відповіді (self needsAction)")
    sp.add_argument("--only-tentative", action="store_true", help="Лише з status=tentative")
    sp.add_argument("--own-email", dest="own_email", default=None, help="Email для перевірки needsAction")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_events)

    cp = sub.add_parser("create", parents=[_save], help="Створити подію (за замовч. dry-run)")
    _add_write_event_args(cp, require_core=True)
    cp.set_defaults(func=cmd_create)

    up = sub.add_parser("update", parents=[_save], help="Оновити подію (за замовч. dry-run)")
    up.add_argument("--event-id", required=True, help="ID події в Google Calendar")
    _add_write_event_args(up)
    up.set_defaults(func=cmd_update)

    gp = sub.add_parser("get", parents=[_save], help="Отримати подію за ID")
    gp.add_argument("--calendar", default="primary")
    gp.add_argument("--event-id", required=True)
    gp.add_argument("--json", action="store_true")
    gp.set_defaults(func=cmd_get)

    args = p.parse_args()
    try:
        svc = _service(args, write=args.cmd in WRITE_COMMANDS)
        return args.func(svc, args)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    except HttpError as e:
        print(e, file=sys.stderr)
        if e.resp.status in (403, 404):
            reason = ""
            try:
                details = json.loads(e.content.decode("utf-8")).get("error", {}).get("errors", [])
                reason = details[0].get("reason", "") if details else ""
            except (json.JSONDecodeError, UnicodeDecodeError, IndexError, AttributeError):
                pass
            if reason == "accessNotConfigured":
                print(
                    "\nПідказка: увімкніть Google Calendar API в GCP Console для OAuth-проєкту "
                    "(номер проєкту — у client_secret_*.json), потім зачекайте 1–2 хв:\n"
                    "https://console.developers.google.com/apis/api/calendar-json.googleapis.com/overview\n"
                    "Далі: `python oauth_login.py` (якщо scope ще не в токені) і повторіть команду.",
                    file=sys.stderr,
                )
            else:
                print(
                    "\nПідказка: для OAuth виконайте `python oauth_login.py`. "
                    "Для SA надайте доступ до календаря сервісному акаунту або використайте --impersonate.",
                    file=sys.stderr,
                )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
