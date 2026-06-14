import hashlib
import hmac
import json
import os
import sqlite3
import subprocess
import threading
import time
import secrets
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session, send_from_directory, g
from groq import Groq
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

def load_secret_key() -> str:
    configured = os.environ.get("FLASK_SECRET_KEY", "").strip()
    if configured:
        return configured

    # A random in-memory key breaks sessions as soon as a request lands on a
    # different gunicorn worker or the container restarts. Keep a generated key
    # in the persisted instance directory so login behaves the same behind the
    # public reverse proxy as it does during a single-process local run.
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
        # Last-resort fallback for read-only environments. This is intentionally
        # not the normal path because it cannot support multi-worker sessions.
        return os.urandom(32).hex()


app = Flask(__name__)
app.secret_key = load_secret_key()
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", "12")) * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 8
if os.environ.get("TRUST_PROXY", "false").lower() == "true":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.before_request
def request_guard():
    g.started_at = time.perf_counter()
    if request.endpoint == "login":
        return None
    if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
        token = csrf_token()
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not hmac.compare_digest(sent or "", token):
            return jsonify({
                "error": "Sicherheitsprüfung fehlgeschlagen. Seite neu laden.",
                "csrf_token": token,
            }), 403


@app.after_request
def harden_response(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'")
    response.headers["X-Response-Time"] = f"{(time.perf_counter() - getattr(g, 'started_at', time.perf_counter())) * 1000:.1f}ms"
    return response

MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

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
    "privacy_mode": "true",
    "safe_uploads": "true",
}

DEFAULT_ALLOWED_UPLOADS = {"png","jpg","jpeg","gif","webp","pdf","txt","md","py","js","ts","html","css","json","yml","yaml","toml","log","csv"}
MAX_FILES_PER_MESSAGE = 5
MAX_TEXT_CHARS = 24000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sanitize_text(value: str, limit: int = MAX_TEXT_CHARS) -> str:
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value or "")
    return value[:limit].strip()


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db() as con:
        con.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS chats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT 'Neuer Chat',
                archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content TEXT NOT NULL,
                meta TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS public_usage(
                ip_hash TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0,
                attachment_count INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS uploads(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message_id INTEGER,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                mime TEXT,
                size INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE,
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE SET NULL
            );
            """
        )
        try:
            con.execute("ALTER TABLE public_usage ADD COLUMN attachment_count INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
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


def is_logged_in() -> bool:
    return session.get("auth") is True


def admin_email() -> str:
    return os.environ.get("ADMIN_EMAIL", "joshua@pondsec.com").strip().lower()


def verify_admin(email: str, password: str) -> bool:
    email = (email or "").strip().lower()
    if email != admin_email():
        return False
    stored_hash = os.environ.get("ADMIN_PASSWORD_HASH", "").strip()
    if stored_hash:
        return check_password_hash(stored_hash, password or "")
    raw = os.environ.get("ADMIN_PASSWORD", "")
    return bool(raw) and hmac.compare_digest(raw, password or "")


def client_ip() -> str:
    # ProxyFix makes request.remote_addr honor X-Forwarded-For when TRUST_PROXY=true.
    return request.remote_addr or "unknown"


def ip_hash(ip: str) -> str:
    secret = os.environ.get("IP_HASH_SECRET", app.secret_key)
    return hmac.new(secret.encode(), ip.encode(), hashlib.sha256).hexdigest()


def public_limits() -> dict:
    msg_limit = int(get_setting("public_message_limit", os.environ.get("PUBLIC_MESSAGE_LIMIT", "3")) or 3)
    attachment_limit = int(get_setting("public_attachment_limit", os.environ.get("PUBLIC_ATTACHMENT_LIMIT", "1")) or 1)
    if is_logged_in():
        return {"message_limit": msg_limit, "attachment_limit": attachment_limit, "messages_used": 0, "attachments_used": 0, "message_limit_reached": False, "attachment_limit_reached": False}
    key = ip_hash(client_ip())
    with db() as con:
        row = con.execute("SELECT count, attachment_count FROM public_usage WHERE ip_hash=?", (key,)).fetchone()
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
    key = ip_hash(client_ip())
    ts = now_iso()
    add_attachment = 1 if has_attachment else 0
    with db() as con:
        con.execute(
            """
            INSERT INTO public_usage(ip_hash,count,attachment_count,first_seen,last_seen) VALUES(?,?,?,?,?)
            ON CONFLICT(ip_hash) DO UPDATE SET count=count+1, attachment_count=attachment_count+excluded.attachment_count, last_seen=excluded.last_seen
            """,
            (key, 1, add_attachment, ts, ts),
        )
        con.commit()


def create_chat(title="Neuer Chat") -> int:
    ts = now_iso()
    with db() as con:
        cur = con.execute("INSERT INTO chats(title,created_at,updated_at) VALUES(?,?,?)", (title, ts, ts))
        con.commit()
        return int(cur.lastrowid)


def add_message(chat_id: int, role: str, content: str, meta: dict | None = None) -> int:
    ts = now_iso()
    with db() as con:
        cur = con.execute(
            "INSERT INTO messages(chat_id,role,content,meta,created_at) VALUES(?,?,?,?,?)",
            (chat_id, role, content, json.dumps(meta or {}, ensure_ascii=False), ts),
        )
        con.execute("UPDATE chats SET updated_at=? WHERE id=?", (ts, chat_id))
        con.commit()
        return int(cur.lastrowid)


def fetch_messages(chat_id: int):
    with db() as con:
        rows = con.execute("SELECT id,role,content,meta,created_at FROM messages WHERE chat_id=? ORDER BY id ASC", (chat_id,)).fetchall()
        return [dict(r) for r in rows]


def build_messages(history, user_message: str, attachment_context: str = ""):
    context_n = max(2, min(int(get_setting("context_messages", "12") or 12), 40))
    style_mode = get_setting("style_mode", "holo")
    answer_length = get_setting("answer_length", "normal")
    system_prompt = get_setting("system_prompt", DEFAULT_SYSTEM_PROMPT)
    creator = get_setting("creator_name", "Joshua Dean Pond")
    owner = get_setting("brand_owner", "PondSec")
    if is_logged_in():
        identity = (
            "\nAktueller Nutzerstatus: ANGEMELDET. "
            "Du sprichst mit Joshua. Behandle ihn als Betreiber/Entwickler/Admin dieses Systems. "
            "Du darfst ihn Joshua nennen. "
        )
    else:
        identity = (
            "\nAktueller Nutzerstatus: GAST. "
            "Du sprichst mit einem unbekannten öffentlichen Gast. Keine privaten Admin-Details preisgeben. "
        )
    system_extra = (
        f"\nStilmodus: {style_mode}. Antwortlänge: {answer_length}."
        f"\nCreator/Programmierer: {creator}. Betreiber/Brand: {owner}."
        + identity
    )
    messages = [{"role": "system", "content": system_prompt + system_extra}]
    for m in history[-context_n:]:
        if m["role"] in ["user", "assistant"]:
            messages.append({"role": m["role"], "content": m["content"]})
    final_user = user_message
    if attachment_context:
        final_user += "\n\nAnhänge/Dateikontext:\n" + attachment_context
    messages.append({"role": "user", "content": final_user})
    return messages


def call_llm(messages, temperature=None, max_tokens=None) -> str:
    if not client:
        raise RuntimeError("GROQ_API_KEY fehlt. Trage ihn in .env ein.")
    temp = float(temperature if temperature is not None else get_setting("temperature", "0.75"))
    mt = int(max_tokens if max_tokens is not None else get_setting("max_tokens", "4096"))
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temp,
        max_completion_tokens=mt,
        top_p=1,
    )
    return completion.choices[0].message.content or ""


def generate_title(user_text: str, answer_text: str = "", force: bool = False) -> str:
    if not force and get_setting("auto_title", "true") != "true":
        return "Neuer Chat"
    words = max(1, min(int(get_setting("title_words", "2") or 2), 4))
    fallback = user_text.strip().split("\n")[0][:28] or "Chat"
    prompt = (
        f"Erstelle einen deutschen Chat-Titel mit maximal {words} Wörtern. "
        "Kein Satz, keine Satzzeichen, keine Emojis, kein 'Holo Rick', keine Füllwörter. "
        "Nur das Thema. Beispiele: 'Dunkle Materie', 'Python Fehler', 'Brillen Eingewöhnung'.\n\n"
        f"User: {user_text[:1200]}\n\nAntwortauszug: {answer_text[:800]}"
    )
    try:
        title = call_llm([
            {"role": "system", "content": "Du erzeugst extrem kurze, saubere Sidebar-Titel."},
            {"role": "user", "content": prompt},
        ], temperature=0.1, max_tokens=20)
        title = clean_title(title, words)
        return title or fallback
    except Exception:
        return clean_title(fallback, words) or "Chat"


def clean_title(title: str, max_words: int) -> str:
    title = (title or "").strip().replace('"', '').replace("'", '')
    title = title.replace("Holo Rick", "").replace("Chat", "").strip(" -:|.,;!?")
    banned = {"geht", "fühlt", "fühlt", "hallo", "hey", "jo", "bitte", "kannst", "du", "was", "wie", "holo", "rick", "gehts", "geht", "fühl", "sich", "an", "nicht", "real", "sein", "sondern", "nur", "ein"}
    parts = [p for p in title.split() if p.lower().strip(".,:;!?") not in banned]
    if not parts:
        parts = title.split()
    return " ".join(parts[:max_words]).strip().title()[:40]


def allowed_file(filename: str) -> bool:
    allowed = {x.strip().lower() for x in os.environ.get("ALLOWED_UPLOAD_EXTENSIONS", "").split(",") if x.strip()}
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not allowed:
        allowed = DEFAULT_ALLOWED_UPLOADS
    return ext in allowed


def save_upload(file, chat_id: int | None = None, message_id: int | None = None):
    original = secure_filename(file.filename or "upload")
    if not original or not allowed_file(original):
        raise ValueError(f"Dateityp nicht erlaubt: {original}")
    ts = int(time.time() * 1000)
    stored = f"{ts}_{os.urandom(6).hex()}_{original}"
    path = UPLOAD_DIR / stored
    file.save(path)
    size = path.stat().st_size
    with db() as con:
        cur = con.execute(
            "INSERT INTO uploads(chat_id,message_id,original_name,stored_name,mime,size,created_at) VALUES(?,?,?,?,?,?,?)",
            (chat_id, message_id, original, stored, file.mimetype, size, now_iso()),
        )
        con.commit()
        upload_id = int(cur.lastrowid)
    return {"id": upload_id, "name": original, "url": f"/uploads/{stored}", "mime": file.mimetype, "size": size, "stored": stored}


def attachment_context(upload_infos):
    chunks = []
    for u in upload_infos:
        name = u.get("name", "")
        stored = u.get("stored", "")
        path = UPLOAD_DIR / stored
        mime = u.get("mime") or ""
        if mime.startswith("text/") or Path(name).suffix.lower() in {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json", ".yml", ".yaml", ".toml", ".log", ".csv"}:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")[:8000]
                chunks.append(f"DATEI {name}:\n{text}")
            except Exception:
                chunks.append(f"DATEI {name}: konnte nicht gelesen werden")
        else:
            chunks.append(f"DATEI {name}: hochgeladen ({mime}, {u.get('size')} bytes). Bild/PDF wird gespeichert, aber vom aktuellen Textmodell nicht visuell analysiert.")
    return "\n\n".join(chunks)


def git_update_now() -> tuple[bool, str]:
    repo_url = os.environ.get("AUTO_UPDATE_REPO", "https://github.com/PondSec/HoloRick.git")
    branch = os.environ.get("AUTO_UPDATE_BRANCH", "main")
    try:
        if not (BASE_DIR / ".git").exists():
            return False, "Kein Git-Repository im App-Ordner. Clone die App als Repo, sonst kann kein Pull laufen."
        cmds = [
            ["git", "remote", "set-url", "origin", repo_url],
            ["git", "fetch", "origin", branch],
            ["git", "reset", "--hard", f"origin/{branch}"],
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
    return jsonify({
        "authenticated": is_logged_in(),
        "email": admin_email() if is_logged_in() else None,
        "public_limit_reached": limits["message_limit_reached"],
        "public_attachment_limit_reached": limits["attachment_limit_reached"],
        "public_message_limit": limits["message_limit"],
        "public_attachment_limit": limits["attachment_limit"],
        "public_messages_used": limits["messages_used"],
        "public_attachments_used": limits["attachments_used"],
        "csrf_token": csrf_token(),
    })


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    if verify_admin(data.get("email", ""), data.get("password", "")):
        session.clear()
        session["csrf_token"] = secrets.token_urlsafe(32)
        session["auth"] = True
        session["email"] = admin_email()
        return jsonify({"ok": True})
    time.sleep(0.6)
    return jsonify({"error": "Login fehlgeschlagen"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/settings", methods=["GET", "PUT"])
def settings():
    if not is_logged_in():
        return jsonify({"error": "Login erforderlich"}), 401
    if request.method == "GET":
        return jsonify({"model": MODEL, **{k: get_setting(k, v) for k, v in DEFAULT_SETTINGS.items()}})
    data = request.get_json() or {}
    for k in DEFAULT_SETTINGS:
        if k in data:
            set_setting(k, str(data[k]))
    return jsonify({"ok": True})


@app.route("/api/chats", methods=["GET", "POST"])
def chats():
    if not is_logged_in():
        # Anonymous gets an ephemeral single chat experience, not saved list.
        if request.method == "GET":
            return jsonify([])
        if public_limit_reached():
            return jsonify({"error": "PUBLIC_LIMIT"}), 429
    if request.method == "POST":
        chat_id = create_chat("Neuer Chat") if is_logged_in() else 0
        return jsonify({"id": chat_id})
    archived = 1 if request.args.get("archived") == "1" else 0
    with db() as con:
        rows = con.execute("SELECT id,title,archived,created_at,updated_at FROM chats WHERE archived=? ORDER BY updated_at DESC", (archived,)).fetchall()
        return jsonify([dict(r) for r in rows])


@app.route("/api/chats/<int:chat_id>")
def chat_detail(chat_id):
    if not is_logged_in():
        return jsonify({"error": "Login erforderlich"}), 401
    with db() as con:
        row = con.execute("SELECT id,title,archived,created_at,updated_at FROM chats WHERE id=?", (chat_id,)).fetchone()
    if not row:
        return jsonify({"error": "Chat nicht gefunden"}), 404
    return jsonify({"chat": dict(row), "messages": fetch_messages(chat_id)})


@app.route("/api/chats/<int:chat_id>/archive", methods=["POST"])
def archive_chat(chat_id):
    if not is_logged_in():
        return jsonify({"error": "Login erforderlich"}), 401
    archived = 1 if (request.get_json() or {}).get("archived", True) else 0
    with db() as con:
        con.execute("UPDATE chats SET archived=?, updated_at=? WHERE id=?", (archived, now_iso(), chat_id))
        con.commit()
    return jsonify({"ok": True})




@app.route("/api/chats/<int:chat_id>/delete", methods=["POST", "DELETE"])
def delete_chat(chat_id):
    if not is_logged_in():
        return jsonify({"error": "Login erforderlich"}), 401
    with db() as con:
        rows = con.execute("SELECT stored_name FROM uploads WHERE chat_id=?", (chat_id,)).fetchall()
        con.execute("DELETE FROM chats WHERE id=?", (chat_id,))
        con.commit()
    for row in rows:
        try:
            (UPLOAD_DIR / row["stored_name"]).unlink(missing_ok=True)
        except Exception:
            pass
    return jsonify({"ok": True})

@app.route("/api/chats/<int:chat_id>/retitle", methods=["POST"])
def retitle(chat_id):
    if not is_logged_in():
        return jsonify({"error": "Login erforderlich"}), 401
    messages = fetch_messages(chat_id)
    user = next((m["content"] for m in messages if m["role"] == "user"), "")
    assistant = next((m["content"] for m in messages if m["role"] == "assistant"), "")
    title = generate_title(user, assistant, force=True)
    with db() as con:
        con.execute("UPDATE chats SET title=?, updated_at=? WHERE id=?", (title, now_iso(), chat_id))
        con.commit()
    return jsonify({"title": title})


@app.route("/api/send", methods=["POST"])
def send():
    data = request.form if request.content_type and request.content_type.startswith("multipart/form-data") else (request.get_json() or {})
    text = sanitize_text(data.get("message") or "")
    chat_id = int(data.get("chat_id") or 0)
    has_attachment = bool(request.files.getlist("files"))
    if public_limit_reached(has_attachment=has_attachment):
        return jsonify({"error": "PUBLIC_LIMIT", "message": "Nutzungslimit erreicht"}), 429
    if not text and not has_attachment:
        return jsonify({"error": "Nachricht ist leer"}), 400
    if not is_logged_in():
        chat_id = 0
        history = []
    else:
        if not chat_id:
            chat_id = create_chat("Neuer Chat")
        history = fetch_messages(chat_id)
    upload_infos = []
    files = request.files.getlist("files")[:MAX_FILES_PER_MESSAGE]
    if len(request.files.getlist("files")) > MAX_FILES_PER_MESSAGE:
        return jsonify({"error": f"Maximal {MAX_FILES_PER_MESSAGE} Dateien pro Nachricht"}), 400
    for f in files:
        upload_infos.append(save_upload(f, chat_id if chat_id else None, None))
    ctx = attachment_context(upload_infos)
    messages = build_messages(history, text, ctx)
    try:
        answer = call_llm(messages)
        title = None
        user_id = None
        assistant_id = None
        if is_logged_in():
            user_id = add_message(chat_id, "user", text, {"uploads": upload_infos})
            assistant_id = add_message(chat_id, "assistant", answer)
            for u in upload_infos:
                with db() as con:
                    con.execute("UPDATE uploads SET chat_id=?, message_id=? WHERE id=?", (chat_id, user_id, u["id"]))
                    con.commit()
            if len(history) == 0:
                title = generate_title(text, answer, force=True)
                with db() as con:
                    con.execute("UPDATE chats SET title=? WHERE id=?", (title, chat_id))
                    con.commit()
        increment_public_usage(has_attachment=bool(upload_infos))
        return jsonify({
            "chat_id": chat_id,
            "title": title,
            "user_message": {"id": user_id, "role": "user", "content": text, "meta": json.dumps({"uploads": upload_infos}, ensure_ascii=False), "created_at": now_iso()},
            "assistant_message": {"id": assistant_id, "role": "assistant", "content": answer, "created_at": now_iso()},
            "public_limit_reached": public_limit_reached(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/uploads/<path:name>")
def uploads(name):
    if not is_logged_in():
        return jsonify({"error": "Login erforderlich"}), 401
    return send_from_directory(UPLOAD_DIR, name)



@app.route("/api/chats/<int:chat_id>/export")
def export_chat(chat_id):
    if not is_logged_in():
        return jsonify({"error": "Login erforderlich"}), 401
    with db() as con:
        chat = con.execute("SELECT id,title,created_at,updated_at FROM chats WHERE id=?", (chat_id,)).fetchone()
    if not chat:
        return jsonify({"error": "Chat nicht gefunden"}), 404
    messages = fetch_messages(chat_id)
    return jsonify({"chat": dict(chat), "messages": messages, "exported_at": now_iso()})


@app.route("/api/chats/<int:chat_id>/summarize", methods=["POST"])
def summarize_chat(chat_id):
    if not is_logged_in():
        return jsonify({"error": "Login erforderlich"}), 401
    messages = fetch_messages(chat_id)
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-20:])
    summary = call_llm([
        {"role": "system", "content": "Fasse den Chat in Deutsch als kurze, klare Arbeitsnotiz zusammen: Ziel, wichtige Fakten, offene nächste Schritte."},
        {"role": "user", "content": transcript[:12000]},
    ], temperature=0.2, max_tokens=700)
    add_message(chat_id, "assistant", "**Kurznotiz**\n\n" + summary)
    return jsonify({"summary": summary})

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
