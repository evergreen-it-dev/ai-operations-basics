#!/usr/bin/env python3
"""
Google Drive: список файлів у папці, копіювання, переміщення, створення папки.

OAuth scope: drive (див. oauth_login.py після оновлення _auth.py).

Приклади:
  python drive_tool.py list-folder --id <FOLDER_ID>
  python drive_tool.py copy-file --id <FILE_ID> --name "Копія" [--as-gdoc]
  python drive_tool.py share-link --id <FILE_ID> --role commenter
  python drive_tool.py export-pdf --id <FILE_ID> --out /tmp/file.pdf
  python drive_tool.py export --id <FILE_ID> --format pdf|docx|pptx|txt --out /tmp/file.pdf
  python drive_tool.py move-to-folder --id <FILE_ID> --folder <FOLDER_ID>
  python drive_tool.py create-folder --name "Оффер_Іван" --parent <FOLDER_ID>
  python drive_tool.py get-meta --id <FILE_ID>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from _auth import get_credentials_for_tool
from _output import write_json_output

from _auth import ALL_OAUTH_SCOPES
SCOPES = ALL_OAUTH_SCOPES

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
PDF_MIME = "application/pdf"
EXPORT_MIMES = {
    "pdf": PDF_MIME,
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
}
GOOGLE_NATIVE_PREFIX = "application/vnd.google-apps."


def _maybe_save(args, stem: str, data: Any) -> None:
    if not getattr(args, "save", False):
        return
    path = write_json_output(data, stem, output_dir=getattr(args, "output_dir", None))
    print(path, file=sys.stderr)


def _service(args):
    creds = get_credentials_for_tool(
        SCOPES,
        auth=args.auth,
        oauth_client_secret=args.client_secret,
        oauth_token=args.token,
        sa_credentials=args.credentials,
        impersonate=args.impersonate,
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def cmd_list_folder(svc, args) -> int:
    """Список файлів і папок у вказаній папці (рекурсивно — ні, лише перший рівень)."""
    query = f"'{args.id}' in parents and trashed = false"
    fields = "files(id, name, mimeType, createdTime, modifiedTime, webViewLink)"
    results = []
    page_token = None
    while True:
        kwargs: dict = dict(q=query, fields=f"nextPageToken, {fields}", pageSize=100)
        if page_token:
            kwargs["pageToken"] = page_token
        resp = svc.files().list(**kwargs).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    _maybe_save(args, "drive_list_folder", results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def cmd_copy_file(svc, args) -> int:
    """Копіює файл. Повертає {id, name, webViewLink} нової копії."""
    body: dict = {}
    if args.name:
        body["name"] = args.name
    if args.parent:
        body["parents"] = [args.parent]
    if args.as_gdoc:
        body["mimeType"] = GOOGLE_DOC_MIME
    copied = svc.files().copy(
        fileId=args.id, body=body, fields="id,name,mimeType,webViewLink"
    ).execute()
    _maybe_save(args, "drive_copy_file", copied)
    print(json.dumps(copied, ensure_ascii=False, indent=2))
    return 0


def cmd_share_link(svc, args) -> int:
    """Відкриває доступ anyone-with-link (reader або commenter)."""
    perm = (
        svc.permissions()
        .create(
            fileId=args.id,
            body={
                "type": "anyone",
                "role": args.role,
                "allowFileDiscovery": False,
            },
            fields="id,type,role",
        )
        .execute()
    )
    meta = svc.files().get(fileId=args.id, fields="id,name,webViewLink").execute()
    out = {**meta, "permission": perm, "role": args.role}
    _maybe_save(args, "drive_share_link", out)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def _write_media(request, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _status, done = downloader.next_chunk()


def cmd_export(svc, args) -> int:
    """Експорт Google Doc/Slides або завантаження вже бінарного файлу."""
    fmt = args.format
    target_mime = EXPORT_MIMES[fmt]
    meta = svc.files().get(fileId=args.id, fields="id,name,mimeType").execute()
    src_mime = meta.get("mimeType") or ""
    out_path = Path(args.out)
    if src_mime.startswith(GOOGLE_NATIVE_PREFIX):
        request = svc.files().export_media(fileId=args.id, mimeType=target_mime)
    else:
        if src_mime != target_mime:
            print(
                f"file is {src_mime}, not a Google file; cannot convert to {fmt}",
                file=sys.stderr,
            )
            return 1
        request = svc.files().get_media(fileId=args.id)
    _write_media(request, out_path)
    print(
        json.dumps(
            {
                "id": args.id,
                "name": meta.get("name"),
                "mimeType": src_mime,
                "format": fmt,
                "out": str(out_path.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_export_pdf(svc, args) -> int:
    """Експорт Google Doc / Slides у PDF (аліас export --format pdf)."""
    args.format = "pdf"
    return cmd_export(svc, args)


def cmd_move_to_folder(svc, args) -> int:
    """Переміщає файл до нової папки (прибирає старого батька)."""
    meta = svc.files().get(fileId=args.id, fields="parents").execute()
    previous_parents = ",".join(meta.get("parents", []))
    updated = svc.files().update(
        fileId=args.id,
        addParents=args.folder,
        removeParents=previous_parents,
        fields="id,name,parents,webViewLink",
    ).execute()
    _maybe_save(args, "drive_move", updated)
    print(json.dumps(updated, ensure_ascii=False, indent=2))
    return 0


def cmd_create_folder(svc, args) -> int:
    """Створює папку (опційно в батьківській папці)."""
    body: dict = {
        "name": args.name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if args.parent:
        body["parents"] = [args.parent]
    folder = svc.files().create(body=body, fields="id,name,webViewLink").execute()
    _maybe_save(args, "drive_create_folder", folder)
    print(json.dumps(folder, ensure_ascii=False, indent=2))
    return 0


def cmd_get_meta(svc, args) -> int:
    """Метадані файлу/папки."""
    fields = "id,name,mimeType,parents,createdTime,modifiedTime,webViewLink"
    meta = svc.files().get(fileId=args.id, fields=fields).execute()
    _maybe_save(args, "drive_meta", meta)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Google Drive API (OAuth або service account)")
    p.add_argument("--auth", choices=("oauth", "service-account"), default="oauth")
    p.add_argument("--client-secret", default=None)
    p.add_argument("--token", default=None)
    p.add_argument("--credentials", default=None)
    p.add_argument("--impersonate", default=None)
    _save = argparse.ArgumentParser(add_help=False)
    _save.add_argument("--save", action="store_true")
    _save.add_argument("--output-dir", type=Path, default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list-folder", parents=[_save], help="Список файлів у папці")
    sp.add_argument("--id", required=True, help="ID папки")
    sp.set_defaults(func=cmd_list_folder)

    sp = sub.add_parser("copy-file", parents=[_save], help="Копіювати файл")
    sp.add_argument("--id", required=True, help="ID файлу-джерела")
    sp.add_argument("--name", default=None, help="Нова назва (опційно)")
    sp.add_argument("--parent", default=None, help="ID батьківської папки для копії")
    sp.add_argument(
        "--as-gdoc",
        action="store_true",
        help="Конвертувати копію в native Google Doc (для DOCX-шаблонів)",
    )
    sp.set_defaults(func=cmd_copy_file)

    sp = sub.add_parser("share-link", parents=[_save], help="Доступ anyone-with-link")
    sp.add_argument("--id", required=True, help="ID файлу")
    sp.add_argument(
        "--role",
        choices=("reader", "commenter"),
        default="commenter",
        help="reader = перегляд, commenter = коментарі (юрист NDA)",
    )
    sp.set_defaults(func=cmd_share_link)

    sp = sub.add_parser("export-pdf", parents=[_save], help="Експорт Doc/Slides у PDF")
    sp.add_argument("--id", required=True, help="ID файлу")
    sp.add_argument("--out", required=True, type=Path, help="Шлях до PDF")
    sp.set_defaults(func=cmd_export_pdf)

    sp = sub.add_parser("export", parents=[_save], help="Експорт Doc/Slides (pdf/docx/pptx/txt) або download бінаря")
    sp.add_argument("--id", required=True, help="ID файлу")
    sp.add_argument("--format", required=True, choices=sorted(EXPORT_MIMES), help="Цільовий формат")
    sp.add_argument("--out", required=True, type=Path, help="Шлях до файлу")
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("move-to-folder", parents=[_save], help="Перемістити файл до папки")
    sp.add_argument("--id", required=True, help="ID файлу")
    sp.add_argument("--folder", required=True, help="ID цільової папки")
    sp.set_defaults(func=cmd_move_to_folder)

    sp = sub.add_parser("create-folder", parents=[_save], help="Створити папку")
    sp.add_argument("--name", required=True, help="Назва папки")
    sp.add_argument("--parent", default=None, help="ID батьківської папки")
    sp.set_defaults(func=cmd_create_folder)

    sp = sub.add_parser("get-meta", parents=[_save], help="Метадані файлу/папки")
    sp.add_argument("--id", required=True, help="ID файлу/папки")
    sp.set_defaults(func=cmd_get_meta)

    args = p.parse_args()
    try:
        svc = _service(args)
        return args.func(svc, args)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    except HttpError as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
