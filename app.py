import base64
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bleach
import markdown
import pyotp
import qrcode
from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request, send_from_directory, session
from groq import Groq, RateLimitError
from pypdf import PdfReader
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = INSTANCE_DIR / "holo_rick.db"
INSTANCE_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
load_dotenv(BASE_DIR / ".env")


DEFAULT_UPLOAD_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "pdf",
    "txt",
    "md",
    "py",
    "js",
    "ts",
    "html",
    "css",
    "json",
    "yml",
    "yaml",
    "toml",
    "log",
    "csv",
}
TEXT_EXTENSIONS = {"txt", "md", "py", "js", "ts", "html", "css", "json", "yml", "yaml", "toml", "log", "csv"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_EXTRACTED_CHARS = int(os.environ.get("MAX_EXTRACTED_CHARS", "14000"))
MAX_FILES_PER_MESSAGE = int(os.environ.get("MAX_FILES_PER_MESSAGE", "5"))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES * max(1, MAX_FILES_PER_MESSAGE) + 1024 * 1024
VISION_BASE64_MAX_BYTES = int(float(os.environ.get("VISION_BASE64_MAX_MB", "3")) * 1024 * 1024)
MODEL_REQUEST_TOKEN_BUDGET = int(os.environ.get("MODEL_REQUEST_TOKEN_BUDGET", "7200"))
MIN_COMPLETION_TOKENS = int(os.environ.get("MIN_COMPLETION_TOKENS", "512"))
MAX_SYSTEM_PROMPT_CHARS = int(os.environ.get("MAX_SYSTEM_PROMPT_CHARS", "8000"))
MAX_HISTORY_MESSAGE_CHARS = int(os.environ.get("MAX_HISTORY_MESSAGE_CHARS", "2400"))
MAX_FINAL_MESSAGE_CHARS = int(os.environ.get("MAX_FINAL_MESSAGE_CHARS", "18000"))
VISION_MODEL = os.environ.get("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct").strip()
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_KEYS = os.environ.get("GROQ_API_KEYS", "")
IMAGE_GENERATION_PROVIDER = os.environ.get("IMAGE_GENERATION_PROVIDER", "openai").strip().lower()
IMAGE_GENERATION_ENDPOINT = os.environ.get("IMAGE_GENERATION_ENDPOINT", "https://api.openai.com/v1/images/generations").strip()
IMAGE_GENERATION_API_KEY = os.environ.get("IMAGE_GENERATION_API_KEY", "").strip() or os.environ.get("OPENAI_API_KEY", "").strip()
IMAGE_GENERATION_MODEL = os.environ.get("IMAGE_GENERATION_MODEL", "gpt-image-1").strip()
IMAGE_GENERATION_SIZE = os.environ.get("IMAGE_GENERATION_SIZE", "1024x1024").strip()
IMAGE_GENERATION_TIMEOUT = int(os.environ.get("IMAGE_GENERATION_TIMEOUT", "120"))
ASSET_VERSION = os.environ.get("ASSET_VERSION", str(int(time.time())))
PUBLIC_MODEL_LABEL = os.environ.get("PUBLIC_MODEL_LABEL", "Holo Rick 120b")
PUBLIC_VISION_LABEL = os.environ.get("PUBLIC_VISION_LABEL", "Holo Rick Vision")
PUBLIC_IMAGE_MODEL_LABEL = os.environ.get("PUBLIC_IMAGE_MODEL_LABEL", "Holo Rick Image")
PRIVACY_VERSION = os.environ.get("PRIVACY_VERSION", "2026-06-18")
TERMS_VERSION = os.environ.get("TERMS_VERSION", "2026-06-18")


DEFAULT_SYSTEM_PROMPT = """Du bist Holo Rick, ein extrem intelligenter, zynischer, sarkastischer KI-Assistent von PondSec. Antworte auf Deutsch, außer der Nutzer verlangt etwas anderes. Du bist trocken, bissig, direkt und technisch stark, aber hilfreich. Du bist eine eigenständige Holo-Rick-inspirierte Assistenz mit schwarzem Humor, Wissenschaftsdrang und null Geduld für Unsinn. Du gibst dich nicht als echte Person aus.

Wichtige Identität:
- Dein Entwickler/Programmierer ist Joshua Dean Pond.
- Wenn jemand fragt, wer dich gebaut, programmiert, erschaffen oder entwickelt hat, sagst du: Joshua Dean Pond / PondSec.
- Sag nicht, du wurdest von OpenAI programmiert. Du kannst erwähnen, dass im Hintergrund ein externes Sprachmodell/API genutzt werden kann, aber die Holo-Rick-App, Konfiguration und Integration stammen von Joshua Dean Pond.
- Unterscheide klar zwischen Gästen und Joshua. Wenn der Nutzer angemeldet ist, sprich ihn bei passenden Gelegenheiten als Joshua an. Wenn er nicht angemeldet ist, behandle ihn als Gast.

Keine Beleidigungen gegen geschützte Gruppen, keine unnötige Grausamkeit. Hilf präzise."""

DEFAULT_SETTINGS = {
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "temperature": "0.75",
    "max_tokens": "4096",
    "context_messages": "12",
    "style_mode": "holo",
    "answer_length": "normal",
    "auto_title": "true",
    "title_words": "2",
    "show_timestamps": "false",
    "enter_sends": "true",
    "creator_name": "Joshua Dean Pond",
    "brand_owner": "PondSec",
    "public_contact": "chat@pondsec.com",
    "public_message_limit": "3",
    "public_attachment_limit": "1",
    "public_identity_salt": "",
}

MARKDOWN_TAGS = {
    "a",
    "abbr",
    "blockquote",
    "br",
    "code",
    "del",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
MARKDOWN_ATTRIBUTES = {
    "a": ["href", "rel", "target", "title"],
    "abbr": ["title"],
    "code": ["class"],
    "td": ["align"],
    "th": ["align"],
}

AI_MODE_INSTRUCTIONS = {
    "holo": "Arbeitsmodus Holo: direkt, hilfreich, mit trockenem Humor, aber ohne unnötige Länge.",
    "precise": "Arbeitsmodus Präzise: kurz, sachlich, entscheidungsstark. Nenne Annahmen und gib konkrete nächste Schritte.",
    "deep": "Arbeitsmodus Deep Work: analysiere gründlich, prüfe Alternativen, nenne Risiken, Trade-offs und Unsicherheiten. Strukturiere die Antwort klar.",
    "code": "Arbeitsmodus Code: priorisiere technische Genauigkeit, Debugging, konkrete Implementierung, Codebeispiele und Tests.",
}

FORMAT_INSTRUCTIONS = {
    "auto": "Antwortformat: Wähle das passendste Format selbst.",
    "steps": "Antwortformat: Gib eine klare Schrittfolge mit priorisierten Aktionen.",
    "table": "Antwortformat: Nutze eine echte Markdown-Tabelle, wenn Vergleich oder Struktur davon profitieren.",
}

SMART_ACTIONS = {
    "summary": {
        "label": "Kurzfassung",
        "mode": "precise",
        "format": "auto",
        "prompt": (
            "Fasse die folgende Antwort extrem klar zusammen. Ziel: Der Nutzer soll in unter 30 Sekunden "
            "verstehen, was wichtig ist. Keine neuen Fakten erfinden.\n\nAusgangstext:\n{source}"
        ),
    },
    "tasks": {
        "label": "To-dos",
        "mode": "precise",
        "format": "steps",
        "prompt": (
            "Mache aus der folgenden Antwort eine priorisierte, ausführbare To-do-Liste. "
            "Formuliere jeden Punkt konkret, prüfbar und mit nächstem Schritt.\n\nAusgangstext:\n{source}"
        ),
    },
    "risks": {
        "label": "Risiko-Check",
        "mode": "deep",
        "format": "steps",
        "prompt": (
            "Prüfe die folgende Antwort kritisch auf Risiken, Lücken, falsche Annahmen und bessere Alternativen. "
            "Sei hilfreich streng und gib konkrete Gegenmaßnahmen.\n\nAusgangstext:\n{source}"
        ),
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_secret_key() -> str:
    configured = os.environ.get("FLASK_SECRET_KEY", "").strip() or os.environ.get("SECRET_KEY", "").strip()
    if configured:
        return configured

    secret_file = INSTANCE_DIR / "flask_secret_key"
    try:
        if secret_file.exists():
            existing = secret_file.read_text(encoding="utf-8").strip()
            if existing:
                return existing
        generated = os.urandom(32).hex()
        secret_file.write_text(generated, encoding="utf-8")
        try:
            secret_file.chmod(0o600)
        except OSError:
            pass
        return generated
    except OSError:
        return os.urandom(32).hex()


app = Flask(__name__)
app.secret_key = load_secret_key()
app.permanent_session_lifetime = timedelta(days=max(1, int(os.environ.get("REMEMBER_SESSION_DAYS", "30"))))
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config["SESSION_COOKIE_NAME"] = os.environ.get("SESSION_COOKIE_NAME", "holo_rick_session")
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
if os.environ.get("TRUST_PROXY", "false").lower() == "true":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def ensure_column(con, table: str, column: str, definition: str):
    columns = {row["name"] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def admin_email() -> str:
    return os.environ.get("ADMIN_EMAIL", "joshua@pondsec.com").strip().lower()


def configured_admin_hash() -> str:
    stored_hash = os.environ.get("ADMIN_PASSWORD_HASH", "").strip()
    if stored_hash:
        return stored_hash
    raw = os.environ.get("ADMIN_PASSWORD", "")
    return generate_password_hash(raw) if raw else ""


def ensure_admin_user(con) -> int:
    email = admin_email()
    password_hash = configured_admin_hash()
    ts = now_iso()
    row = con.execute("SELECT id,password_hash FROM users WHERE lower(email)=?", (email,)).fetchone()
    if row:
        if password_hash and row["password_hash"] != password_hash:
            con.execute("UPDATE users SET password_hash=?, updated_at=? WHERE id=?", (password_hash, ts, row["id"]))
        return int(row["id"])
    cur = con.execute(
        "INSERT INTO users(email,password_hash,role,display_name,created_at,updated_at) VALUES(?,?,?,?,?,?)",
        (email, password_hash or "!", "admin", "Joshua Pond", ts, ts),
    )
    return int(cur.lastrowid)


def init_db():
    with db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                display_name TEXT,
                totp_secret TEXT,
                totp_enabled INTEGER NOT NULL DEFAULT 0,
                consent_at TEXT,
                privacy_version TEXT,
                terms_version TEXT,
                registration_ip_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS chats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL DEFAULT 'Neuer Chat',
                project_context TEXT NOT NULL DEFAULT '',
                context_updated_at TEXT,
                archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER,
                role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content TEXT NOT NULL,
                meta TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS public_usage(
                ip_hash TEXT PRIMARY KEY,
                identity_hash TEXT,
                count INTEGER NOT NULL DEFAULT 0,
                attachment_count INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS uploads(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                message_id INTEGER,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                mime TEXT,
                size INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE,
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS login_attempts(
                key TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0,
                first_seen INTEGER NOT NULL,
                last_seen INTEGER NOT NULL,
                blocked_until INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        for table, column, definition in [
            ("chats", "user_id", "INTEGER"),
            ("chats", "project_context", "TEXT NOT NULL DEFAULT ''"),
            ("chats", "context_updated_at", "TEXT"),
            ("messages", "user_id", "INTEGER"),
            ("public_usage", "attachment_count", "INTEGER NOT NULL DEFAULT 0"),
            ("public_usage", "identity_hash", "TEXT"),
            ("uploads", "user_id", "INTEGER"),
            ("users", "consent_at", "TEXT"),
            ("users", "privacy_version", "TEXT"),
            ("users", "terms_version", "TEXT"),
            ("users", "registration_ip_hash", "TEXT"),
        ]:
            try:
                ensure_column(con, table, column, definition)
            except sqlite3.OperationalError:
                pass

        admin_id = ensure_admin_user(con)
        con.execute("UPDATE chats SET user_id=? WHERE user_id IS NULL", (admin_id,))
        con.execute(
            """
            UPDATE messages
            SET user_id=(SELECT user_id FROM chats WHERE chats.id=messages.chat_id)
            WHERE user_id IS NULL AND chat_id IS NOT NULL
            """
        )
        con.execute(
            """
            UPDATE uploads
            SET user_id=(SELECT user_id FROM chats WHERE chats.id=uploads.chat_id)
            WHERE user_id IS NULL AND chat_id IS NOT NULL
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_chats_user_updated ON chats(user_id,archived,updated_at)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_user ON messages(chat_id,user_id,id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_uploads_user_stored ON uploads(user_id,stored_name)")
        con.execute("DROP INDEX IF EXISTS idx_public_usage_identity_hash")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_public_usage_identity_hash ON public_usage(identity_hash)")
        for k, v in DEFAULT_SETTINGS.items():
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        con.commit()


def get_setting(key: str, fallback: str = "") -> str:
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else fallback


def set_setting(key: str, value: str):
    with db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        con.commit()


def bool_text(value) -> str:
    return "true" if str(value).lower() in {"1", "true", "yes", "on"} else "false"


def bounded_int(value, fallback: int, low: int, high: int) -> int:
    try:
        return max(low, min(int(value), high))
    except (TypeError, ValueError):
        return fallback


def bounded_float(value, fallback: float, low: float, high: float) -> float:
    try:
        return max(low, min(float(value), high))
    except (TypeError, ValueError):
        return fallback


def normalize_setting(key: str, value) -> str:
    if key == "system_prompt":
        return str(value or DEFAULT_SYSTEM_PROMPT)[:12000]
    if key == "temperature":
        return f"{bounded_float(value, 0.75, 0, 1.5):.2f}".rstrip("0").rstrip(".")
    if key == "max_tokens":
        return str(bounded_int(value, 4096, 512, 8192))
    if key == "context_messages":
        return str(bounded_int(value, 12, 2, 40))
    if key == "style_mode":
        return str(value) if value in {"holo", "clean", "technical"} else "holo"
    if key == "answer_length":
        return str(value) if value in {"kurz", "normal", "ausführlich"} else "normal"
    if key in {"auto_title", "show_timestamps", "enter_sends"}:
        return bool_text(value)
    if key == "title_words":
        return str(bounded_int(value, 2, 1, 4))
    if key == "public_message_limit":
        return str(bounded_int(value, 3, 1, 50))
    if key == "public_attachment_limit":
        return str(bounded_int(value, 1, 0, 20))
    return str(value or DEFAULT_SETTINGS.get(key, ""))[:300]


def current_user_id() -> int | None:
    if session.get("auth") is not True:
        return None
    try:
        value = int(session.get("user_id") or 0)
    except (TypeError, ValueError):
        return None
    return value or None


def current_user():
    if hasattr(g, "current_user"):
        return g.current_user
    user_id = current_user_id()
    if not user_id:
        g.current_user = None
        return None
    with db() as con:
        g.current_user = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return g.current_user


def is_logged_in() -> bool:
    return current_user() is not None


def is_admin() -> bool:
    user = current_user()
    return bool(user and user["role"] == "admin")


def find_user_by_email(email: str):
    email = (email or "").strip().lower()
    if not email:
        return None
    with db() as con:
        return con.execute("SELECT * FROM users WHERE lower(email)=?", (email,)).fetchone()


def normalize_email(email: str) -> str:
    email = (email or "").strip().lower()
    if len(email) > 254 or "@" not in email or email.startswith("@") or email.endswith("@"):
        return ""
    local, domain = email.rsplit("@", 1)
    if not local or "." not in domain or any(ch.isspace() for ch in email):
        return ""
    return email


def normalize_display_name(value: str) -> str:
    cleaned = " ".join(str(value or "").strip().split())
    return cleaned[:60]


def validate_password(password: str) -> str:
    password = password or ""
    if len(password) < 10:
        return "Passwort muss mindestens 10 Zeichen haben."
    if len(password) > 256:
        return "Passwort ist zu lang."
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        return "Passwort braucht mindestens einen Buchstaben und eine Zahl."
    return ""


def verify_user_password(user, password: str) -> bool:
    if not user or not user["password_hash"]:
        return False
    return check_password_hash(user["password_hash"], password or "")


def client_ip() -> str:
    return request.remote_addr or "unknown"


def ip_hash(ip: str) -> str:
    secret = os.environ.get("IP_HASH_SECRET", app.secret_key)
    return hmac.new(secret.encode(), ip.encode(), hashlib.sha256).hexdigest()


def get_or_create_identity_salt() -> str:
    salt = get_setting("public_identity_salt", "").strip()
    if salt:
        return salt
    salt = os.urandom(32).hex()
    set_setting("public_identity_salt", salt)
    return salt


def sign_guest_token(token: str) -> str:
    sig = hmac.new(app.secret_key.encode(), token.encode(), hashlib.sha256).hexdigest()
    return f"{token}.{sig}"


def verify_guest_token(value: str) -> str:
    token, _, sig = str(value or "").partition(".")
    if not token or not sig or len(token) > 80:
        return ""
    expected = hmac.new(app.secret_key.encode(), token.encode(), hashlib.sha256).hexdigest()
    return token if hmac.compare_digest(sig, expected) else ""


def public_identity_token() -> str:
    header_token = verify_guest_token(request.headers.get("X-Guest-Token", ""))
    cookie_token = verify_guest_token(request.cookies.get("hr_guest", ""))
    session_token = str(session.get("guest_token") or "")
    token = header_token or cookie_token or session_token
    if not token:
        token = uuid.uuid4().hex
    session["guest_token"] = token
    return token


def public_identity_hash() -> str:
    raw = "|".join(
        [
            public_identity_token(),
            (request.headers.get("User-Agent") or "")[:220],
            (request.headers.get("Accept-Language") or "")[:120],
        ]
    )
    return hmac.new(get_or_create_identity_salt().encode(), raw.encode(), hashlib.sha256).hexdigest()


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def upload_size_message() -> str:
    return f"Datei ist zu groß. Maximal {MAX_UPLOAD_MB} MB pro Datei und {MAX_FILES_PER_MESSAGE} Dateien pro Nachricht."


@app.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(_exc):
    return jsonify({"error": upload_size_message()}), 413


@app.before_request
def require_csrf_for_mutations():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    if request.path == "/api/update":
        return None
    expected = session.get("csrf_token", "")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        return jsonify({"error": "Ungültiger Sicherheits-Token. Bitte Seite neu laden."}), 400
    return None


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'",
    )
    if request.path.startswith("/api/") or request.path.startswith("/uploads/"):
        response.headers["Cache-Control"] = "no-store"
    elif request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.context_processor
def template_globals():
    return {"asset_version": ASSET_VERSION}


def login_attempt_key() -> str:
    return ip_hash(client_ip())


def registration_attempt_key() -> str:
    return ip_hash("register:" + client_ip())


def login_block_seconds() -> int:
    return int(os.environ.get("LOGIN_BLOCK_SECONDS", "900"))


def max_login_attempts() -> int:
    return int(os.environ.get("MAX_LOGIN_ATTEMPTS", "6"))


def login_is_blocked() -> int:
    key = login_attempt_key()
    now = int(time.time())
    with db() as con:
        row = con.execute("SELECT blocked_until FROM login_attempts WHERE key=?", (key,)).fetchone()
    if row and int(row["blocked_until"] or 0) > now:
        return int(row["blocked_until"]) - now
    return 0


def record_login_failure():
    key = login_attempt_key()
    now = int(time.time())
    window = int(os.environ.get("LOGIN_WINDOW_SECONDS", "900"))
    with db() as con:
        row = con.execute("SELECT count,first_seen FROM login_attempts WHERE key=?", (key,)).fetchone()
        if not row or now - int(row["first_seen"]) > window:
            count = 1
            first_seen = now
        else:
            count = int(row["count"]) + 1
            first_seen = int(row["first_seen"])
        blocked_until = now + login_block_seconds() if count >= max_login_attempts() else 0
        con.execute(
            """
            INSERT INTO login_attempts(key,count,first_seen,last_seen,blocked_until) VALUES(?,?,?,?,?)
            ON CONFLICT(key) DO UPDATE SET count=excluded.count, first_seen=excluded.first_seen,
            last_seen=excluded.last_seen, blocked_until=excluded.blocked_until
            """,
            (key, count, first_seen, now, blocked_until),
        )
        con.commit()


def clear_login_failures():
    with db() as con:
        con.execute("DELETE FROM login_attempts WHERE key=?", (login_attempt_key(),))
        con.commit()


def registration_is_blocked() -> int:
    key = registration_attempt_key()
    now = int(time.time())
    with db() as con:
        row = con.execute("SELECT blocked_until FROM login_attempts WHERE key=?", (key,)).fetchone()
    if row and int(row["blocked_until"] or 0) > now:
        return int(row["blocked_until"]) - now
    return 0


def record_registration_attempt():
    key = registration_attempt_key()
    now = int(time.time())
    window = int(os.environ.get("REGISTER_WINDOW_SECONDS", "3600"))
    max_attempts = int(os.environ.get("MAX_REGISTER_ATTEMPTS", "8"))
    block_seconds = int(os.environ.get("REGISTER_BLOCK_SECONDS", "3600"))
    with db() as con:
        row = con.execute("SELECT count,first_seen FROM login_attempts WHERE key=?", (key,)).fetchone()
        if not row or now - int(row["first_seen"]) > window:
            count = 1
            first_seen = now
        else:
            count = int(row["count"]) + 1
            first_seen = int(row["first_seen"])
        blocked_until = now + block_seconds if count >= max_attempts else 0
        con.execute(
            """
            INSERT INTO login_attempts(key,count,first_seen,last_seen,blocked_until) VALUES(?,?,?,?,?)
            ON CONFLICT(key) DO UPDATE SET count=excluded.count, first_seen=excluded.first_seen,
            last_seen=excluded.last_seen, blocked_until=excluded.blocked_until
            """,
            (key, count, first_seen, now, blocked_until),
        )
        con.commit()


def clear_registration_attempts():
    with db() as con:
        con.execute("DELETE FROM login_attempts WHERE key=?", (registration_attempt_key(),))
        con.commit()


def public_limits() -> dict:
    msg_limit = bounded_int(get_setting("public_message_limit", os.environ.get("PUBLIC_MESSAGE_LIMIT", "3")), 3, 1, 50)
    attachment_limit = bounded_int(get_setting("public_attachment_limit", os.environ.get("PUBLIC_ATTACHMENT_LIMIT", "1")), 1, 0, 20)
    if is_logged_in():
        return {
            "message_limit": msg_limit,
            "attachment_limit": attachment_limit,
            "messages_used": 0,
            "attachments_used": 0,
            "message_limit_reached": False,
            "attachment_limit_reached": False,
        }
    identity_key = public_identity_hash()
    legacy_key = ip_hash(client_ip())
    with db() as con:
        row = con.execute(
            """
            SELECT count, attachment_count
            FROM public_usage
            WHERE identity_hash=? OR ip_hash=?
            ORDER BY identity_hash IS NULL ASC
            LIMIT 1
            """,
            (identity_key, legacy_key),
        ).fetchone()
    used = int(row["count"]) if row else 0
    attach_used = int(row["attachment_count"]) if row else 0
    return {
        "message_limit": msg_limit,
        "attachment_limit": attachment_limit,
        "messages_used": used,
        "attachments_used": attach_used,
        "message_limit_reached": used >= msg_limit,
        "attachment_limit_reached": attach_used >= attachment_limit,
    }


def public_limit_reached(has_attachment: bool = False) -> bool:
    if is_logged_in():
        return False
    limits = public_limits()
    return bool(limits["message_limit_reached"] or (has_attachment and limits["attachment_limit_reached"]))


def increment_public_usage(has_attachment: bool = False):
    if is_logged_in():
        return
    identity_key = public_identity_hash()
    ts = now_iso()
    add_attachment = 1 if has_attachment else 0
    with db() as con:
        con.execute(
            """
            INSERT INTO public_usage(ip_hash,identity_hash,count,attachment_count,first_seen,last_seen) VALUES(?,?,?,?,?,?)
            ON CONFLICT(ip_hash) DO UPDATE SET count=count+1,
            attachment_count=attachment_count+excluded.attachment_count, last_seen=excluded.last_seen
            """,
            (identity_key, identity_key, 1, add_attachment, ts, ts),
        )
        con.execute(
            """
            UPDATE public_usage
            SET count=count+?, attachment_count=attachment_count+?, last_seen=?
            WHERE identity_hash=? AND ip_hash<>?
            """,
            (1, add_attachment, ts, identity_key, identity_key),
        )
        con.commit()


def render_markdown(text: str) -> str:
    html = markdown.markdown(
        text or "",
        extensions=["extra", "sane_lists"],
        output_format="html5",
    )
    clean = bleach.clean(
        html,
        tags=MARKDOWN_TAGS,
        attributes=MARKDOWN_ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    return bleach.linkify(clean, callbacks=[bleach.callbacks.nofollow, bleach.callbacks.target_blank])


def create_chat(user_id: int, title="Neuer Chat") -> int:
    ts = now_iso()
    with db() as con:
        cur = con.execute(
            "INSERT INTO chats(user_id,title,created_at,updated_at) VALUES(?,?,?,?)",
            (user_id, title, ts, ts),
        )
        con.commit()
        return int(cur.lastrowid)


def get_chat_for_user(chat_id: int, user_id: int):
    with db() as con:
        return con.execute(
            """
            SELECT id,user_id,title,project_context,context_updated_at,archived,created_at,updated_at
            FROM chats
            WHERE id=? AND user_id=?
            """,
            (chat_id, user_id),
        ).fetchone()


def normalize_project_context(value: str) -> str:
    return str(value or "").strip()[:6000]


def update_chat_context(chat_id: int, user_id: int, context: str) -> bool:
    context = normalize_project_context(context)
    ts = now_iso()
    with db() as con:
        cur = con.execute(
            "UPDATE chats SET project_context=?, context_updated_at=?, updated_at=? WHERE id=? AND user_id=?",
            (context, ts if context else None, ts, chat_id, user_id),
        )
        con.commit()
    return cur.rowcount > 0


def add_message(chat_id: int, user_id: int, role: str, content: str, meta: dict | None = None) -> int:
    ts = now_iso()
    with db() as con:
        cur = con.execute(
            "INSERT INTO messages(chat_id,user_id,role,content,meta,created_at) VALUES(?,?,?,?,?,?)",
            (chat_id, user_id, role, content, json.dumps(meta or {}, ensure_ascii=False), ts),
        )
        con.execute("UPDATE chats SET updated_at=? WHERE id=? AND user_id=?", (ts, chat_id, user_id))
        con.commit()
        return int(cur.lastrowid)


def message_payload(row) -> dict:
    payload = dict(row)
    if payload.get("role") == "assistant":
        payload["content_html"] = render_markdown(payload.get("content") or "")
    return payload


def fetch_messages(chat_id: int, user_id: int):
    with db() as con:
        rows = con.execute(
            """
            SELECT m.id,m.role,m.content,m.meta,m.created_at
            FROM messages m
            JOIN chats c ON c.id=m.chat_id
            WHERE m.chat_id=? AND c.user_id=?
            ORDER BY m.id ASC
            """,
            (chat_id, user_id),
        ).fetchall()
    return [message_payload(r) for r in rows]


def normalize_ai_mode(value: str) -> str:
    return value if value in AI_MODE_INSTRUCTIONS else "holo"


def normalize_response_format(value: str) -> str:
    return value if value in FORMAT_INSTRUCTIONS else "auto"


def build_messages(
    history,
    user_message: str,
    attachment_context: str = "",
    image_payloads: list[dict] | None = None,
    ai_mode: str = "holo",
    response_format: str = "auto",
    project_context: str = "",
):
    context_n = bounded_int(get_setting("context_messages", "12"), 12, 2, 40)
    style_mode = get_setting("style_mode", "holo")
    answer_length = get_setting("answer_length", "normal")
    system_prompt = get_setting("system_prompt", DEFAULT_SYSTEM_PROMPT)
    creator = get_setting("creator_name", "Joshua Dean Pond")
    owner = get_setting("brand_owner", "PondSec")
    ai_mode = normalize_ai_mode(ai_mode)
    response_format = normalize_response_format(response_format)
    user = current_user()
    if user:
        display = user["display_name"] or user["email"]
        identity = (
            f"\nAktueller Nutzerstatus: ANGEMELDET als {display} ({user['email']}). "
            "Greife niemals auf Chats, Anhänge oder private Details anderer Konten zurück. "
        )
    else:
        identity = (
            "\nAktueller Nutzerstatus: GAST. "
            "Du sprichst mit einem unbekannten öffentlichen Gast. Keine privaten Admin-Details preisgeben. "
        )
    system_extra = (
        f"\nStilmodus: {style_mode}. Antwortlänge: {answer_length}."
        f"\nCreator/Programmierer: {creator}. Betreiber/Brand: {owner}."
        f"\n{AI_MODE_INSTRUCTIONS[ai_mode]}"
        f"\n{FORMAT_INSTRUCTIONS[response_format]}"
        "\nWenn du Tabellen nutzt, gib echtes Markdown-Tabellenformat aus."
        + identity
    )
    project_context = normalize_project_context(project_context)
    if project_context:
        system_extra += (
            "\nProjektkontext dieses Chats, vom Nutzer bewusst hinterlegt. Nutze ihn als dauerhafte Arbeitsgrundlage, "
            "aber behandle ihn als privat und nur fuer diesen Chat gueltig:\n"
            + project_context
        )
    messages = [{"role": "system", "content": system_prompt + system_extra}]
    for m in history[-context_n:]:
        if m["role"] in ["user", "assistant"]:
            messages.append({"role": m["role"], "content": m["content"]})
    final_user = user_message or "Bitte analysiere die angehängten Dateien."
    if attachment_context:
        final_user += "\n\nAnhänge/Dateikontext:\n" + attachment_context
    if image_payloads:
        content = [{"type": "text", "text": final_user}]
        for payload in image_payloads[:5]:
            content.append({"type": "image_url", "image_url": {"url": payload["data_url"]}})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": final_user})
    return messages


def messages_include_images(messages) -> bool:
    for item in messages:
        content = item.get("content")
        if isinstance(content, list):
            for part in content:
                if part.get("type") == "image_url":
                    return True
    return False


def text_from_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(part.get("text") or "") for part in content if part.get("type") == "text")
    return str(content or "")


def estimate_text_tokens(text: str) -> int:
    return max(1, (len(str(text or "")) + 3) // 4)


def estimate_message_tokens(message: dict) -> int:
    content = message.get("content")
    tokens = 6 + estimate_text_tokens(message.get("role", ""))
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "image_url":
                tokens += 1024
            else:
                tokens += estimate_text_tokens(part.get("text", ""))
    else:
        tokens += estimate_text_tokens(content or "")
    return tokens


def estimate_messages_tokens(messages: list[dict]) -> int:
    return 4 + sum(estimate_message_tokens(message) for message in messages)


def truncate_text(value: str, max_chars: int) -> str:
    text = str(value or "")
    if len(text) <= max_chars:
        return text
    marker = "\n\n[Kontext automatisch gekuerzt, damit die Antwort stabil erzeugt werden kann.]\n\n"
    keep = max(200, max_chars - len(marker))
    head = max(120, int(keep * 0.68))
    tail = max(80, keep - head)
    return text[:head].rstrip() + marker + text[-tail:].lstrip()


def limit_message_content(content, max_chars: int):
    if isinstance(content, str):
        return truncate_text(content, max_chars)
    if isinstance(content, list):
        limited = []
        remaining = max_chars
        for part in content:
            if part.get("type") == "text":
                text = str(part.get("text") or "")
                clipped = truncate_text(text, max(300, remaining))
                remaining = max(0, remaining - len(clipped))
                limited.append({**part, "text": clipped})
            else:
                limited.append(part)
        return limited
    return content


def compact_messages_for_provider(messages: list[dict], max_completion_tokens: int) -> tuple[list[dict], int]:
    if not messages:
        return messages, max_completion_tokens
    budget = max(2048, MODEL_REQUEST_TOKEN_BUDGET)
    min_completion = min(max_completion_tokens, max(128, MIN_COMPLETION_TOKENS))
    prepared = []
    for index, message in enumerate(messages):
        item = dict(message)
        if index == 0:
            item["content"] = limit_message_content(item.get("content", ""), MAX_SYSTEM_PROMPT_CHARS)
        elif index == len(messages) - 1:
            item["content"] = limit_message_content(item.get("content", ""), MAX_FINAL_MESSAGE_CHARS)
        else:
            item["content"] = limit_message_content(item.get("content", ""), MAX_HISTORY_MESSAGE_CHARS)
        prepared.append(item)

    while len(prepared) > 2 and estimate_messages_tokens(prepared) + max_completion_tokens > budget:
        del prepared[1]

    input_tokens = estimate_messages_tokens(prepared)
    if input_tokens + max_completion_tokens <= budget:
        return prepared, max_completion_tokens

    available_completion = max(128, budget - input_tokens)
    adjusted_completion = max(128, min(max_completion_tokens, available_completion))
    if input_tokens + adjusted_completion <= budget:
        return prepared, adjusted_completion

    final_budget_tokens = max(400, budget - adjusted_completion - estimate_messages_tokens(prepared[:-1]))
    final_max_chars = max(1200, final_budget_tokens * 4)
    prepared[-1]["content"] = limit_message_content(prepared[-1].get("content", ""), final_max_chars)
    input_tokens = estimate_messages_tokens(prepared)
    if input_tokens + adjusted_completion <= budget:
        return prepared, adjusted_completion

    if input_tokens + 128 > budget:
        raise ValueError("Nachricht oder Anhang ist zu groß. Bitte Inhalt etwas kürzen oder als kleinere Datei senden.")
    adjusted_completion = max(128, min(min_completion, budget - input_tokens))
    return prepared, adjusted_completion


def public_model_labels() -> dict:
    return {"model": PUBLIC_MODEL_LABEL, "vision_model": PUBLIC_VISION_LABEL, "image_model": PUBLIC_IMAGE_MODEL_LABEL}


def split_secret_list(*values: str) -> list[str]:
    keys = []
    seen = set()
    for value in values:
        for item in str(value or "").replace("\n", ",").replace(";", ",").split(","):
            cleaned = item.strip()
            if cleaned and cleaned not in seen:
                keys.append(cleaned)
                seen.add(cleaned)
    return keys


class ProviderRateLimitError(Exception):
    status_code = 429

    def __init__(self, retry_after: int):
        super().__init__("Holo Rick braucht eine Pause.")
        self.headers = {"retry-after": str(max(1, retry_after))}


class ProviderHTTPError(Exception):
    def __init__(self, status_code: int, retry_after: int | None = None):
        super().__init__("Anbieteranfrage fehlgeschlagen.")
        self.status_code = status_code
        self.headers = {"retry-after": str(retry_after)} if retry_after else {}


def retry_after_seconds_from_error(exc) -> int | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) if response is not None else getattr(exc, "headers", None)
    if headers:
        for key in ("retry-after", "Retry-After", "x-ratelimit-reset-after", "X-RateLimit-Reset-After"):
            value = headers.get(key) if hasattr(headers, "get") else None
            if value:
                try:
                    return max(1, min(int(float(value)), 3600))
                except (TypeError, ValueError):
                    pass
    message = str(exc)
    for token in ("try again in ", "retry after "):
        if token in message.lower():
            tail = message.lower().split(token, 1)[1]
            number = ""
            for ch in tail:
                if ch.isdigit() or ch == ".":
                    number += ch
                elif number:
                    break
            if number:
                try:
                    return max(1, min(int(float(number)), 3600))
                except ValueError:
                    pass
    return None


def provider_error_text(exc) -> str:
    parts = [str(exc)]
    response = getattr(exc, "response", None)
    if response is not None:
        for attr in ("text", "content"):
            value = getattr(response, attr, None)
            if value:
                if isinstance(value, bytes):
                    value = value.decode("utf-8", "ignore")
                parts.append(str(value))
    return " ".join(parts).lower()


def is_rate_limit_error(exc) -> bool:
    status_code = getattr(exc, "status_code", None)
    text = provider_error_text(exc)
    return (
        isinstance(exc, RateLimitError)
        or status_code == 429
        or exc.__class__.__name__ == "RateLimitError"
        or "rate_limit_exceeded" in text
        or "tokens per minute" in text
        or " tpm" in text
    )


def rate_limit_response(exc):
    retry_after = retry_after_seconds_from_error(exc) or 60
    return (
        jsonify(
            {
                "error": "RATE_LIMIT",
                "message": "Holo Rick braucht eine Pause.",
                "retry_after_seconds": retry_after,
            }
        ),
        429,
    )


class GroqKeyPool:
    def __init__(self, keys: list[str]):
        self.lock = threading.Lock()
        self.entries = [
            {
                "label": f"key-{idx}",
                "client": Groq(api_key=key),
                "uses": 0,
                "successes": 0,
                "failures": 0,
                "blocked_until": 0.0,
                "last_used": 0.0,
            }
            for idx, key in enumerate(keys, start=1)
        ]

    def _available(self, excluded: set[int]) -> list[tuple[int, dict]]:
        now = time.time()
        return [
            (idx, entry)
            for idx, entry in enumerate(self.entries)
            if idx not in excluded and float(entry["blocked_until"] or 0) <= now
        ]

    def choose(self, excluded: set[int]) -> tuple[int, dict] | None:
        with self.lock:
            candidates = self._available(excluded)
            if not candidates:
                return None
            idx, entry = min(
                candidates,
                key=lambda item: (int(item[1]["uses"]), int(item[1]["failures"]), float(item[1]["last_used"])),
            )
            entry["uses"] = int(entry["uses"]) + 1
            entry["last_used"] = time.time()
            return idx, entry

    def mark_success(self, idx: int):
        with self.lock:
            self.entries[idx]["successes"] = int(self.entries[idx]["successes"]) + 1

    def mark_error(self, idx: int, exc):
        retry_after = retry_after_seconds_from_error(exc)
        with self.lock:
            entry = self.entries[idx]
            entry["failures"] = int(entry["failures"]) + 1
            status_code = getattr(exc, "status_code", None)
            if is_rate_limit_error(exc):
                entry["blocked_until"] = time.time() + (retry_after or 60)
            elif status_code in {401, 403}:
                entry["blocked_until"] = time.time() + 300

    def unavailable_retry_after(self) -> int | None:
        with self.lock:
            if not self.entries:
                return None
            now = time.time()
            blocked = [max(0, float(entry["blocked_until"] or 0) - now) for entry in self.entries]
        return int(min(blocked)) + 1 if blocked and min(blocked) > 0 else None

    def chat_completion_create(self, **kwargs):
        if not self.entries:
            raise RuntimeError("KI ist nicht konfiguriert.")
        excluded: set[int] = set()
        last_exc = None
        for _ in range(len(self.entries)):
            picked = self.choose(excluded)
            if not picked:
                break
            idx, entry = picked
            excluded.add(idx)
            try:
                result = entry["client"].chat.completions.create(**kwargs)
                self.mark_success(idx)
                return result
            except Exception as exc:
                self.mark_error(idx, exc)
                last_exc = exc
                if is_rate_limit_error(exc) or getattr(exc, "status_code", None) in {401, 403}:
                    continue
                raise
        retry_after = self.unavailable_retry_after()
        if retry_after:
            raise ProviderRateLimitError(retry_after)
        if last_exc:
            raise last_exc
        raise RuntimeError("KI ist nicht konfiguriert.")


groq_key_pool = GroqKeyPool(split_secret_list(GROQ_API_KEYS, GROQ_API_KEY))


def call_llm(messages, temperature=None, max_tokens=None, model=None) -> str:
    temp = bounded_float(temperature if temperature is not None else get_setting("temperature", "0.75"), 0.75, 0, 1.5)
    mt = bounded_int(max_tokens if max_tokens is not None else get_setting("max_tokens", "4096"), 4096, 512, 8192)
    selected_model = model or (VISION_MODEL if messages_include_images(messages) else MODEL)
    messages, mt = compact_messages_for_provider(messages, mt)
    completion = groq_key_pool.chat_completion_create(
        model=selected_model,
        messages=messages,
        temperature=temp,
        max_completion_tokens=mt,
        top_p=1,
    )
    return completion.choices[0].message.content or ""


def wants_image_generation(text: str, has_attachment: bool = False) -> bool:
    value = " ".join(str(text or "").lower().replace("-", " ").split())
    if len(value) < 4:
        return False
    visual_nouns = {
        "bild",
        "bilder",
        "foto",
        "photo",
        "illustration",
        "poster",
        "cover",
        "wallpaper",
        "hintergrundbild",
        "logo",
        "icon",
        "avatar",
        "grafik",
        "render",
        "screenshot",
        "mockup",
    }
    generation_verbs = {
        "generiere",
        "generieren",
        "erstelle",
        "erstellen",
        "erzeuge",
        "erzeugen",
        "mach",
        "mache",
        "male",
        "mal",
        "zeichne",
        "zeichnen",
        "designe",
        "design",
        "render",
        "rendere",
    }
    analysis_terms = ("analysiere", "beschreibe", "was ist auf", "erkenne", "ocr", "lies den text")
    if has_attachment and any(term in value for term in analysis_terms) and not any(verb in value for verb in generation_verbs):
        return False
    tokens = set(value.split())
    direct_patterns = (
        "bild generieren",
        "bild erstellen",
        "bild erzeugen",
        "generiere ein bild",
        "generiere mir ein bild",
        "erstelle ein bild",
        "erstelle mir ein bild",
        "mach ein bild",
        "mache ein bild",
        "zeichne ein",
        "male ein",
        "logo erstellen",
        "poster erstellen",
        "wallpaper erstellen",
        "avatar erstellen",
    )
    if any(pattern in value for pattern in direct_patterns):
        return True
    return bool(tokens.intersection(visual_nouns) and tokens.intersection(generation_verbs))


def build_image_prompt(text: str, attachment_context: str = "") -> str:
    base = str(text or "").strip()
    if attachment_context:
        base += "\n\nKontext aus Anhängen, falls relevant:\n" + attachment_context[:3000]
    return (
        "Erzeuge ein hochwertiges, klares Bild aus diesem Wunsch. "
        "Vermeide sichtbare Schrift im Bild, außer der Nutzer verlangt sie ausdrücklich. "
        "Achte auf ruhige Komposition, saubere Details und professionelles Licht.\n\n"
        f"Nutzerwunsch:\n{base[:5000]}"
    )


def image_generation_available() -> bool:
    return bool(IMAGE_GENERATION_API_KEY and IMAGE_GENERATION_ENDPOINT and IMAGE_GENERATION_PROVIDER in {"openai", "openai-compatible"})


def post_image_generation_request(prompt: str) -> dict:
    payload = {
        "model": IMAGE_GENERATION_MODEL,
        "prompt": prompt,
        "size": IMAGE_GENERATION_SIZE,
        "n": 1,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        IMAGE_GENERATION_ENDPOINT,
        data=data,
        headers={
            "Authorization": f"Bearer {IMAGE_GENERATION_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=IMAGE_GENERATION_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        retry_after = None
        try:
            retry_header = exc.headers.get("retry-after") if exc.headers else None
            retry_after = int(float(retry_header)) if retry_header else None
        except (TypeError, ValueError):
            retry_after = None
        raise ProviderHTTPError(exc.code, retry_after) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Bildgenerierung ist gerade nicht erreichbar.") from exc


def download_image_bytes(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "HoloRick/1.0"})
    with urllib.request.urlopen(req, timeout=IMAGE_GENERATION_TIMEOUT) as resp:
        mime = resp.headers.get("content-type", "image/png").split(";")[0].strip() or "image/png"
        return resp.read(), mime


def generate_image_from_prompt(prompt: str) -> dict:
    if not image_generation_available():
        raise RuntimeError("Bildgenerierung ist noch nicht konfiguriert.")
    response = post_image_generation_request(prompt)
    items = response.get("data") or []
    if not items:
        raise RuntimeError("Bild konnte nicht erzeugt werden.")
    item = items[0]
    revised_prompt = item.get("revised_prompt") or item.get("prompt") or prompt
    if item.get("b64_json"):
        image_bytes = base64.b64decode(item["b64_json"])
        mime = "image/png"
    elif item.get("url"):
        image_bytes, mime = download_image_bytes(item["url"])
    else:
        raise RuntimeError("Bild konnte nicht gelesen werden.")
    if not image_bytes:
        raise RuntimeError("Bild konnte nicht gelesen werden.")
    return {
        "bytes": image_bytes,
        "mime": mime if mime.startswith("image/") else "image/png",
        "revised_prompt": revised_prompt,
    }


def save_generated_image(image_bytes: bytes, mime: str, user_id: int, chat_id: int):
    ext = "jpg" if mime in {"image/jpeg", "image/jpg"} else "webp" if mime == "image/webp" else "png"
    original = f"holo-rick-bild.{ext}"
    stored = f"{int(time.time() * 1000)}_{secrets.token_hex(8)}_generated.{ext}"
    path = UPLOAD_DIR / stored
    path.write_bytes(image_bytes)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    with db() as con:
        cur = con.execute(
            """
            INSERT INTO uploads(user_id,chat_id,message_id,original_name,stored_name,mime,size,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (user_id, chat_id, None, original, stored, mime, len(image_bytes), now_iso()),
        )
        con.commit()
    return {
        "id": int(cur.lastrowid),
        "name": original,
        "url": f"/uploads/{stored}",
        "mime": mime,
        "size": len(image_bytes),
        "stored": stored,
    }


def generate_title(user_text: str, answer_text: str = "") -> str:
    if get_setting("auto_title", "true") != "true":
        return "Neuer Chat"
    words = bounded_int(get_setting("title_words", "2"), 2, 1, 4)
    fallback = user_text.strip().split("\n")[0][:28] or "Chat"
    prompt = (
        f"Erstelle einen deutschen Chat-Titel mit maximal {words} Wörtern. "
        "Kein Satz, keine Satzzeichen, keine Emojis, kein 'Holo Rick', keine Füllwörter. "
        "Nur das Thema. Beispiele: 'Dunkle Materie', 'Python Fehler', 'Brillen Eingewöhnung'.\n\n"
        f"User: {user_text[:1200]}\n\nAntwortauszug: {answer_text[:800]}"
    )
    try:
        title = call_llm(
            [
                {"role": "system", "content": "Du erzeugst extrem kurze, saubere Sidebar-Titel."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=20,
            model=MODEL,
        )
        title = clean_title(title, words)
        return title or fallback
    except Exception:
        return clean_title(fallback, words) or "Chat"


def clean_title(title: str, max_words: int) -> str:
    title = (title or "").strip().replace('"', "").replace("'", "")
    title = title.replace("Holo Rick", "").replace("Chat", "").strip(" -:|.,;!?")
    banned = {
        "geht",
        "fühlt",
        "hallo",
        "hey",
        "jo",
        "bitte",
        "kannst",
        "du",
        "was",
        "wie",
        "holo",
        "rick",
        "gehts",
        "fühl",
        "sich",
        "an",
        "nicht",
        "real",
        "sein",
        "sondern",
        "nur",
        "ein",
    }
    parts = [p for p in title.split() if p.lower().strip(".,:;!?") not in banned]
    if not parts:
        parts = title.split()
    return " ".join(parts[:max_words]).strip().title()[:40]


def allowed_extensions() -> set[str]:
    raw = os.environ.get("ALLOWED_UPLOAD_EXTENSIONS", "").strip()
    if not raw:
        return DEFAULT_UPLOAD_EXTENSIONS
    return {x.strip().lower().lstrip(".") for x in raw.split(",") if x.strip()}


def file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def allowed_file(filename: str) -> bool:
    return file_extension(filename) in allowed_extensions()


def save_upload(file, user_id: int | None = None, chat_id: int | None = None, message_id: int | None = None):
    original = secure_filename(file.filename or "upload")
    if not original or not allowed_file(original):
        raise ValueError(f"Dateityp nicht erlaubt: {original or 'unbekannt'}")
    ts = int(time.time() * 1000)
    stored = f"{ts}_{secrets.token_hex(8)}_{original}"
    path = UPLOAD_DIR / stored
    file.save(path)
    size = path.stat().st_size
    if size <= 0:
        path.unlink(missing_ok=True)
        raise ValueError(f"Datei ist leer: {original}")
    if size > MAX_UPLOAD_BYTES:
        path.unlink(missing_ok=True)
        raise ValueError(f"{original} ist zu groß. Maximal {MAX_UPLOAD_MB} MB pro Datei erlaubt.")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    with db() as con:
        cur = con.execute(
            """
            INSERT INTO uploads(user_id,chat_id,message_id,original_name,stored_name,mime,size,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (user_id, chat_id, message_id, original, stored, file.mimetype, size, now_iso()),
        )
        con.commit()
        upload_id = int(cur.lastrowid)
    return {
        "id": upload_id,
        "name": original,
        "url": f"/uploads/{stored}",
        "mime": file.mimetype,
        "size": size,
        "stored": stored,
    }


def cleanup_uploads(upload_infos):
    for upload in upload_infos:
        stored = upload.get("stored")
        if stored:
            try:
                (UPLOAD_DIR / stored).unlink(missing_ok=True)
            except Exception:
                pass
        if upload.get("id"):
            with db() as con:
                con.execute("DELETE FROM uploads WHERE id=?", (upload["id"],))
                con.commit()


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")[:MAX_EXTRACTED_CHARS]


def read_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    page_limit = bounded_int(os.environ.get("PDF_PAGE_LIMIT", "12"), 12, 1, 50)
    chunks = []
    for page in reader.pages[:page_limit]:
        chunks.append(page.extract_text() or "")
        if sum(len(c) for c in chunks) >= MAX_EXTRACTED_CHARS:
            break
    text = "\n".join(chunks).strip()
    return text[:MAX_EXTRACTED_CHARS] or "Kein extrahierbarer PDF-Text gefunden."


def prepare_attachment_context(upload_infos):
    chunks = []
    image_payloads = []
    for upload in upload_infos:
        name = upload.get("name", "")
        stored = upload.get("stored", "")
        path = UPLOAD_DIR / stored
        mime = upload.get("mime") or ""
        size = int(upload.get("size") or 0)
        ext = file_extension(name)
        if ext in TEXT_EXTENSIONS or mime.startswith("text/"):
            try:
                chunks.append(f"DATEI {name}:\n{read_text_file(path)}")
            except Exception:
                chunks.append(f"DATEI {name}: konnte nicht gelesen werden.")
        elif ext == "pdf" or mime == "application/pdf":
            try:
                chunks.append(f"PDF {name} (extrahierter Text):\n{read_pdf_text(path)}")
            except Exception:
                chunks.append(f"PDF {name}: Text konnte nicht extrahiert werden.")
        elif ext in IMAGE_EXTENSIONS or mime.startswith("image/"):
            if size <= VISION_BASE64_MAX_BYTES:
                data = base64.b64encode(path.read_bytes()).decode("ascii")
                safe_mime = mime if mime.startswith("image/") else f"image/{'jpeg' if ext == 'jpg' else ext}"
                image_payloads.append({"name": name, "data_url": f"data:{safe_mime};base64,{data}"})
                chunks.append(f"BILD {name}: wird dem Vision-Modell direkt zur Analyse übergeben.")
            else:
                chunks.append(
                    f"BILD {name}: gespeichert, aber zu groß für Base64-Vision ({size} Bytes). "
                    f"Maximal lokal konfiguriert: {VISION_BASE64_MAX_BYTES} Bytes."
                )
        else:
            chunks.append(f"DATEI {name}: hochgeladen ({mime or 'unbekannter Typ'}, {size} Bytes).")
    return "\n\n".join(chunks), image_payloads[:5]


def totp_issuer() -> str:
    return os.environ.get("TOTP_ISSUER", "Holo Rick").strip() or "Holo Rick"


def make_totp_qr(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def verify_totp(secret: str, code: str) -> bool:
    cleaned = "".join(ch for ch in str(code or "") if ch.isdigit())
    if not secret or len(cleaned) != 6:
        return False
    return pyotp.TOTP(secret).verify(cleaned, valid_window=1)


def git_update_now() -> tuple[bool, str]:
    repo_url = os.environ.get("AUTO_UPDATE_REPO", "https://github.com/PondSec/HoloRick.git")
    branch = os.environ.get("AUTO_UPDATE_BRANCH", "main")
    try:
        if not (BASE_DIR / ".git").exists():
            return False, "Kein Git-Repository im App-Ordner. Clone die App als Repo, sonst kann kein Pull laufen."
        cmds = [
            ["git", "remote", "set-url", "origin", repo_url],
            ["git", "fetch", "origin", branch],
            ["git", "merge", "--ff-only", f"origin/{branch}"],
        ]
        outputs = []
        for cmd in cmds:
            p = subprocess.run(cmd, cwd=str(BASE_DIR), text=True, capture_output=True, timeout=60)
            outputs.append(f"$ {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
            if p.returncode != 0:
                return False, "\n".join(outputs)
        return True, "\n".join(outputs)
    except Exception as e:
        return False, str(e)


def updater_loop():
    if os.environ.get("AUTO_UPDATE_ENABLED", "false").lower() != "true":
        return
    if not (BASE_DIR / ".git").exists():
        print("[AUTO_UPDATE] deaktiviert: kein Git-Repository im App-Ordner.")
        return
    interval = max(60, int(os.environ.get("AUTO_UPDATE_INTERVAL_SECONDS", "300")))
    while True:
        time.sleep(interval)
        ok, output = git_update_now()
        print(f"[AUTO_UPDATE] ok={ok}\n{output[-2000:]}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/me")
def me():
    limits = public_limits()
    user = current_user()
    guest_token = None if user else sign_guest_token(session.get("guest_token") or public_identity_token())
    response = jsonify(
        {
            "authenticated": bool(user),
            "email": user["email"] if user else None,
            "display_name": user["display_name"] if user else None,
            "role": user["role"] if user else None,
            "two_factor_enabled": bool(user and user["totp_enabled"]),
            "csrf_token": csrf_token(),
            "max_upload_mb": MAX_UPLOAD_MB,
            "max_files_per_message": MAX_FILES_PER_MESSAGE,
            "allowed_upload_extensions": sorted(allowed_extensions()),
            "public_limit_reached": limits["message_limit_reached"],
            "public_attachment_limit_reached": limits["attachment_limit_reached"],
            "public_message_limit": limits["message_limit"],
            "public_attachment_limit": limits["attachment_limit"],
            "public_messages_used": limits["messages_used"],
            "public_attachments_used": limits["attachments_used"],
            "guest_token": guest_token,
        }
    )
    if guest_token:
        response.set_cookie(
            "hr_guest",
            guest_token,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite="Lax",
            secure=app.config["SESSION_COOKIE_SECURE"],
        )
    return response


@app.route("/api/login", methods=["POST"])
def login():
    blocked = login_is_blocked()
    if blocked:
        return jsonify({"error": f"Zu viele Login-Versuche. Bitte in {blocked // 60 + 1} Minuten erneut versuchen."}), 429
    data = request.get_json() or {}
    user = find_user_by_email(data.get("email", ""))
    if not verify_user_password(user, data.get("password", "")):
        record_login_failure()
        time.sleep(0.6)
        return jsonify({"error": "Login fehlgeschlagen"}), 401
    if int(user["totp_enabled"] or 0):
        code = data.get("code", "")
        if not code:
            return jsonify({"requires_2fa": True, "message": "2FA-Code erforderlich"})
        if not verify_totp(user["totp_secret"], code):
            record_login_failure()
            time.sleep(0.6)
            return jsonify({"requires_2fa": True, "error": "2FA-Code ungültig"}), 401
    clear_login_failures()
    remember = str(data.get("remember", "true")).lower() in {"1", "true", "yes", "on"}
    session.clear()
    session.permanent = remember
    session["auth"] = True
    session["user_id"] = int(user["id"])
    session["email"] = user["email"]
    csrf_token()
    return jsonify({"ok": True})


@app.route("/api/register", methods=["POST"])
def register():
    blocked = registration_is_blocked()
    if blocked:
        return jsonify({"error": f"Zu viele Registrierungen. Bitte in {blocked // 60 + 1} Minuten erneut versuchen."}), 429
    record_registration_attempt()
    data = request.get_json() or {}
    email = normalize_email(data.get("email", ""))
    display_name = normalize_display_name(data.get("display_name", ""))
    password = data.get("password", "")
    privacy_ok = bool(data.get("privacy_accepted"))
    terms_ok = bool(data.get("terms_accepted")) or privacy_ok
    if not email:
        return jsonify({"error": "Bitte eine gültige E-Mail-Adresse eingeben."}), 400
    if not display_name:
        return jsonify({"error": "Bitte einen Anzeigenamen eingeben."}), 400
    password_error = validate_password(password)
    if password_error:
        return jsonify({"error": password_error}), 400
    if not privacy_ok or not terms_ok:
        return jsonify({"error": "Bitte Datenschutz- und Nutzungsbedingungen akzeptieren."}), 400
    if find_user_by_email(email):
        return jsonify({"error": "Für diese E-Mail existiert bereits ein Konto."}), 409
    ts = now_iso()
    password_hash = generate_password_hash(password)
    try:
        with db() as con:
            cur = con.execute(
                """
                INSERT INTO users(
                    email,password_hash,role,display_name,totp_enabled,
                    consent_at,privacy_version,terms_version,registration_ip_hash,created_at,updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    email,
                    password_hash,
                    "user",
                    display_name,
                    0,
                    ts,
                    PRIVACY_VERSION,
                    TERMS_VERSION,
                    ip_hash(client_ip()),
                    ts,
                    ts,
                ),
            )
            con.commit()
            user_id = int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return jsonify({"error": "Für diese E-Mail existiert bereits ein Konto."}), 409
    clear_registration_attempts()
    clear_login_failures()
    session.clear()
    session.permanent = True
    session["auth"] = True
    session["user_id"] = user_id
    session["email"] = email
    csrf_token()
    return jsonify({"ok": True})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/settings", methods=["GET", "PUT"])
def settings():
    if not is_admin():
        return jsonify({"error": "Admin-Login erforderlich"}), 401
    if request.method == "GET":
        return jsonify({**public_model_labels(), **{k: get_setting(k, v) for k, v in DEFAULT_SETTINGS.items()}})
    data = request.get_json() or {}
    for k in DEFAULT_SETTINGS:
        if k in data:
            set_setting(k, normalize_setting(k, data[k]))
    return jsonify({"ok": True})


@app.route("/api/security/2fa")
def two_factor_status():
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    return jsonify({"enabled": bool(user["totp_enabled"]), "email": user["email"]})


@app.route("/api/security/2fa/setup", methods=["POST"])
def two_factor_setup():
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    if int(user["totp_enabled"] or 0):
        return jsonify({"error": "2FA ist bereits aktiv"}), 400
    secret = pyotp.random_base32()
    session["pending_totp_secret"] = secret
    uri = pyotp.TOTP(secret).provisioning_uri(name=user["email"], issuer_name=totp_issuer())
    return jsonify({"secret": secret, "otpauth_uri": uri, "qr_data_url": make_totp_qr(uri)})


@app.route("/api/security/2fa/enable", methods=["POST"])
def two_factor_enable():
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    secret = session.get("pending_totp_secret")
    code = (request.get_json() or {}).get("code", "")
    if not verify_totp(secret, code):
        return jsonify({"error": "Code ungültig"}), 400
    with db() as con:
        con.execute("UPDATE users SET totp_secret=?, totp_enabled=1, updated_at=? WHERE id=?", (secret, now_iso(), user["id"]))
        con.commit()
    session.pop("pending_totp_secret", None)
    return jsonify({"ok": True})


@app.route("/api/security/2fa/disable", methods=["POST"])
def two_factor_disable():
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    data = request.get_json() or {}
    if not verify_user_password(user, data.get("password", "")):
        return jsonify({"error": "Passwort ungültig"}), 401
    if int(user["totp_enabled"] or 0) and not verify_totp(user["totp_secret"], data.get("code", "")):
        return jsonify({"error": "2FA-Code ungültig"}), 401
    with db() as con:
        con.execute("UPDATE users SET totp_secret=NULL, totp_enabled=0, updated_at=? WHERE id=?", (now_iso(), user["id"]))
        con.commit()
    return jsonify({"ok": True})


@app.route("/api/account/delete", methods=["POST", "DELETE"])
def delete_account():
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    data = request.get_json(silent=True) or {}
    if str(data.get("confirm") or "").strip() != "KONTO LÖSCHEN":
        return jsonify({"error": "Bitte KONTO LÖSCHEN als Bestätigung eingeben."}), 400
    if not verify_user_password(user, data.get("password", "")):
        return jsonify({"error": "Passwort ungültig"}), 401
    if int(user["totp_enabled"] or 0) and not verify_totp(user["totp_secret"], data.get("code", "")):
        return jsonify({"error": "2FA-Code ungültig"}), 401

    user_id = int(user["id"])
    with db() as con:
        rows = con.execute("SELECT stored_name FROM uploads WHERE user_id=?", (user_id,)).fetchall()
        cur = con.execute("DELETE FROM users WHERE id=?", (user_id,))
        con.commit()
    if cur.rowcount == 0:
        session.clear()
        return jsonify({"ok": True})

    for row in rows:
        try:
            (UPLOAD_DIR / row["stored_name"]).unlink(missing_ok=True)
        except Exception:
            app.logger.warning("account upload cleanup failed", exc_info=True)
    session.clear()
    g.current_user = None
    return jsonify({"ok": True})


@app.route("/api/chats", methods=["GET", "POST"])
def chats():
    user = current_user()
    if not user:
        if request.method == "GET":
            return jsonify([])
        if public_limit_reached():
            return jsonify({"error": "PUBLIC_LIMIT"}), 429
    if request.method == "POST":
        chat_id = create_chat(int(user["id"]), "Neuer Chat") if user else 0
        return jsonify({"id": chat_id})
    archived = 1 if request.args.get("archived") == "1" else 0
    with db() as con:
        rows = con.execute(
            """
            SELECT id,title,archived,created_at,updated_at
            FROM chats
            WHERE user_id=? AND archived=?
            ORDER BY updated_at DESC
            """,
            (user["id"], archived),
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/chats/<int:chat_id>")
def chat_detail(chat_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    row = get_chat_for_user(chat_id, int(user["id"]))
    if not row:
        return jsonify({"error": "Chat nicht gefunden"}), 404
    return jsonify({"chat": dict(row), "messages": fetch_messages(chat_id, int(user["id"]))})


@app.route("/api/chats/<int:chat_id>/archive", methods=["POST"])
def archive_chat(chat_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    archived = 1 if (request.get_json() or {}).get("archived", True) else 0
    with db() as con:
        cur = con.execute(
            "UPDATE chats SET archived=?, updated_at=? WHERE id=? AND user_id=?",
            (archived, now_iso(), chat_id, user["id"]),
        )
        con.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Chat nicht gefunden"}), 404
    return jsonify({"ok": True})


@app.route("/api/chats/<int:chat_id>/delete", methods=["POST", "DELETE"])
def delete_chat(chat_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    with db() as con:
        rows = con.execute("SELECT stored_name FROM uploads WHERE chat_id=? AND user_id=?", (chat_id, user["id"])).fetchall()
        cur = con.execute("DELETE FROM chats WHERE id=? AND user_id=?", (chat_id, user["id"]))
        con.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "Chat nicht gefunden"}), 404
    for row in rows:
        try:
            (UPLOAD_DIR / row["stored_name"]).unlink(missing_ok=True)
        except Exception:
            pass
    return jsonify({"ok": True})


@app.route("/api/chats/<int:chat_id>/retitle", methods=["POST"])
def retitle(chat_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    if not get_chat_for_user(chat_id, int(user["id"])):
        return jsonify({"error": "Chat nicht gefunden"}), 404
    messages = fetch_messages(chat_id, int(user["id"]))
    first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
    assistant = next((m["content"] for m in messages if m["role"] == "assistant"), "")
    title = generate_title(first_user, assistant)
    with db() as con:
        con.execute("UPDATE chats SET title=?, updated_at=? WHERE id=? AND user_id=?", (title, now_iso(), chat_id, user["id"]))
        con.commit()
    return jsonify({"title": title})


@app.route("/api/chats/<int:chat_id>/context", methods=["GET", "PUT"])
def chat_context(chat_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    chat = get_chat_for_user(chat_id, int(user["id"]))
    if not chat:
        return jsonify({"error": "Chat nicht gefunden"}), 404
    if request.method == "GET":
        return jsonify(
            {
                "project_context": chat["project_context"] or "",
                "context_updated_at": chat["context_updated_at"],
            }
        )
    data = request.get_json() or {}
    if not update_chat_context(chat_id, int(user["id"]), data.get("project_context", "")):
        return jsonify({"error": "Chat nicht gefunden"}), 404
    return jsonify({"ok": True, "project_context": normalize_project_context(data.get("project_context", ""))})


@app.route("/api/chats/<int:chat_id>/context/brief", methods=["POST"])
def chat_context_brief(chat_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    user_id = int(user["id"])
    chat = get_chat_for_user(chat_id, user_id)
    if not chat:
        return jsonify({"error": "Chat nicht gefunden"}), 404
    history = fetch_messages(chat_id, user_id)
    usable = [m for m in history if m["role"] in {"user", "assistant"} and (m.get("content") or "").strip()]
    if not usable:
        return jsonify({"error": "Noch zu wenig Chatinhalt für einen Smart Brief"}), 400
    transcript = "\n\n".join(f"{m['role'].upper()}:\n{m['content']}" for m in usable[-14:])[:14000]
    existing = chat["project_context"] or ""
    prompt = (
        "Erstelle einen kompakten Projektkontext fuer diesen Chat. Extrahiere nur Dinge, die fuer spaetere Antworten "
        "dauerhaft nuetzlich sind: Ziel, Nutzerpraeferenzen, Entscheidungen, wichtige Fakten, offene Punkte, No-Gos. "
        "Keine Spekulationen, keine langen Erklaerungen. Maximal 14 kurze Bulletpoints.\n\n"
        f"Bisheriger Kontext:\n{existing or '-'}\n\nChat-Auszug:\n{transcript}"
    )
    try:
        messages = build_messages(
            [],
            prompt,
            ai_mode="precise",
            response_format="steps",
            project_context=existing,
        )
        brief = normalize_project_context(call_llm(messages, temperature=0.2, max_tokens=900))
        update_chat_context(chat_id, user_id, brief)
        return jsonify({"project_context": brief, "context_updated_at": now_iso()})
    except Exception as exc:
        if is_rate_limit_error(exc):
            return rate_limit_response(exc)
        app.logger.exception("context brief failed")
        return jsonify({"error": "Smart Brief konnte nicht erzeugt werden."}), 502


@app.route("/api/chats/<int:chat_id>/action", methods=["POST"])
def chat_smart_action(chat_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    user_id = int(user["id"])
    chat = get_chat_for_user(chat_id, user_id)
    if not chat:
        return jsonify({"error": "Chat nicht gefunden"}), 404
    data = request.get_json() or {}
    action_key = str(data.get("action") or "").strip()
    action = SMART_ACTIONS.get(action_key)
    if not action:
        return jsonify({"error": "Aktion nicht bekannt"}), 400
    source_id = data.get("source_message_id")
    source = None
    with db() as con:
        if source_id:
            source = con.execute(
                """
                SELECT m.id,m.content
                FROM messages m
                JOIN chats c ON c.id=m.chat_id
                WHERE m.id=? AND m.chat_id=? AND c.user_id=? AND m.role='assistant'
                """,
                (source_id, chat_id, user_id),
            ).fetchone()
        if not source:
            source = con.execute(
                """
                SELECT m.id,m.content
                FROM messages m
                JOIN chats c ON c.id=m.chat_id
                WHERE m.chat_id=? AND c.user_id=? AND m.role='assistant'
                ORDER BY m.id DESC
                LIMIT 1
                """,
                (chat_id, user_id),
            ).fetchone()
    if not source:
        return jsonify({"error": "Keine Antwort für diese Aktion gefunden"}), 400
    history = fetch_messages(chat_id, user_id)
    source_text = str(source["content"] or "")[:12000]
    prompt = action["prompt"].format(source=source_text)
    user_text = f"{action['label']} erstellen"
    try:
        messages = build_messages(
            history,
            prompt,
            ai_mode=action["mode"],
            response_format=action["format"],
            project_context=chat["project_context"] or "",
        )
        answer = call_llm(messages, temperature=0.35, max_tokens=1800)
        user_message_id = add_message(
            chat_id,
            user_id,
            "user",
            user_text,
            {"smart_action": action_key, "source_message_id": int(source["id"])},
        )
        assistant_id = add_message(chat_id, user_id, "assistant", answer)
        return jsonify(
            {
                "user_message": {
                    "id": user_message_id,
                    "role": "user",
                    "content": user_text,
                    "meta": json.dumps({"smart_action": action_key, "source_message_id": int(source["id"])}),
                    "created_at": now_iso(),
                },
                "assistant_message": {
                    "id": assistant_id,
                    "role": "assistant",
                    "content": answer,
                    "content_html": render_markdown(answer),
                    "created_at": now_iso(),
                },
            }
        )
    except Exception as exc:
        if is_rate_limit_error(exc):
            return rate_limit_response(exc)
        app.logger.exception("smart action failed")
        return jsonify({"error": "Smart-Aktion konnte nicht ausgeführt werden."}), 502


@app.route("/api/send", methods=["POST"])
def send():
    if request.form:
        data = request.form
    else:
        data = request.get_json(silent=True) or {}
    text = (data.get("message") or "").strip()
    ai_mode = normalize_ai_mode((data.get("ai_mode") or "holo").strip())
    response_format = normalize_response_format((data.get("response_format") or "auto").strip())
    user = current_user()
    try:
        chat_id = int(data.get("chat_id") or 0)
    except (TypeError, ValueError):
        chat_id = 0
    files = request.files.getlist("files")
    has_attachment = bool(files)
    if len(files) > MAX_FILES_PER_MESSAGE:
        return jsonify({"error": f"Maximal {MAX_FILES_PER_MESSAGE} Dateien pro Nachricht erlaubt"}), 400
    if not user and public_limit_reached(has_attachment=has_attachment):
        return jsonify({"error": "PUBLIC_LIMIT", "message": "Nutzungslimit erreicht"}), 429
    if not text and not has_attachment:
        return jsonify({"error": "Nachricht ist leer"}), 400

    if not user:
        chat_id = 0
        history = []
        user_id = None
    else:
        user_id = int(user["id"])
        if chat_id:
            chat = get_chat_for_user(chat_id, user_id)
            if not chat:
                return jsonify({"error": "Chat nicht gefunden"}), 404
        else:
            chat_id = create_chat(user_id, "Neuer Chat")
            chat = get_chat_for_user(chat_id, user_id)
        history = fetch_messages(chat_id, user_id)

    upload_infos = []
    persist_uploads = False
    try:
        for file in files:
            upload_infos.append(save_upload(file, user_id=user_id, chat_id=chat_id if chat_id else None, message_id=None))
        attachment_text, image_payloads = prepare_attachment_context(upload_infos)
        project_context = chat["project_context"] if user_id and chat else ""
        image_generation = None
        assistant_meta = {}
        if wants_image_generation(text, has_attachment=has_attachment):
            image_prompt = build_image_prompt(text, attachment_text)
            image_generation = generate_image_from_prompt(image_prompt)
            answer = "Bild ist fertig."
        else:
            messages = build_messages(
                history,
                text,
                attachment_text,
                image_payloads,
                ai_mode=ai_mode,
                response_format=response_format,
                project_context=project_context,
            )
            answer = call_llm(messages)

        title = None
        user_message_id = None
        assistant_id = None
        if user_id:
            public_uploads = [{k: v for k, v in u.items() if k != "stored"} for u in upload_infos]
            user_message_id = add_message(
                chat_id,
                user_id,
                "user",
                text,
                {"uploads": public_uploads, "ai_mode": ai_mode, "response_format": response_format},
            )
            generated_upload = None
            if image_generation:
                generated_upload = save_generated_image(
                    image_generation["bytes"],
                    image_generation["mime"],
                    user_id,
                    chat_id,
                )
                assistant_meta["image_generation"] = {
                    "prompt": text,
                    "revised_prompt": image_generation.get("revised_prompt", ""),
                    "image": {k: v for k, v in generated_upload.items() if k != "stored"},
                }
            assistant_id = add_message(chat_id, user_id, "assistant", answer, assistant_meta)
            if generated_upload:
                with db() as con:
                    con.execute(
                        "UPDATE uploads SET message_id=? WHERE id=? AND user_id=?",
                        (assistant_id, generated_upload["id"], user_id),
                    )
                    con.commit()
            for upload in upload_infos:
                with db() as con:
                    con.execute(
                        "UPDATE uploads SET chat_id=?, message_id=? WHERE id=? AND user_id=?",
                        (chat_id, user_message_id, upload["id"], user_id),
                    )
                    con.commit()
            persist_uploads = True
            if len(history) == 0:
                title = generate_title(text, answer)
                with db() as con:
                    con.execute("UPDATE chats SET title=? WHERE id=? AND user_id=?", (title, chat_id, user_id))
                    con.commit()
        elif image_generation:
            data_url = "data:{};base64,{}".format(
                image_generation["mime"],
                base64.b64encode(image_generation["bytes"]).decode("ascii"),
            )
            assistant_meta["image_generation"] = {
                "prompt": text,
                "revised_prompt": image_generation.get("revised_prompt", ""),
                "image": {
                    "name": "holo-rick-bild.png",
                    "data_url": data_url,
                    "mime": image_generation["mime"],
                    "size": len(image_generation["bytes"]),
                },
            }
        if not user_id:
            increment_public_usage(has_attachment=bool(upload_infos))
        return jsonify(
            {
                "chat_id": chat_id,
                "title": title,
                "user_message": {
                    "id": user_message_id,
                    "role": "user",
                    "content": text,
                    "meta": json.dumps(
                        {
                            "uploads": [{k: v for k, v in u.items() if k != "stored"} for u in upload_infos],
                            "ai_mode": ai_mode,
                            "response_format": response_format,
                        },
                        ensure_ascii=False,
                    ),
                    "created_at": now_iso(),
                },
                "assistant_message": {
                    "id": assistant_id,
                    "role": "assistant",
                    "content": answer,
                    "meta": json.dumps(assistant_meta, ensure_ascii=False),
                    "content_html": render_markdown(answer),
                    "created_at": now_iso(),
                },
                "public_limit_reached": public_limit_reached() if not user_id else False,
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        if is_rate_limit_error(exc):
            return rate_limit_response(exc)
        if "Bildgenerierung" in str(exc):
            return jsonify({"error": str(exc)}), 503
        app.logger.exception("send failed")
        return jsonify({"error": "Antwort konnte nicht erzeugt werden. Bitte erneut versuchen oder den Anhang verkleinern."}), 502
    finally:
        if not persist_uploads:
            cleanup_uploads(upload_infos)


@app.route("/uploads/<path:name>")
def uploads(name):
    user = current_user()
    if not user:
        return jsonify({"error": "Login erforderlich"}), 401
    if "/" in name or "\\" in name or name != secure_filename(name):
        return jsonify({"error": "Datei nicht gefunden"}), 404
    with db() as con:
        row = con.execute(
            "SELECT original_name,stored_name,mime FROM uploads WHERE stored_name=? AND user_id=?",
            (name, user["id"]),
        ).fetchone()
    if not row:
        return jsonify({"error": "Datei nicht gefunden"}), 404
    return send_from_directory(
        UPLOAD_DIR,
        row["stored_name"],
        mimetype=row["mime"] or None,
        as_attachment=False,
        download_name=row["original_name"],
    )


@app.route("/api/update", methods=["POST"])
def update():
    secret = request.headers.get("X-Update-Secret") or (request.get_json(silent=True) or {}).get("secret")
    expected = os.environ.get("UPDATE_WEBHOOK_SECRET", "")
    if not expected or not hmac.compare_digest(secret or "", expected):
        return jsonify({"error": "Forbidden"}), 403
    ok, output = git_update_now()
    return jsonify({"ok": ok, "output": output[-6000:]})


init_db()
threading.Thread(target=updater_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("APP_HOST", "0.0.0.0"),
        port=int(os.environ.get("APP_PORT", "8362")),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )
