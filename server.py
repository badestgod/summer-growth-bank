from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Final
from urllib.parse import parse_qs, urlparse

DB_PATH: Final = os.environ.get(
    "GROWTH_BANK_DB",
    "/var/lib/summer-growth-bank/growth-bank.sqlite3",
)
HOST: Final = "127.0.0.1"
PORT: Final = int(os.environ.get("GROWTH_BANK_PORT", "8765"))
MAX_BODY_BYTES: Final = 1_000_000
JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class ApiError(Exception):
    status: HTTPStatus
    message: str

    def __str__(self) -> str:
        return self.message


def key_hash(family_key: str) -> str:
    normalized = family_key.strip()
    if len(normalized) < 4:
        raise ApiError(HTTPStatus.BAD_REQUEST, "家庭口令至少需要 4 个字符。")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def connect_db() -> sqlite3.Connection:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS family_states (
            key_hash TEXT PRIMARY KEY,
            state_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    return connection


def load_state(family_key: str) -> str | None:
    with connect_db() as connection:
        row = connection.execute(
            "SELECT state_json FROM family_states WHERE key_hash = ?",
            (key_hash(family_key),),
        ).fetchone()
    return None if row is None else str(row[0])


def save_state(family_key: str, state_json: str) -> None:
    parsed = json.loads(state_json)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("profiles"), list):
        raise ApiError(HTTPStatus.BAD_REQUEST, "保存数据格式不正确。")
    with connect_db() as connection:
        connection.execute(
            """
            INSERT INTO family_states (key_hash, state_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key_hash) DO UPDATE SET
              state_json = excluded.state_json,
              updated_at = CURRENT_TIMESTAMP
            """,
            (key_hash(family_key), json.dumps(parsed, ensure_ascii=False)),
        )


class GrowthBankHandler(BaseHTTPRequestHandler):
    server_version = "GrowthBank/1.0"

    def do_GET(self) -> None:
        try:
            parsed_url = urlparse(self.path)
            if parsed_url.path != "/api/state":
                raise ApiError(HTTPStatus.NOT_FOUND, "接口不存在。")
            params = parse_qs(parsed_url.query)
            family_key = params.get("key", [""])[0]
            state_json = load_state(family_key)
            self.write_json({"found": state_json is not None, "state": json.loads(state_json) if state_json else None})
        except ApiError as error:
            self.write_error(error)

    def do_POST(self) -> None:
        try:
            parsed_url = urlparse(self.path)
            if parsed_url.path != "/api/state":
                raise ApiError(HTTPStatus.NOT_FOUND, "接口不存在。")
            body = self.read_json_body()
            family_key = str(body.get("key", ""))
            state = body.get("state")
            save_state(family_key, json.dumps(state, ensure_ascii=False))
            self.write_json({"ok": True})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.write_error(ApiError(HTTPStatus.BAD_REQUEST, "请求数据不是有效 JSON。"))
        except ApiError as error:
            self.write_error(error)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.write_common_headers()
        self.end_headers()

    def read_json_body(self) -> dict[str, JsonValue]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "请求数据大小不正确。")
        raw_body = self.rfile.read(content_length).decode("utf-8")
        body = json.loads(raw_body)
        if not isinstance(body, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "请求数据格式不正确。")
        return body

    def write_json(self, data: dict[str, JsonValue]) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.write_common_headers()
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def write_error(self, error: ApiError) -> None:
        payload = json.dumps({"error": error.message}, ensure_ascii=False).encode("utf-8")
        self.send_response(error.status)
        self.write_common_headers()
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def write_common_headers(self) -> None:
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: JsonValue) -> None:
        return


def main() -> None:
    with ThreadingHTTPServer((HOST, PORT), GrowthBankHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
