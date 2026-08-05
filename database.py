from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from typing import TypedDict, Annotated
from langchain_groq import ChatGroq

import os
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage

# Persistence
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state: ChatState):
    # Take query from user
    messages = state["messages"]

    # Send to LLM
    response = llm.invoke(messages)

    # Store response in state
    return {
        "messages": [response]
    }

import time

def get_db():
    c = sqlite3.connect(database='chatbot.db', timeout=60.0, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA busy_timeout=60000;")
    return c

conn = get_db()
memory = SqliteSaver(conn=conn)

def db_retry(func, *args, **kwargs):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(0.4 * (attempt + 1))
                continue
            raise e

graph = StateGraph(ChatState)

graph.add_node("chat_node", chat_node)

graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

# Compile with persistence
workflow = graph.compile(checkpointer=memory)
thread_id = "1"
config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
workflow.get_state(config)
def retrieve_all_threads():
    all_threads = set()

    for checkpoint in memory.list(None):
        all_threads.add(
            checkpoint.config["configurable"]["thread_id"]
        )

    return list(all_threads)

import hashlib
import secrets
from datetime import datetime

def init_user_db():
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            provider TEXT DEFAULT 'local',
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            user_email TEXT NOT NULL,
            user_name TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_path TEXT,
            size_bytes INTEGER DEFAULT 0,
            subject TEXT DEFAULT 'General',
            semester TEXT DEFAULT 'Semester 1'
        )
    """)
    # Migration helper for existing table
    try:
        cursor.execute("ALTER TABLE user_uploads ADD COLUMN subject TEXT DEFAULT 'General'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE user_uploads ADD COLUMN semester TEXT DEFAULT 'Semester 1'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE user_uploads ADD COLUMN file_type TEXT DEFAULT 'Notes'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE user_uploads ADD COLUMN exam_type TEXT DEFAULT 'Other'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE user_uploads ADD COLUMN is_private INTEGER DEFAULT 0")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN contribution_score INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN current_streak INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_active_date TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN has_seen_onboarding INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 1")
    except Exception:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reported_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            reporter_email TEXT,
            reporter_name TEXT,
            reason TEXT NOT NULL,
            notes TEXT,
            reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp_code TEXT NOT NULL,
            otp_type TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            is_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT NOT NULL,
            action_type TEXT NOT NULL,
            attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            user_email TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            is_shared INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            shared_by_user_id INTEGER NOT NULL,
            shared_with_user_id INTEGER,
            permission_type TEXT DEFAULT 'view',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    try: cursor.execute("ALTER TABLE documents ADD COLUMN user_id INTEGER DEFAULT 1")
    except Exception: pass
    try: cursor.execute("ALTER TABLE documents ADD COLUMN user_email TEXT")
    except Exception: pass
    try: cursor.execute("ALTER TABLE documents ADD COLUMN title TEXT")
    except Exception: pass
    try: cursor.execute("ALTER TABLE documents ADD COLUMN content TEXT")
    except Exception: pass
    try: cursor.execute("ALTER TABLE documents ADD COLUMN is_shared INTEGER DEFAULT 0")
    except Exception: pass
    try: cursor.execute("ALTER TABLE documents ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except Exception: pass
    try: cursor.execute("ALTER TABLE documents ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except Exception: pass

    conn.commit()

init_user_db()

def hash_password(password: str, email: str = "") -> str:
    user_salt = f"college_freshers_{email.strip().lower()}_2026_salt"
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        user_salt.encode('utf-8'),
        120000
    ).hex()

def verify_password(password: str, hashed: str, email: str = "") -> bool:
    if not password or not hashed:
        return False
    if hash_password(password, email) == hashed:
        return True
    legacy_salt = "college_freshers_salt_2026"
    legacy_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), legacy_salt.encode('utf-8'), 100000).hex()
    return legacy_hash == hashed

import re
import random
from datetime import datetime, timedelta

def validate_password_strength(password: str) -> tuple[bool, str]:
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number (0-9)."
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        return False, "Password must contain at least one special character (!@#$%^&*)."
    return True, "Valid"

def check_login_lockout(email: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
    email = email.strip().lower()
    window_start = (datetime.utcnow() - timedelta(minutes=window_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM auth_rate_limits
        WHERE lower(identifier) = ? AND action_type = 'login_failed' AND attempt_time > ?
    """, (email, window_start))
    count = cursor.fetchone()[0]
    return count >= max_attempts

def record_failed_login(email: str):
    email = email.strip().lower()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    def _do():
        with get_db() as c:
            c.execute("INSERT INTO auth_rate_limits (identifier, action_type, attempt_time) VALUES (?, 'login_failed', ?)", (email, now_str))
            c.commit()
    db_retry(_do)

def clear_failed_logins(email: str):
    email = email.strip().lower()
    def _do():
        with get_db() as c:
            c.execute("DELETE FROM auth_rate_limits WHERE lower(identifier) = ? AND action_type = 'login_failed'", (email,))
            c.commit()
    db_retry(_do)

def create_user(name: str, email: str, password: str = None, provider: str = "local", avatar_url: str = None, is_verified: bool = True):
    email = email.strip().lower()
    name = name.strip()
    pwd_hash = hash_password(password, email) if password else None
    if not avatar_url:
        avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={email}"
    
    today_date = datetime.now().strftime("%Y-%m-%d")
    verified_val = 1 if is_verified else 0
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, provider, avatar_url, contribution_score, current_streak, last_active_date, has_seen_onboarding, is_verified) VALUES (?, ?, ?, ?, ?, 0, 1, ?, 0, ?)",
        (name, email, pwd_hash, provider, avatar_url, today_date, verified_val)
    )
    conn.commit()
    return get_user_by_email(email)

def get_user_by_email(email: str):
    if not email:
        return None
    email = email.strip().lower()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, password_hash, provider, avatar_url, created_at,
               COALESCE(contribution_score, 0), COALESCE(current_streak, 0), last_active_date,
               COALESCE(has_seen_onboarding, 0), COALESCE(is_verified, 1)
        FROM users WHERE lower(email) = ?
    """, (email,))
    row = cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "password_hash": row[3],
            "provider": row[4],
            "avatar_url": row[5],
            "created_at": row[6],
            "contribution_score": row[7],
            "current_streak": row[8],
            "last_active_date": row[9],
            "has_seen_onboarding": bool(row[10]),
            "is_verified": bool(row[11])
        }
    return None

def create_otp(email: str, otp_type: str = "forgot_password", expiry_minutes: int = 10) -> str:
    email = email.strip().lower()
    otp_code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    
    def _do():
        with get_db() as c:
            c.execute(
                "INSERT INTO password_otps (email, otp_code, otp_type, expires_at, is_used) VALUES (?, ?, ?, ?, 0)",
                (email, otp_code, otp_type, expires_at.strftime("%Y-%m-%d %H:%M:%S"))
            )
            c.commit()
    db_retry(_do)
    return otp_code

def verify_otp_code(email: str, otp_code: str, otp_type: str = "forgot_password") -> bool:
    email = email.strip().lower()
    otp_code = otp_code.strip()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM password_otps 
        WHERE lower(email) = ? AND otp_code = ? AND otp_type = ? AND is_used = 0 AND expires_at > ?
        ORDER BY id DESC LIMIT 1
    """, (email, otp_code, otp_type, now_str))
    row = cursor.fetchone()
    if row:
        otp_id = row[0]
        def _do():
            with get_db() as c:
                c.execute("UPDATE password_otps SET is_used = 1 WHERE id = ?", (otp_id,))
                c.commit()
        db_retry(_do)
        return True
    return False

def update_user_password(email: str, new_password: str) -> bool:
    email = email.strip().lower()
    pwd_hash = hash_password(new_password, email)
    def _do():
        with get_db() as c:
            c.execute("UPDATE users SET password_hash = ?, is_verified = 1 WHERE lower(email) = ?", (pwd_hash, email))
            c.commit()
    db_retry(_do)
    return True

def mark_user_verified(email: str):
    email = email.strip().lower()
    def _do():
        with get_db() as c:
            c.execute("UPDATE users SET is_verified = 1 WHERE lower(email) = ?", (email,))
            c.commit()
    db_retry(_do)

def check_rate_limit(identifier: str, action_type: str, max_attempts: int, window_minutes: int) -> bool:
    identifier = identifier.strip().lower()
    window_start = (datetime.utcnow() - timedelta(minutes=window_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM auth_rate_limits
        WHERE lower(identifier) = ? AND action_type = ? AND attempt_time > ?
    """, (identifier, action_type, window_start))
    count = cursor.fetchone()[0]
    return count < max_attempts

def record_rate_limit_attempt(identifier: str, action_type: str):
    identifier = identifier.strip().lower()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    def _do():
        with get_db() as c:
            c.execute("INSERT INTO auth_rate_limits (identifier, action_type, attempt_time) VALUES (?, ?, ?)", (identifier, action_type, now_str))
            c.commit()
    db_retry(_do)

def mark_onboarding_completed(email: str):
    if not email:
        return
    email = email.strip().lower()
    def _do():
        with get_db() as c:
            c.execute("UPDATE users SET has_seen_onboarding = 1 WHERE lower(email) = ?", (email,))
            c.commit()
    db_retry(_do)

def update_user_activity(email: str):
    if not email:
        return None
    email = email.strip().lower()
    user = get_user_by_email(email)
    if not user:
        return None

    today_date = datetime.now().strftime("%Y-%m-%d")
    last_date = user.get("last_active_date")
    current_streak = user.get("current_streak", 0)

    if last_date == today_date:
        return user

    if last_date:
        try:
            today_dt = datetime.strptime(today_date, "%Y-%m-%d")
            last_dt = datetime.strptime(last_date, "%Y-%m-%d")
            days_diff = (today_dt - last_dt).days
            if days_diff == 1:
                current_streak += 1
            else:
                current_streak = 1
        except Exception:
            current_streak = 1
    else:
        current_streak = 1

    def _do():
        with get_db() as c:
            c.execute("""
                UPDATE users 
                SET current_streak = ?, last_active_date = ?
                WHERE lower(email) = ?
            """, (current_streak, today_date, email))
            c.commit()
    db_retry(_do)

    return get_user_by_email(email)

def add_contribution_points(email: str, points: int):
    if not email or points <= 0 or email.lower().strip() == "anonymous@college.edu":
        return
    email = email.strip().lower()
    
    user = get_user_by_email(email)
    if not user:
        return

    def _do():
        with get_db() as c:
            c.execute("""
                UPDATE users 
                SET contribution_score = COALESCE(contribution_score, 0) + ?
                WHERE lower(email) = ?
            """, (points, email))
            c.commit()
    db_retry(_do)

def get_top_contributors(limit: int = 10):
    with get_db() as c:
        cursor = c.cursor()
        cursor.execute("""
            SELECT name, avatar_url, COALESCE(contribution_score, 0) as score, COALESCE(current_streak, 0) as streak
            FROM users
            WHERE lower(email) != 'anonymous@college.edu'
            ORDER BY score DESC, streak DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        leaderboard = []
        for r in rows:
            leaderboard.append({
                "name": r[0],
                "avatar_url": r[1] or f"https://api.dicebear.com/7.x/bottts/svg?seed={r[0]}",
                "contribution_score": r[2],
                "current_streak": r[3]
            })
        return leaderboard

def record_upload(filename: str, user_email: str, user_name: str, file_path: str, size_bytes: int = 0, subject: str = "General Engineering", semester: str = "Semester 1", file_type: str = "Notes", exam_type: str = "Other", is_private: int = 0):
    def _do():
        with get_db() as c:
            c.execute("""
                INSERT OR REPLACE INTO user_uploads (filename, user_email, user_name, uploaded_at, file_path, size_bytes, subject, semester, file_type, exam_type, is_private)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (filename, user_email, user_name, datetime.now().isoformat(), file_path, size_bytes, subject, semester, file_type, exam_type, is_private))
            c.commit()
    db_retry(_do)

def get_file_uploads_metadata():
    with get_db() as c:
        cursor = c.cursor()
        cursor.execute("SELECT filename, user_email, user_name, uploaded_at, size_bytes, subject, semester, file_type, exam_type, is_private FROM user_uploads")
        rows = cursor.fetchall()
        result = {}
        for r in rows:
            result[r[0]] = {
                "filename": r[0],
                "user_email": r[1],
                "user_name": r[2],
                "uploaded_at": r[3],
                "size_bytes": r[4],
                "subject": r[5] if len(r) > 5 and r[5] else "General Engineering",
                "semester": r[6] if len(r) > 6 and r[6] else "Semester 1",
                "file_type": r[7] if len(r) > 7 and r[7] else "Notes",
                "exam_type": r[8] if len(r) > 8 and r[8] else "Other",
                "is_private": r[9] if len(r) > 9 and r[9] is not None else 0
            }
        return result

def delete_upload_record(filename: str):
    def _do():
        with get_db() as c:
            c.execute("DELETE FROM user_uploads WHERE filename = ?", (filename,))
            c.commit()
    db_retry(_do)

def get_upload_by_filename(filename: str):
    with get_db() as c:
        cursor = c.cursor()
        cursor.execute("SELECT filename, user_email, user_name, uploaded_at, size_bytes, subject, semester, file_type, exam_type, is_private FROM user_uploads WHERE lower(filename) = lower(?)", (filename,))
        row = cursor.fetchone()
        if row:
            return {
                "filename": row[0],
                "user_email": row[1],
                "user_name": row[2],
                "uploaded_at": row[3],
                "size_bytes": row[4],
                "subject": row[5] if len(row) > 5 and row[5] else "General Engineering",
                "semester": row[6] if len(row) > 6 and row[6] else "Semester 1",
                "file_type": row[7] if len(row) > 7 and row[7] else "Notes",
                "exam_type": row[8] if len(row) > 8 and row[8] else "Other",
                "is_private": row[9] if len(row) > 9 and row[9] is not None else 0
            }
        return None

def record_report(filename: str, reporter_email: str = "anonymous@college.edu", reporter_name: str = "Anonymous Student", reason: str = "Inappropriate", notes: str = ""):
    def _do():
        with get_db() as c:
            c.execute("""
                INSERT INTO reported_files (filename, reporter_email, reporter_name, reason, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (filename, reporter_email, reporter_name, reason, notes))
            c.commit()
    db_retry(_do)

def get_reported_files():
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, reporter_email, reporter_name, reason, notes, reported_at, status FROM reported_files ORDER BY id DESC")
    rows = cursor.fetchall()
    return [
        {
            "id": r[0],
            "filename": r[1],
            "reporter_email": r[2],
            "reporter_name": r[3],
            "reason": r[4],
            "notes": r[5],
            "reported_at": r[6],
            "status": r[7]
        }
        for r in rows
    ]

# ----------------------------------------------------
# Document Management (Private & Shared Library)
# ----------------------------------------------------

def create_document(user_id: int, user_email: str, title: str, content: str, is_shared: bool = False) -> dict:
    user_email = user_email.strip().lower()
    is_shared_val = 1 if is_shared else 0
    now_str = datetime.now().isoformat()
    def _do():
        with get_db() as c:
            cur = c.cursor()
            cur.execute("""
                INSERT INTO documents (user_id, user_email, title, content, is_shared, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, user_email, title, content, is_shared_val, now_str, now_str))
            c.commit()
            return cur.lastrowid
    doc_id = db_retry(_do)
    return get_document_by_id(doc_id)

def get_document_by_id(doc_id: int) -> dict:
    with get_db() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT d.id, d.user_id, d.user_email, d.title, d.content, d.is_shared, d.created_at, d.updated_at, COALESCE(u.name, 'Student') as owner_name
            FROM documents d
            LEFT JOIN users u ON lower(d.user_email) = lower(u.email)
            WHERE d.id = ?
        """, (doc_id,))
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "user_email": row[2],
                "title": row[3],
                "content": row[4] or "",
                "is_shared": bool(row[5]),
                "created_at": row[6],
                "updated_at": row[7],
                "owner_name": row[8]
            }
        return None

def get_user_documents(user_email: str) -> list:
    if not user_email:
        return []
    with get_db() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT d.id, d.user_id, d.user_email, d.title, d.content, d.is_shared, d.created_at, d.updated_at, COALESCE(u.name, 'Student') as owner_name
            FROM documents d
            LEFT JOIN users u ON lower(d.user_email) = lower(u.email)
            WHERE lower(d.user_email) = lower(?)
            ORDER BY d.id DESC
        """, (user_email.strip(),))
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "user_id": r[1],
                "user_email": r[2],
                "title": r[3],
                "content": r[4] or "",
                "is_shared": bool(r[5]),
                "created_at": r[6],
                "updated_at": r[7],
                "owner_name": r[8]
            }
            for r in rows
        ]

def get_shared_documents() -> list:
    with get_db() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT d.id, d.user_id, d.user_email, d.title, d.content, d.is_shared, d.created_at, d.updated_at, COALESCE(u.name, 'Student') as owner_name
            FROM documents d
            LEFT JOIN users u ON lower(d.user_email) = lower(u.email)
            WHERE d.is_shared = 1
            ORDER BY d.id DESC
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "user_id": r[1],
                "user_email": r[2],
                "title": r[3],
                "content": r[4] or "",
                "is_shared": bool(r[5]),
                "created_at": r[6],
                "updated_at": r[7],
                "owner_name": r[8]
            }
            for r in rows
        ]

def update_document_record(doc_id: int, user_email: str, title: str, content: str, is_shared: bool):
    doc = get_document_by_id(doc_id)
    if not doc:
        return None
    if doc["user_email"].lower() != user_email.lower():
        return "FORBIDDEN"
    is_shared_val = 1 if is_shared else 0
    now_str = datetime.now().isoformat()
    def _do():
        with get_db() as c:
            c.execute("""
                UPDATE documents
                SET title = ?, content = ?, is_shared = ?, updated_at = ?
                WHERE id = ?
            """, (title, content, is_shared_val, now_str, doc_id))
            c.commit()
    db_retry(_do)
    return get_document_by_id(doc_id)

def delete_document_record(doc_id: int, user_email: str):
    doc = get_document_by_id(doc_id)
    if not doc:
        return None
    if doc["user_email"].lower() != user_email.lower():
        return "FORBIDDEN"
    def _do():
        with get_db() as c:
            c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            c.commit()
    db_retry(_do)
    return True

def toggle_document_share_record(doc_id: int, user_email: str, is_shared: bool):
    doc = get_document_by_id(doc_id)
    if not doc:
        return None
    if doc["user_email"].lower() != user_email.lower():
        return "FORBIDDEN"
    is_shared_val = 1 if is_shared else 0
    now_str = datetime.now().isoformat()
    def _do():
        with get_db() as c:
            c.execute("UPDATE documents SET is_shared = ?, updated_at = ? WHERE id = ?", (is_shared_val, now_str, doc_id))
            c.commit()
    db_retry(_do)
    return get_document_by_id(doc_id)