
import re
import sqlite3
import secrets
import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DB_PATH = BASE_DIR / "chat.db"

app = FastAPI(title="OIBSIP Advanced Chat Application")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

sessions: dict[str, str] = {}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, 200_000
    )
    return salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(),
            bytes.fromhex(salt_hex), 200_000
        )
        return hmac.compare_digest(actual, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                room TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_room_id
            ON messages(room, id);

            CREATE TABLE IF NOT EXISTS private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL COLLATE NOCASE,
                recipient TEXT NOT NULL COLLATE NOCASE,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_private_conversation
            ON private_messages(sender, recipient, id);
        """)


init_db()


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=24)
    password: str = Field(min_length=8, max_length=128)


@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/register")
async def register(data: Credentials):
    username = data.username.strip()

    if not re.fullmatch(r"[A-Za-z0-9_]{3,24}", username):
        raise HTTPException(
            status_code=400,
            detail="Username may contain only letters, numbers, and underscores."
        )

    with get_db() as conn:
        try:
            conn.execute(
                """INSERT INTO users
                   (username, password_hash, created_at)
                   VALUES (?, ?, ?)""",
                (username, hash_password(data.password), now_iso())
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409, detail="Username already exists."
            )

    return {"message": "Registration successful. You can now log in."}


@app.post("/api/login")
async def login(data: Credentials):
    username = data.username.strip()

    with get_db() as conn:
        row = conn.execute(
            "SELECT username, password_hash FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if not row or not verify_password(data.password, row["password_hash"]):
        raise HTTPException(
            status_code=401, detail="Invalid username or password."
        )

    token = secrets.token_urlsafe(32)
    sessions[token] = row["username"]

    return {"token": token, "username": row["username"]}


def authenticated_user(token: str) -> str | None:
    return sessions.get(token)


def message_history(room: str, limit: int = 50):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT username, room, message, timestamp
               FROM messages WHERE room = ?
               ORDER BY id DESC LIMIT ?""",
            (room, limit)
        ).fetchall()

    return [dict(row) for row in reversed(rows)]


def save_message(username: str, room: str, message: str, timestamp: str):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO messages(username, room, message, timestamp)
               VALUES (?, ?, ?, ?)""",
            (username, room, message, timestamp)
        )


def save_private_message(sender: str, recipient: str,
                         message: str, timestamp: str):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO private_messages
               (sender, recipient, message, timestamp)
               VALUES (?, ?, ?, ?)""",
            (sender, recipient, message, timestamp)
        )


def private_history(user1: str, user2: str, limit: int = 100):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT sender, recipient, message, timestamp
               FROM private_messages
               WHERE (sender = ? AND recipient = ?)
                  OR (sender = ? AND recipient = ?)
               ORDER BY id DESC LIMIT ?""",
            (user1, user2, user2, user1, limit)
        ).fetchall()

    return [
        {
            "type": "private",
            "from": row["sender"],
            "to": row["recipient"],
            "message": row["message"],
            "timestamp": row["timestamp"],
        }
        for row in reversed(rows)
    ]


class ChatManager:
    def __init__(self):
        self.rooms: dict[str, set[WebSocket]] = {}
        self.user_connections: dict[str, set[WebSocket]] = {}
        self.socket_users: dict[WebSocket, tuple[str, str]] = {}

    async def connect(self, room: str, username: str, ws: WebSocket):
        await ws.accept()
        self.rooms.setdefault(room, set()).add(ws)
        self.user_connections.setdefault(username, set()).add(ws)
        self.socket_users[ws] = (room, username)

    def disconnect(self, ws: WebSocket):
        info = self.socket_users.pop(ws, None)
        if not info:
            return None

        room, username = info
        self.rooms.get(room, set()).discard(ws)

        if not self.rooms.get(room):
            self.rooms.pop(room, None)

        self.user_connections.get(username, set()).discard(ws)

        if not self.user_connections.get(username):
            self.user_connections.pop(username, None)

        return room, username

    async def send_user(self, username: str, data: dict):
        for ws in list(self.user_connections.get(username, set())):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)

    async def broadcast(self, room: str, data: dict):
        for ws in list(self.rooms.get(room, set())):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)

    def online_users(self, room: str) -> list[str]:
        return sorted({
            self.socket_users[ws][1]
            for ws in self.rooms.get(room, set())
            if ws in self.socket_users
        }, key=str.lower)


manager = ChatManager()


@app.websocket("/ws/{room}")
async def chat_socket(ws: WebSocket, room: str):
    token = ws.query_params.get("token", "")
    username = authenticated_user(token)
    room = room.strip()

    if not username or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", room):
        await ws.close(code=1008)
        return

    await manager.connect(room, username, ws)

    await ws.send_json({
        "type": "history",
        "messages": message_history(room)
    })

    await manager.broadcast(room, {
        "type": "presence",
        "users": manager.online_users(room)
    })

    await manager.broadcast(room, {
        "type": "system",
        "message": f"{username} joined {room}."
    })

    try:
        while True:
            data = await ws.receive_json()

            if not isinstance(data, dict):
                continue

            action = data.get("action", "message")

            if action == "typing":
                await manager.broadcast(room, {
                    "type": "typing",
                    "username": username
                })
                continue

            if action == "private_history":
                recipient = str(data.get("to", "")).strip()

                if not recipient or recipient.lower() == username.lower():
                    continue

                with get_db() as conn:
                    user_exists = conn.execute(
                        "SELECT username FROM users WHERE username = ?",
                        (recipient,)
                    ).fetchone()

                if not user_exists:
                    await ws.send_json({
                        "type": "error",
                        "message": "That user does not exist."
                    })
                    continue

                await ws.send_json({
                    "type": "private_history",
                    "with": user_exists["username"],
                    "messages": private_history(
                        username, user_exists["username"]
                    )
                })
                continue

            if action == "private":
                recipient = str(data.get("to", "")).strip()
                message = str(data.get("message", "")).strip()

                if not message or len(message) > 1000:
                    continue

                if not recipient or recipient.lower() == username.lower():
                    continue

                with get_db() as conn:
                    row = conn.execute(
                        "SELECT username FROM users WHERE username = ?",
                        (recipient,)
                    ).fetchone()

                if not row:
                    await ws.send_json({
                        "type": "error",
                        "message": "Recipient account was not found."
                    })
                    continue

                recipient = row["username"]
                timestamp = now_iso()

                # Save once, before delivering to either user.
                save_private_message(
                    username, recipient, message, timestamp
                )

                payload = {
                    "type": "private",
                    "from": username,
                    "to": recipient,
                    "message": message,
                    "timestamp": timestamp
                }

                await manager.send_user(username, payload)

                if recipient.lower() != username.lower():
                    await manager.send_user(recipient, payload)

                continue

            if action == "message":
                message = str(data.get("message", "")).strip()

                if not message or len(message) > 1000:
                    continue

                timestamp = now_iso()
                save_message(username, room, message, timestamp)

                await manager.broadcast(room, {
                    "type": "message",
                    "username": username,
                    "room": room,
                    "message": message,
                    "timestamp": timestamp
                })

    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        info = manager.disconnect(ws)

        if info:
            old_room, old_username = info

            await manager.broadcast(old_room, {
                "type": "system",
                "message": f"{old_username} left {old_room}."
            })

            await manager.broadcast(old_room, {
                "type": "presence",
                "users": manager.online_users(old_room)
            })
