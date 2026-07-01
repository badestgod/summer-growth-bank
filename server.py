from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Final
from urllib.parse import parse_qs, urlparse

DB_PATH: Final = os.environ.get("GROWTH_BANK_DB", "/var/lib/summer-growth-bank/growth-bank.sqlite3")
HOST: Final = "127.0.0.1"
PORT: Final = int(os.environ.get("GROWTH_BANK_PORT", "8765"))
MAX_BODY_BYTES: Final = 1_000_000
USERNAME_RE: Final = re.compile(r"^[0-9A-Za-z_\-\u4e00-\u9fff]{3,32}$")
JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class ApiError(Exception):
    status: HTTPStatus
    message: str

    def __str__(self) -> str:
        return self.message


def connect_db() -> sqlite3.Connection:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute("CREATE TABLE IF NOT EXISTS accounts (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, salt TEXT NOT NULL, state_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    connection.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, username TEXT NOT NULL REFERENCES accounts(username), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    return connection


def validate_username(username: str) -> str:
    normalized = username.strip()
    if not USERNAME_RE.fullmatch(normalized):
        raise ApiError(HTTPStatus.BAD_REQUEST, "用户名需为 3-32 位，可用中文、字母、数字、下划线或横线。")
    return normalized


def validate_password(password: str) -> str:
    if len(password) < 6:
        raise ApiError(HTTPStatus.BAD_REQUEST, "密码至少需要 6 位。")
    return password


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return digest.hex()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def parse_state_json(state_json: str) -> str:
    parsed = json.loads(state_json)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("profiles"), list):
        raise ApiError(HTTPStatus.BAD_REQUEST, "保存数据格式不正确。")
    return json.dumps(parsed, ensure_ascii=False)


def create_session(connection: sqlite3.Connection, username: str) -> str:
    token = secrets.token_urlsafe(32)
    connection.execute("INSERT INTO sessions (token_hash, username) VALUES (?, ?)", (hash_token(token), username))
    return token


def register_account(username: str, password: str, state_json: str) -> tuple[str, str]:
    account_name = validate_username(username)
    account_password = validate_password(password)
    salt = secrets.token_hex(16)
    with connect_db() as connection:
        existing = connection.execute("SELECT 1 FROM accounts WHERE username = ?", (account_name,)).fetchone()
        if existing is not None:
            raise ApiError(HTTPStatus.CONFLICT, "用户名已存在，请直接登录或换一个用户名。")
        connection.execute("INSERT INTO accounts (username, password_hash, salt, state_json) VALUES (?, ?, ?, ?)", (account_name, hash_password(account_password, salt), salt, parse_state_json(state_json)))
        return account_name, create_session(connection, account_name)


def login_account(username: str, password: str) -> tuple[str, str, str]:
    account_name = validate_username(username)
    account_password = validate_password(password)
    with connect_db() as connection:
        row = connection.execute("SELECT password_hash, salt, state_json FROM accounts WHERE username = ?", (account_name,)).fetchone()
        if row is None:
            raise ApiError(HTTPStatus.UNAUTHORIZED, "用户名或密码不正确。")
        saved_hash, salt, state_json = str(row[0]), str(row[1]), str(row[2])
        if not hmac.compare_digest(saved_hash, hash_password(account_password, salt)):
            raise ApiError(HTTPStatus.UNAUTHORIZED, "用户名或密码不正确。")
        return account_name, create_session(connection, account_name), state_json


def username_for_token(connection: sqlite3.Connection, token: str) -> str:
    row = connection.execute("SELECT username FROM sessions WHERE token_hash = ?", (hash_token(token),)).fetchone()
    if row is None:
        raise ApiError(HTTPStatus.UNAUTHORIZED, "登录已失效，请重新登录。")
    return str(row[0])


def load_state(token: str) -> tuple[str, str]:
    with connect_db() as connection:
        username = username_for_token(connection, token)
        row = connection.execute("SELECT state_json FROM accounts WHERE username = ?", (username,)).fetchone()
    if row is None:
        raise ApiError(HTTPStatus.UNAUTHORIZED, "账号不存在，请重新登录。")
    return username, str(row[0])


def save_state(token: str, state_json: str) -> None:
    with connect_db() as connection:
        username = username_for_token(connection, token)
        connection.execute("UPDATE accounts SET state_json = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?", (parse_state_json(state_json), username))


class GrowthBankHandler(BaseHTTPRequestHandler):
    server_version = "GrowthBank/2.0"

    def do_GET(self) -> None:
        try:
            parsed_url = urlparse(self.path)
            if parsed_url.path != "/api/state":
                raise ApiError(HTTPStatus.NOT_FOUND, "接口不存在。")
            params = parse_qs(parsed_url.query)
            username, state_json = load_state(params.get("token", [""])[0])
            self.write_json({"username": username, "state": json.loads(state_json)})
        except ApiError as error:
            self.write_error(error)

    def do_POST(self) -> None:
        try:
            parsed_url = urlparse(self.path)
            body = self.read_json_body()
            match parsed_url.path:
                case "/api/register":
                    self.handle_register(body)
                case "/api/login":
                    self.handle_login(body)
                case "/api/state":
                    self.handle_save_state(body)
                case _:
                    raise ApiError(HTTPStatus.NOT_FOUND, "接口不存在。")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.write_error(ApiError(HTTPStatus.BAD_REQUEST, "请求数据不是有效 JSON。"))
        except ApiError as error:
            self.write_error(error)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.write_common_headers()
        self.end_headers()

    def handle_register(self, body: dict[str, JsonValue]) -> None:
        state = body.get("state")
        username, token = register_account(str(body.get("username", "")), str(body.get("password", "")), json.dumps(state, ensure_ascii=False))
        self.write_json({"ok": True, "username": username, "token": token})

    def handle_login(self, body: dict[str, JsonValue]) -> None:
        username, token, state_json = login_account(str(body.get("username", "")), str(body.get("password", "")))
        self.write_json({"ok": True, "username": username, "token": token, "state": json.loads(state_json)})

    def handle_save_state(self, body: dict[str, JsonValue]) -> None:
        save_state(str(body.get("token", "")), json.dumps(body.get("state"), ensure_ascii=False))
        self.write_json({"ok": True})

    def read_json_body(self) -> dict[str, JsonValue]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            raise ApiError(HTTPStatus.BAD_REQUEST, "请求数据大小不正确。")
        body = json.loads(self.rfile.read(content_length).decode("utf-8"))
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
