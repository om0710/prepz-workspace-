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
    conn.commit()

init_user_db()

def hash_password(password: str) -> str:
    salt = "college_freshers_salt_2026"
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_user(name: str, email: str, password: str = None, provider: str = "local", avatar_url: str = None):
    email = email.strip().lower()
    name = name.strip()
    pwd_hash = hash_password(password) if password else None
    if not avatar_url:
        avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={email}"
    
    today_date = datetime.now().strftime("%Y-%m-%d")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, provider, avatar_url, contribution_score, current_streak, last_active_date, has_seen_onboarding) VALUES (?, ?, ?, ?, ?, 0, 1, ?, 0)",
        (name, email, pwd_hash, provider, avatar_url, today_date)
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
               COALESCE(has_seen_onboarding, 0)
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
            "has_seen_onboarding": bool(row[10])
        }
    return None

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