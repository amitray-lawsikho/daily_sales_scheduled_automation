"""Put the run's PDF and xlsx in Drive: Team performance & Reports > Team Uzair Performance (Amit) >
Daily Sales Check (created on the first run). A re-run for the same date replaces the files in place."""
from __future__ import annotations

import json
import os

from dsc.settings import CFG

FOLDER = "application/vnd.google-apps.folder"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
TYPES = {".pdf": "application/pdf", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def folder_id(g) -> str:
    parent, name = CFG["drive_folder_id"], CFG["drive_subfolder"]
    hits = g.find(f"'{parent}' in parents and trashed = false and mimeType = '{FOLDER}' and name = '{name}'")
    if hits:
        return hits[0]["id"]
    r = g._ok(g.s.post(g.DRIVE, params={"supportsAllDrives": "true", "fields": "id"},
                       json={"name": name, "mimeType": FOLDER, "parents": [parent]}))
    return r.json()["id"]


def upload(g, path: str, fid: str) -> str:
    name = os.path.basename(path)
    mime = TYPES[os.path.splitext(name)[1]]
    with open(path, "rb") as f:
        data = f.read()
    hits = g.find(f"'{fid}' in parents and trashed = false and name = '{name.replace(chr(39), chr(92) + chr(39))}'")
    if hits:
        file_id = hits[0]["id"]
        g._ok(g.s.patch(f"{UPLOAD}/{file_id}", params={"uploadType": "media", "supportsAllDrives": "true"},
                        data=data, headers={"Content-Type": mime}))
    else:
        b = "dsc-boundary"
        body = (f"--{b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps({'name': name, 'parents': [fid]})}\r\n--{b}\r\nContent-Type: {mime}\r\n\r\n").encode() \
            + data + f"\r\n--{b}--".encode()
        r = g._ok(g.s.post(UPLOAD, params={"uploadType": "multipart", "supportsAllDrives": "true", "fields": "id"},
                           data=body, headers={"Content-Type": f"multipart/related; boundary={b}"}))
        file_id = r.json()["id"]
    return f"https://drive.google.com/file/d/{file_id}/view"


def publish(paths: list[str]) -> dict:
    from partwise.sources import Google
    g = Google()
    fid = folder_id(g)
    return {os.path.basename(p): upload(g, p, fid) for p in paths}
