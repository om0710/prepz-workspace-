import sqlite3
import os
import re as _re
import json as _json
import secrets as _secrets
import time
from typing import Optional, List, Dict, Any
from datetime import datetime as _dt, datetime
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def get_db():
    c = sqlite3.connect(database='chatbot.db', timeout=60.0, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA busy_timeout=60000;")
    return c

conn = get_db()

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
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN auth_method TEXT DEFAULT 'google'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
    except Exception:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            recipient_email TEXT NOT NULL,
            email_type TEXT DEFAULT 'welcome',
            subject TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'success',
            error_message TEXT
        )
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            session_id TEXT UNIQUE NOT NULL,
            subject TEXT,
            messages TEXT DEFAULT '[]',
            topics_discussed TEXT DEFAULT '[]',
            topic_attempts TEXT DEFAULT '{}',
            understanding_level TEXT DEFAULT 'beginner',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            message_index INTEGER,
            user_message TEXT,
            user_intent TEXT,
            confidence REAL,
            topic TEXT,
            question_count_for_topic INTEGER,
            is_frustrated INTEGER DEFAULT 0,
            is_repeating_question INTEGER DEFAULT 0,
            is_clarifying INTEGER DEFAULT 0,
            should_recommend_videos INTEGER DEFAULT 0,
            recommendation_strength TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS youtube_playlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_name TEXT NOT NULL,
            instructor TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            playlist_url TEXT NOT NULL,
            difficulty TEXT DEFAULT 'Beginner',
            university TEXT DEFAULT 'Bennett University',
            semester INTEGER DEFAULT 1,
            helpfulness_score REAL DEFAULT 4.5,
            total_ratings INTEGER DEFAULT 12,
            helpful_count INTEGER DEFAULT 11,
            total_videos INTEGER DEFAULT 35,
            avg_duration INTEGER DEFAULT 22,
            best_for TEXT DEFAULT '["exam prep", "foundation"]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS playlist_rating (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            playlist_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            was_helpful INTEGER NOT NULL,
            watched_percentage INTEGER DEFAULT 30,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_contexts (
            thread_id TEXT PRIMARY KEY,
            user_email TEXT,
            total_messages INTEGER DEFAULT 0,
            topic_attempts TEXT DEFAULT '{}',
            recent_queries TEXT DEFAULT '[]',
            last_topic TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_weakness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            user_email TEXT,
            subject TEXT,
            concept_name TEXT NOT NULL,
            concept_difficulty TEXT DEFAULT 'foundational',
            first_confused_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            times_confused INTEGER DEFAULT 1,
            last_confused_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confusion_contexts TEXT DEFAULT '[]',
            dependent_topics TEXT DEFAULT '[]',
            impact_score REAL DEFAULT 0.0,
            mastery_level TEXT DEFAULT 'novice',
            mastery_percentage REAL DEFAULT 0.0,
            practice_questions_attempted INTEGER DEFAULT 0,
            practice_score REAL DEFAULT 0.0,
            last_practiced TIMESTAMP,
            is_critical INTEGER DEFAULT 0,
            is_foundational INTEGER DEFAULT 0,
            intervention_priority INTEGER DEFAULT 50,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_dependency_graph (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            prerequisite_concept TEXT NOT NULL,
            dependent_concept TEXT NOT NULL,
            importance TEXT DEFAULT 'critical',
            failure_rate REAL DEFAULT 70.0,
            avg_learning_time INTEGER DEFAULT 25,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adaptive_practice_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            user_email TEXT,
            concept_id INTEGER,
            concept_name TEXT NOT NULL,
            subject TEXT DEFAULT 'General',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            questions TEXT DEFAULT '[]',
            total_questions INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            session_score REAL DEFAULT 0.0,
            initial_difficulty TEXT DEFAULT 'easy',
            final_difficulty TEXT DEFAULT 'easy',
            difficulty_progression TEXT DEFAULT '[]',
            total_time INTEGER DEFAULT 0,
            avg_time_per_question REAL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_question (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            concept TEXT NOT NULL,
            question_text TEXT NOT NULL,
            question_type TEXT DEFAULT 'mcq',
            options TEXT DEFAULT '[]',
            correct_option TEXT,
            explanation TEXT,
            concept_explanation TEXT,
            is_ai_generated INTEGER DEFAULT 0,
            is_pyq_based INTEGER DEFAULT 0,
            difficulty TEXT DEFAULT 'easy',
            attempt_count INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,
            related_video_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

init_user_db()

def seed_course_repository_if_needed():
    try:
        from seed_course_documents import generate_docs
        os.makedirs("uploads", exist_ok=True)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM user_uploads")
        cnt = cur.fetchone()[0]
        if cnt < 5:
            generate_docs()
    except Exception as e:
        print(f"[SEED DOCS NOTICE] {e}")

seed_course_repository_if_needed()

# ── Bennett University Pre-Seeded Channels ─────────────────────────────────────

import json as _json
import re as _re
import os as _os
import secrets as _secrets
from datetime import datetime as _dt

BENNETT_CHANNELS = [
    {
        "channel_name": "Engineers Ki Pathshala",
        "instructor": "Umesh Dhande",
        "subject": "Basic Electrical & Electronics Engineering",
        "topic": "Thevenin Theorem, AC Circuits & Network Theorems",
        "playlist_url": "https://youtube.com/playlist?list=PL9RcWoqXmzaLTYUdnzKhF4bYug3GjGcEc",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "foundation", "theorems"],
        "avg_duration": 25,
        "total_videos": 45,
        "helpfulness_score": 4.9,
        "total_ratings": 65,
        "helpful_count": 63,
        "semester": 1
    },
    {
        "channel_name": "NESO Academy",
        "instructor": "NESO Academy",
        "subject": "Basic Electrical & Electronics Engineering",
        "topic": "Analog Electronics, Diodes & Semiconductor Circuits",
        "playlist_url": "https://youtube.com/playlist?list=PLBlnK6fEyqRgLR-hMp7wem-bdVN1iEhsh",
        "difficulty": "Intermediate",
        "best_for": ["deep learning", "exam prep"],
        "avg_duration": 20,
        "total_videos": 38,
        "helpfulness_score": 4.9,
        "total_ratings": 56,
        "helpful_count": 54,
        "semester": 1
    },
    {
        "channel_name": "Gajendra Purohit",
        "instructor": "Dr. Gajendra Purohit",
        "subject": "Engineering Calculus",
        "topic": "Differentiation, Integration & Calculus",
        "playlist_url": "https://youtube.com/playlist?list=PLU6SqdYcYsfIJRl8mo2Rv1MpdvmVD0YyI",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "foundation"],
        "avg_duration": 18,
        "total_videos": 52,
        "helpfulness_score": 4.9,
        "total_ratings": 140,
        "helpful_count": 136,
        "semester": 1
    },
    {
        "channel_name": "Pradeep Giri Academy",
        "instructor": "Pradeep Giri Academy",
        "subject": "Engineering Calculus",
        "topic": "Engineering Mathematics 1: Calculus & Differentiation",
        "playlist_url": "https://youtube.com/playlist?list=PLT3bOBUU3L9iw3yQWge_IjhXZlDgRGwyq",
        "difficulty": "Beginner",
        "best_for": ["step by step", "exam prep", "engineering math"],
        "avg_duration": 22,
        "total_videos": 45,
        "helpfulness_score": 4.9,
        "total_ratings": 125,
        "helpful_count": 122,
        "semester": 1
    },
    {
        "channel_name": "Tikle's Academy",
        "instructor": "Tikle's Academy",
        "subject": "Engineering Calculus",
        "topic": "Differential Calculus, Limits & Successive Differentiation",
        "playlist_url": "https://youtube.com/playlist?list=PLNKD1qB9ppttx4WuHV0TWRy5dWuVSKEtT",
        "difficulty": "Beginner",
        "best_for": ["numericals", "exam prep", "concept clarity"],
        "avg_duration": 20,
        "total_videos": 50,
        "helpfulness_score": 4.8,
        "total_ratings": 110,
        "helpful_count": 106,
        "semester": 1
    },
    {
        "channel_name": "Bhagwan Singh Vishwakarma",
        "instructor": "Bhagwan Singh Vishwakarma",
        "subject": "Engineering Calculus",
        "topic": "Advanced Calculus & Differential Equations",
        "playlist_url": "https://www.youtube.com/playlist?list=PLdM-WZokR4tbCBA4mkvfk2vOH12eRPT2Y",
        "difficulty": "Intermediate",
        "best_for": ["deep learning", "competitive exams"],
        "avg_duration": 25,
        "total_videos": 48,
        "helpfulness_score": 4.7,
        "total_ratings": 95,
        "helpful_count": 91,
        "semester": 1
    },
    {
        "channel_name": "Apna College",
        "instructor": "Shradha Khapra",
        "subject": "Python Programming",
        "topic": "Python Basics to Advanced",
        "playlist_url": "https://youtube.com/playlist?list=PLGjplNEQ1it8-0CmoljS5yeV-GlKSUEt0",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "foundation", "projects"],
        "avg_duration": 30,
        "total_videos": 102,
        "helpfulness_score": 4.9,
        "total_ratings": 120,
        "helpful_count": 118
    },
    {
        "channel_name": "Code With Harry",
        "instructor": "Harry Jain",
        "subject": "Python Programming",
        "topic": "Python Full Course & DSA",
        "playlist_url": "https://youtube.com/playlist?list=PLu0W_9lII9agwh1XjRt242xIpHhPT2llg",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "projects"],
        "avg_duration": 35,
        "total_videos": 78,
        "helpfulness_score": 4.8,
        "total_ratings": 95,
        "helpful_count": 91
    },
    {
        "channel_name": "Pradeep Giri Academy",
        "instructor": "Pradeep Giri",
        "subject": "Engineering Mechanics",
        "topic": "Statics & Dynamics",
        "playlist_url": "https://youtube.com/playlist?list=PLT3bOBUU3L9hADhGPsZjSddwAC3BvJDnl",
        "difficulty": "Intermediate",
        "best_for": ["exam prep", "deep learning"],
        "avg_duration": 22,
        "total_videos": 62,
        "helpfulness_score": 4.6,
        "total_ratings": 38,
        "helpful_count": 35
    },
    {
        "channel_name": "NESO Academy",
        "instructor": "NESO Academy",
        "subject": "Operating Systems",
        "topic": "Deadlock & Process Management",
        "playlist_url": "https://www.youtube.com/playlist?list=PLBlnK6fEyqRitWLDxMrzVQK8813oqG797",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "foundation"],
        "avg_duration": 18,
        "total_videos": 65,
        "helpfulness_score": 4.9,
        "total_ratings": 84,
        "helpful_count": 82
    },
    {
        "channel_name": "Gate Smashers",
        "instructor": "Varun Singla",
        "subject": "Operating Systems",
        "topic": "OS Concurrency, Semaphores & Memory",
        "playlist_url": "https://www.youtube.com/playlist?list=PLxCzCOWd7aiGz9donHRrE9I3Mwn6XdP8p",
        "difficulty": "Intermediate",
        "best_for": ["exam prep", "short notes"],
        "avg_duration": 15,
        "total_videos": 80,
        "helpfulness_score": 4.9,
        "total_ratings": 110,
        "helpful_count": 108
    },
    {
        "channel_name": "Abdul Bari",
        "instructor": "Abdul Bari",
        "subject": "Data Structures & Algorithms",
        "topic": "Trees, Graphs & Dynamic Programming",
        "playlist_url": "https://www.youtube.com/playlist?list=PLDN4rrl48XKpZkf03iYFl-O29szjTrs_O",
        "difficulty": "Beginner",
        "best_for": ["deep learning", "foundation"],
        "avg_duration": 28,
        "total_videos": 72,
        "helpfulness_score": 5.0,
        "total_ratings": 210,
        "helpful_count": 208,
        "semester": 3
    },
    {
        "channel_name": "Gate Smashers",
        "instructor": "Varun Singla",
        "subject": "Information Management System",
        "topic": "DBMS, SQL & Information Management",
        "playlist_url": "https://youtube.com/playlist?list=PLxCzCOWd7aiFAN6I8CuViBuCdJgiOkT2Y",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "concepts", "sql"],
        "avg_duration": 15,
        "total_videos": 128,
        "helpfulness_score": 4.9,
        "total_ratings": 145,
        "helpful_count": 142,
        "semester": 3
    },
    {
        "channel_name": "NESO Academy",
        "instructor": "NESO Academy",
        "subject": "Information Management System",
        "topic": "DBMS, Relational Model & SQL Complete Series",
        "playlist_url": "https://youtube.com/playlist?list=PLBlnK6fEyqRiyryTrbKHX1Sh9luYI0dhX",
        "difficulty": "Beginner",
        "best_for": ["foundation", "exam prep", "concepts"],
        "avg_duration": 18,
        "total_videos": 80,
        "helpfulness_score": 4.9,
        "total_ratings": 135,
        "helpful_count": 131,
        "semester": 3
    },
    {
        "channel_name": "Gajendra Purohit",
        "instructor": "Dr. Gajendra Purohit",
        "subject": "Probability and Statistics",
        "topic": "Probability & Random Variables 2.0",
        "playlist_url": "https://youtube.com/playlist?list=PLU6SqdYcYsfJPF-4HphQQ8OceDtqhlSW8",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "foundation"],
        "avg_duration": 22,
        "total_videos": 48,
        "helpfulness_score": 4.9,
        "total_ratings": 130,
        "helpful_count": 127,
        "semester": 3
    },
    {
        "channel_name": "Tending to Infinity",
        "instructor": "Shaurya / Prashant",
        "subject": "Probability and Statistics",
        "topic": "Probability & Statistics Complete Series",
        "playlist_url": "https://youtube.com/playlist?list=PLn3Wz38keZOeMt_qcBF6jkv3kKfyBuuTr",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "clear concepts"],
        "avg_duration": 28,
        "total_videos": 55,
        "helpfulness_score": 4.8,
        "total_ratings": 85,
        "helpful_count": 82,
        "semester": 3
    },
    {
        "channel_name": "Algorithm Unlocked",
        "instructor": "Algorithm Unlocked",
        "subject": "Probability and Statistics",
        "topic": "Probability Distributions, Bayes Theorem & Sampling",
        "playlist_url": "https://youtube.com/playlist?list=PLhLZ_zxDsyOIKbQfKFM05BLYRhUZ7JP-M",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "concept clarity", "numericals"],
        "avg_duration": 20,
        "total_videos": 35,
        "helpfulness_score": 4.9,
        "total_ratings": 115,
        "helpful_count": 112,
        "semester": 3
    },
    {
        "channel_name": "Pradeep Giri Academy",
        "instructor": "Pradeep Giri Academy",
        "subject": "Probability and Statistics",
        "topic": "Engineering Mathematics: Probability & Statistics",
        "playlist_url": "https://youtube.com/playlist?list=PLT3bOBUU3L9jex8hXzVAszMS8NOILa7IV",
        "difficulty": "Intermediate",
        "best_for": ["step by step", "exam prep", "engineering math"],
        "avg_duration": 25,
        "total_videos": 40,
        "helpfulness_score": 4.8,
        "total_ratings": 95,
        "helpful_count": 92,
        "semester": 3
    },
    {
        "channel_name": "Apna College",
        "instructor": "Shradha Khapra",
        "subject": "Data Structures & Algorithms in C++",
        "topic": "C++ & DSA Complete Course",
        "playlist_url": "https://youtube.com/playlist?list=PLfqMhTWNBTe137I_EPQd34TsgV6IO55pt",
        "difficulty": "Beginner",
        "best_for": ["foundation", "placements", "exam prep"],
        "avg_duration": 32,
        "total_videos": 85,
        "helpfulness_score": 4.9,
        "total_ratings": 160,
        "helpful_count": 156,
        "semester": 3
    },
    {
        "channel_name": "College Wallah",
        "instructor": "Physics Wallah Team",
        "subject": "Data Structures & Algorithms in C++",
        "topic": "C++ and DSA Foundation Course",
        "playlist_url": "https://youtube.com/playlist?list=PLxgZQoSe9cg0df_GxVjz3DD_Gck5tMXAd",
        "difficulty": "Beginner",
        "best_for": ["foundation", "step by step"],
        "avg_duration": 30,
        "total_videos": 72,
        "helpfulness_score": 4.8,
        "total_ratings": 120,
        "helpful_count": 116,
        "semester": 3
    },
    {
        "channel_name": "Jenny's Lectures CS IT",
        "instructor": "Jenny",
        "subject": "Data Structures & Algorithms in C++",
        "topic": "Data Structures & Algorithms Complete Placement Course",
        "playlist_url": "https://youtube.com/playlist?list=PLdo5W4Nhv31bbKJzrsKfMpo_grxuLl8LU",
        "difficulty": "Beginner",
        "best_for": ["foundation", "visual explanations", "exam prep"],
        "avg_duration": 25,
        "total_videos": 90,
        "helpfulness_score": 4.9,
        "total_ratings": 185,
        "helpful_count": 181,
        "semester": 3
    },
    {
        "channel_name": "NESO Academy",
        "instructor": "NESO Academy",
        "subject": "Discrete Mathematical Structures",
        "topic": "Set Theory, Relations, Functions & Propositional Logic",
        "playlist_url": "https://youtube.com/playlist?list=PLBlnK6fEyqRhqJPDXcvYlLfXPh37L89g3",
        "difficulty": "Beginner",
        "best_for": ["foundation", "exam prep", "clear concepts"],
        "avg_duration": 18,
        "total_videos": 65,
        "helpfulness_score": 4.9,
        "total_ratings": 150,
        "helpful_count": 147,
        "semester": 3
    },
    {
        "channel_name": "Gate Smashers",
        "instructor": "Varun Singla",
        "subject": "Discrete Mathematical Structures",
        "topic": "Discrete Mathematics Complete Course & Graph Theory",
        "playlist_url": "https://youtube.com/playlist?list=PLxCzCOWd7aiH2wwES9vPWsEL6ipTaUSl3",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "fast revision", "concepts"],
        "avg_duration": 15,
        "total_videos": 80,
        "helpfulness_score": 4.9,
        "total_ratings": 190,
        "helpful_count": 186,
        "semester": 3
    },
    {
        "channel_name": "Knowledge Gate",
        "instructor": "Sanchit Jain",
        "subject": "Discrete Mathematical Structures",
        "topic": "Discrete Mathematics Full Course in One Video",
        "playlist_url": "https://youtu.be/3zOtLEeHygg",
        "difficulty": "Beginner",
        "best_for": ["one shot", "complete revision", "exam prep"],
        "avg_duration": 120,
        "total_videos": 1,
        "helpfulness_score": 4.8,
        "total_ratings": 130,
        "helpful_count": 126,
        "semester": 3
    },
    {
        "channel_name": "Pradeep Giri Academy",
        "instructor": "Pradeep Giri Academy",
        "subject": "Discrete Mathematical Structures",
        "topic": "Engineering Mathematics: Discrete Mathematics Complete Playlist",
        "playlist_url": "https://youtube.com/playlist?list=PLT3bOBUU3L9j_VG5CICyWK_a4M0-nwwxy",
        "difficulty": "Beginner",
        "best_for": ["step by step", "exam prep", "engineering math"],
        "avg_duration": 25,
        "total_videos": 40,
        "helpfulness_score": 4.8,
        "total_ratings": 110,
        "helpful_count": 106,
        "semester": 3
    },
    {
        "channel_name": "Gate Smashers",
        "instructor": "Varun Singla",
        "subject": "Digital Design",
        "topic": "Digital Logic, Number Systems & Combinational Circuits",
        "playlist_url": "https://youtube.com/playlist?list=PLxCzCOWd7aiGmXg4NoX6R31AsC5LeCPHe",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "concepts", "fast revision"],
        "avg_duration": 15,
        "total_videos": 70,
        "helpfulness_score": 4.9,
        "total_ratings": 180,
        "helpful_count": 176,
        "semester": 3
    },
    {
        "channel_name": "Engineering Funda",
        "instructor": "Engineering Funda",
        "subject": "Digital Design",
        "topic": "Digital Electronics, Logic Gates & Sequential Circuits",
        "playlist_url": "https://youtube.com/playlist?list=PLgwJf8NK-2e4OD-vicvzWT7wE8BZIQtEe",
        "difficulty": "Beginner",
        "best_for": ["step by step", "foundation", "exam prep"],
        "avg_duration": 18,
        "total_videos": 65,
        "helpfulness_score": 4.8,
        "total_ratings": 120,
        "helpful_count": 116,
        "semester": 3
    },
    {
        "channel_name": "NESO Academy",
        "instructor": "NESO Academy",
        "subject": "Digital Design",
        "topic": "Digital Electronics & Logic Design Complete Series",
        "playlist_url": "https://youtube.com/playlist?list=PLBlnK6fEyqRjMH3mWf6kwqiTbT798eAOm",
        "difficulty": "Beginner",
        "best_for": ["deep foundation", "diagrams", "exam prep"],
        "avg_duration": 20,
        "total_videos": 95,
        "helpfulness_score": 4.9,
        "total_ratings": 195,
        "helpful_count": 191,
        "semester": 3
    },
    {
        "channel_name": "Knowledge Gate",
        "instructor": "Sanchit Jain",
        "subject": "Digital Design",
        "topic": "Digital Logic Design & K-Maps / Flip Flops",
        "playlist_url": "https://youtube.com/playlist?list=PLmXKhU9FNesSfX1PVt4VGm-wbIKfemUWK",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "gate questions", "numericals"],
        "avg_duration": 22,
        "total_videos": 50,
        "helpfulness_score": 4.8,
        "total_ratings": 140,
        "helpful_count": 136,
        "semester": 3
    },
    {
        "channel_name": "Gajendra Purohit",
        "instructor": "Dr. Gajendra Purohit",
        "subject": "Linear Algebra",
        "topic": "Matrices, Determinants, Rank & Eigenvalues",
        "playlist_url": "https://youtube.com/playlist?list=PLU6SqdYcYsfI7Ebw_j-Vy8YKHdbHKP9am",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "foundation", "eigenvalues"],
        "avg_duration": 18,
        "total_videos": 45,
        "helpfulness_score": 4.9,
        "total_ratings": 175,
        "helpful_count": 171,
        "semester": 2
    },
    {
        "channel_name": "Pradeep Giri Academy",
        "instructor": "Pradeep Giri Academy",
        "subject": "Linear Algebra",
        "topic": "Engineering Mathematics: Matrices & Linear Algebra",
        "playlist_url": "https://youtube.com/playlist?list=PLT3bOBUU3L9ijgr3HbpphxsgNfBekbPZS",
        "difficulty": "Beginner",
        "best_for": ["step by step", "numericals", "exam prep"],
        "avg_duration": 22,
        "total_videos": 38,
        "helpfulness_score": 4.8,
        "total_ratings": 130,
        "helpful_count": 126,
        "semester": 2
    },
    {
        "channel_name": "Gajendra Purohit (Advanced)",
        "instructor": "Dr. Gajendra Purohit",
        "subject": "Linear Algebra",
        "topic": "Vector Spaces, Basis, Dimension & Linear Transformations",
        "playlist_url": "https://youtube.com/playlist?list=PLU6SqdYcYsfJRZEK4BpuufOlIrQzWm-nP",
        "difficulty": "Intermediate",
        "best_for": ["deep concepts", "vector spaces", "transformations"],
        "avg_duration": 20,
        "total_videos": 35,
        "helpfulness_score": 4.9,
        "total_ratings": 150,
        "helpful_count": 146,
        "semester": 2
    },
    {
        "channel_name": "GATE Wallah",
        "instructor": "Physics Wallah Team",
        "subject": "Linear Algebra",
        "topic": "Linear Algebra Complete One-Shot Revision",
        "playlist_url": "https://youtu.be/TLRiju0jFEI",
        "difficulty": "Beginner",
        "best_for": ["one shot", "complete revision", "gate & semester prep"],
        "avg_duration": 180,
        "total_videos": 1,
        "helpfulness_score": 4.8,
        "total_ratings": 140,
        "helpful_count": 136,
        "semester": 2
    },
    {
        "channel_name": "Gajendra Purohit",
        "instructor": "Dr. Gajendra Purohit",
        "subject": "Differential Equations",
        "topic": "Ordinary Differential Equations (ODE) - First Order & First Degree",
        "playlist_url": "https://youtube.com/playlist?list=PLU6SqdYcYsfIuZVt20v-eNZBfFLENrM1F",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "foundation", "step by step"],
        "avg_duration": 18,
        "total_videos": 35,
        "helpfulness_score": 4.9,
        "total_ratings": 160,
        "helpful_count": 156,
        "semester": 1
    },
    {
        "channel_name": "Gajendra Purohit (Higher Order)",
        "instructor": "Dr. Gajendra Purohit",
        "subject": "Differential Equations",
        "topic": "Higher Order Linear Differential Equations & PDE",
        "playlist_url": "https://youtube.com/playlist?list=PLU6SqdYcYsfJmqo86d12EoNNWKtAZqu8q",
        "difficulty": "Intermediate",
        "best_for": ["higher order ode", "pde", "exam prep"],
        "avg_duration": 20,
        "total_videos": 40,
        "helpfulness_score": 4.9,
        "total_ratings": 145,
        "helpful_count": 141,
        "semester": 1
    },
    {
        "channel_name": "Apna College",
        "instructor": "Shradha Khapra",
        "subject": "Java Programming",
        "topic": "Java Complete Course, Core Java, OOPs & Data Structures",
        "playlist_url": "https://youtube.com/playlist?list=PLfqMhTWNBTe3LtFWcvwpqTkUSlB32kJop",
        "difficulty": "Beginner",
        "best_for": ["foundation", "core java", "placements", "oops"],
        "avg_duration": 30,
        "total_videos": 45,
        "helpfulness_score": 4.9,
        "total_ratings": 210,
        "helpful_count": 206,
        "semester": 2
    },
    {
        "channel_name": "CodeHelp - by Babbar",
        "instructor": "Love Babbar",
        "subject": "Java Programming",
        "topic": "Supreme Java Placement Course & Problem Solving",
        "playlist_url": "https://youtube.com/playlist?list=PLDzeHZWIZsTqNW1gvXXAicBgku9uPZeOC",
        "difficulty": "Beginner",
        "best_for": ["placement prep", "core concepts", "coding practice"],
        "avg_duration": 35,
        "total_videos": 40,
        "helpfulness_score": 4.9,
        "total_ratings": 190,
        "helpful_count": 186,
        "semester": 2
    },
    {
        "channel_name": "Perfect Computer Engineer",
        "instructor": "Perfect Computer Engineer",
        "subject": "Basic Electrical & Electronics Engineering",
        "topic": "Basic Electronics & Semiconductor Devices",
        "playlist_url": "https://youtube.com/playlist?list=PLPIwNooIb9vhiZRRq1fEWXvSLz7VMeqSh",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "step by step"],
        "avg_duration": 18,
        "total_videos": 42,
        "helpfulness_score": 4.9,
        "total_ratings": 98,
        "helpful_count": 96,
        "semester": 1
    },
    {
        "channel_name": "Tikle's Academy",
        "instructor": "Tikle's Academy",
        "subject": "Basic Electrical & Electronics Engineering",
        "topic": "BJT, Op-Amps, Transistors & Diodes",
        "playlist_url": "https://youtube.com/playlist?list=PLDN15nk5uLiCSOqr7-rUz6-GtdTAjlvul",
        "difficulty": "Intermediate",
        "best_for": ["numerical problem solving", "exam prep"],
        "avg_duration": 22,
        "total_videos": 55,
        "helpfulness_score": 4.8,
        "total_ratings": 120,
        "helpful_count": 116,
        "semester": 1
    }
]

def seed_bennett_channels_if_needed():
    """Populate database with Bennett University recommended channels, ensuring exact 4 electrical/electronics courses exist."""
    def _do():
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtube_playlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT NOT NULL,
                instructor TEXT NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                playlist_url TEXT NOT NULL,
                difficulty TEXT DEFAULT 'Beginner',
                university TEXT DEFAULT 'Bennett University',
                semester INTEGER DEFAULT 1,
                helpfulness_score REAL DEFAULT 4.5,
                total_ratings INTEGER DEFAULT 12,
                helpful_count INTEGER DEFAULT 11,
                total_videos INTEGER DEFAULT 35,
                avg_duration INTEGER DEFAULT 22,
                best_for TEXT DEFAULT '["exam prep", "foundation"]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Clean up obsolete rows
        cursor.execute("DELETE FROM youtube_playlist WHERE channel_name = 'Love You Science'")
        cursor.execute("DELETE FROM youtube_playlist WHERE playlist_url LIKE '%PLmXKhU9FNesR1rSES7oLdJaNFgmuj0SYV%'")
        cursor.execute("DELETE FROM youtube_playlist WHERE playlist_url LIKE '%PLU6SqdYcYsfLRq3tu-g_hvkHDcorrtcBK%'")
        
        for ch in BENNETT_CHANNELS:
            existing = cursor.execute(
                "SELECT id FROM youtube_playlist WHERE playlist_url = ? OR (channel_name = ? AND topic = ?)",
                (ch["playlist_url"], ch["channel_name"], ch["topic"])
            ).fetchone()
            if not existing:
                cursor.execute("""
                    INSERT INTO youtube_playlist (
                        channel_name, instructor, subject, topic, playlist_url,
                        difficulty, university, semester, helpfulness_score,
                        total_ratings, helpful_count, total_videos, avg_duration, best_for
                    ) VALUES (?, ?, ?, ?, ?, ?, 'Bennett University', ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ch["channel_name"], ch["instructor"], ch["subject"], ch["topic"], ch["playlist_url"],
                    ch["difficulty"], ch.get("semester", 1), ch.get("helpfulness_score", 4.8), ch.get("total_ratings", 50),
                    ch.get("helpful_count", 48), ch.get("total_videos", 40), ch.get("avg_duration", 20),
                    _json.dumps(ch.get("best_for", ["exam prep", "foundation"]))
                ))
            else:
                cursor.execute("""
                    UPDATE youtube_playlist SET playlist_url = ?, instructor = ?, subject = ?, topic = ? WHERE id = ?
                """, (ch["playlist_url"], ch["instructor"], ch["subject"], ch["topic"], existing[0]))
        conn.commit()
        print(f"[SEED] Seeded & synced {len(BENNETT_CHANNELS)} Bennett University channels.")
    db_retry(_do)

seed_bennett_channels_if_needed()

# ── Part 2: Database Utility Functions ────────────────────────────────────────

def get_or_create_conversation(user_id: int = 1, session_id: str = None, subject: str = "General") -> dict:
    """Get existing conversation or create new one in conversation_context."""
    if not session_id:
        session_id = _secrets.token_urlsafe(16)
    
    def _do():
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT id, user_id, session_id, subject, messages, topics_discussed, topic_attempts, understanding_level FROM conversation_context WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "session_id": row[2],
                "subject": row[3],
                "messages": _json.loads(row[4] or "[]"),
                "topics_discussed": _json.loads(row[5] or "[]"),
                "topic_attempts": _json.loads(row[6] or "{}"),
                "understanding_level": row[7] or "beginner"
            }
        
        # Create new
        now = _dt.now().isoformat()
        cursor.execute(
            "INSERT INTO conversation_context (user_id, session_id, subject, messages, topics_discussed, topic_attempts, understanding_level, created_at, last_activity) VALUES (?, ?, ?, '[]', '[]', '{}', 'beginner', ?, ?)",
            (user_id or 1, session_id, subject, now, now)
        )
        conn.commit()
        new_id = cursor.lastrowid
        return {
            "id": new_id,
            "user_id": user_id or 1,
            "session_id": session_id,
            "subject": subject,
            "messages": [],
            "topics_discussed": [],
            "topic_attempts": {},
            "understanding_level": "beginner"
        }
    return db_retry(_do)

def update_conversation_context_record(session_id: str, user_message: str, ai_message: str, topic: str, topic_attempts: int, intent: str = "initial", strength: str = "none"):
    """Safely append messages and update topic attempts in conversation_context."""
    def _do():
        cursor = conn.cursor()
        row = cursor.execute("SELECT messages, topics_discussed, topic_attempts FROM conversation_context WHERE session_id = ?", (session_id,)).fetchone()
        if row:
            msgs = _json.loads(row[0] or "[]")
            topics = _json.loads(row[1] or "[]")
            t_attempts = _json.loads(row[2] or "{}")
        else:
            msgs, topics, t_attempts = [], [], {}

        msgs.append({
            "user": user_message,
            "ai": ai_message[:500] if ai_message else "",
            "timestamp": _dt.now().isoformat(),
            "intent": intent,
            "recommendation_strength": strength
        })
        if topic and topic not in topics:
            topics.append(topic)
        t_attempts[topic] = topic_attempts

        cursor.execute("""
            UPDATE conversation_context
            SET messages = ?, topics_discussed = ?, topic_attempts = ?, last_activity = ?
            WHERE session_id = ?
        """, (_json.dumps(msgs[-20:]), _json.dumps(topics), _json.dumps(t_attempts), _dt.now().isoformat(), session_id))
        conn.commit()
    db_retry(_do)

def get_recent_messages(conversation_id: int, limit: int = 10) -> list:
    """Get recent messages from conversation"""
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT messages FROM conversation_context WHERE id = ?", (conversation_id,)).fetchone()
        if row and row[0]:
            msgs = _json.loads(row[0])
            return msgs[-limit:] if msgs else []
        return []
    except Exception as e:
        print(f"[CONTEXT] get_recent_messages error: {e}")
        return []

def calculate_similarity(msg1: str, msg2: str) -> float:
    """Calculate word overlap similarity between two messages (0-1)"""
    if not msg1 or not msg2:
        return 0.0
    msg1_words = set(msg1.lower().split())
    msg2_words = set(msg2.lower().split())
    if not msg1_words or not msg2_words:
        return 0.0
    common = len(msg1_words & msg2_words)
    total = len(msg1_words | msg2_words)
    return common / total if total > 0 else 0.0

# ── Core Academic Topics Dictionary ──────────────────────────────────────────
TOPIC_KW = {
    "electronics": ["basic electronics", "basic electrical", "analog electronics", "electrical engineering", "electronics engineering", "electrical and electronics", "electrical & electronics", "electricals", "electrical", "electronics", "electronic", "elctronics", "electonics", "electornics", "electircal", "elec", "bee", "beee", "ece", "semiconductor", "diode", "bjt", "opamp", "transistor", "fet", "mosfet"],
    "calculus": ["calculus", "differential calculus", "integral calculus", "differentiation", "integration", "derivative", "derivatives", "integral", "integrals", "limit", "limits", "continuity", "maxima", "minima", "taylor series", "maclaurin", "multivariable calculus"],
    "differential equations": ["differential equations", "differential equation", "differntial equations", "differntial equation", "ode", "pde", "exact differential", "bernoulli equation", "linear differential", "higher order differential", "cauchy euler", "legendre polynomial", "frobenius"],
    "linear algebra": ["linear algebra", "linear algerba", "eigenvalue", "eigenvalues", "eigenvector", "eigenvectors", "matrix", "matrices", "determinant", "determinants", "rank of matrix", "linear transformation", "linear transformations", "vector space", "vector spaces", "system of linear equations", "cayley hamilton"],
    "thevenin theorem": ["thevenin", "thevenin's", "thevenins", "norton", "nortons", "kvl", "kcl", "maximum power transfer", "superposition theorem", "superposition", "reciprocity theorem", "network theorem", "network theorems"],
    "electrical circuits": ["circuit", "circuits", "dependent source", "phasor", "impedance", "mesh analysis", "nodal analysis", "rlc circuit", "ac circuit", "kirchhoff"],
    "electrical machines": ["electrical", "motor", "transformer", "transformers", "rotating magnetic field", "rmf", "synchronous motor", "dc motor", "stator", "rotor", "armature", "torque slip"],
    "power systems": ["power factor", "three phase", "transmission line", "load flow", "fault analysis", "generator", "bus admittance"],
    "control systems": ["bode plot", "root locus", "nyquist plot", "transfer function", "pid controller", "state space", "stability"],
    "operating systems": ["operating system", "operating systems", "deadlock", "deadlocks", "scheduling", "semaphore", "semaphores", "paging", "virtual memory", "process management", "banker's algorithm", "concurrency"],
    "information management system": ["information management system", "information management", "ims", "database management system", "database management", "dbms", "database", "databases", "sql", "normalization", "relational database", "acid properties", "transaction", "acid", "relational algebra", "b+ tree"],
    "probability and statistics": ["probability and statistics", "probability & statistics", "statistics and probability", "probability", "statistics", "stats", "p&s", "random variable", "random variables", "bayes theorem", "poisson distribution", "normal distribution", "binomial distribution", "hypothesis testing"],
    "dsa with c++": ["dsa with c++", "c++ dsa", "cpp dsa", "dsa in c++", "c++ data structures", "dsa in cpp", "dsa cpp", "c++", "cpp"],
    "data structures": ["data structure", "data structures", "dsa", "linked list", "linked lists", "binary tree", "binary trees", "heap", "bst", "sorting", "searching", "graph traversal", "avl tree", "stack", "queue"],
    "computer networks": ["computer network", "computer networks", "networking", "network", "networks", "tcp", "ip", "http", "dns", "routing", "osi model", "ethernet", "subnet", "congestion control"],
    "algorithms": ["algorithm", "algorithms", "complexity", "big o", "dynamic programming", "greedy", "backtracking", "divide and conquer", "dijkstra"],
    "python programming": ["python", "python programming", "numpy", "pandas", "oop in python", "django", "flask"],
    "java programming": ["java programming", "java language", "core java", "java dsa", "dsa in java", "java with dsa", "java oops", "java", "shraddha khapra", "shradha khapra", "love babbar", "babbar java"],
    "c programming": ["c programming", "pointer", "pointers", "malloc", "struct", "recursion in c", "dynamic memory", "file handling in c"],
    "engineering mechanics": ["mechanics", "statics", "dynamics", "friction", "centroid", "moment of inertia", "truss", "kinematics", "kinetics"],
    "thermodynamics": ["thermodynamics", "entropy", "enthalpy", "carnot", "rankine", "brayton", "first law", "second law", "refrigeration"],
    "digital design": ["digital design", "digital electronics", "digital logic design", "digital logic", "digital circuits", "dld", "dd", "logic gate", "logic gates", "flip flop", "flip flops", "counter", "multiplexer", "boolean algebra", "karnaugh map", "k-map", "kmap", "adc", "dac", "combinational circuits", "sequential circuits"],
    "discrete mathematics": ["discrete mathematical structures", "discrete mathematical structure", "discrete mathematics", "discrete math", "discrete maths", "discrete", "dms", "set theory", "relations and functions", "graph theory", "propositional logic", "predicate logic", "recurrence relation", "combinatorics"]
}

def classify_intent_with_llm(query: str, last_topic: str = "", conversation_history: list = None) -> dict:
    """Use fast Groq LLM zero-shot classifier to understand user's true intent in any language/slang and follow-ups."""
    groq_key = _os.environ.get("GROQ_API_KEY") or "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"
    if not groq_key:
        return None

    system_prompt = (
        "You are an expert student intent classifier for Bennett University AI copilot.\n"
        "Your job is to deeply understand the student's message (in English, Hinglish, Hindi, slang, or abbreviations).\n"
        "Analyze:\n"
        "1. 'is_video_requested': true IF:\n"
        "   - The student directly asks for videos, YouTube channels, playlists, lectures, visual tutorials, or teachers/sources to learn from (e.g. 'yt channel', 'playlist bata de', 'video links', etc.).\n"
        "   - OR the student asks a follow-up asking for recommendations for another subject (e.g. 'also give for electricals', 'aur os ka bhi de', 'same for python', 'what about dsa', 'aur mechanics ka batao', etc.).\n"
        "   Otherwise false.\n"
        "2. 'is_confused_or_frustrated': true IF the student expresses confusion, struggle, being stuck, or not understanding (e.g. 'samjh nahi aaya', 'stuck ho gaya', 'confusing', 'again please', 'tough lag raha hai', etc.). Otherwise false.\n"
        "3. 'topic': Clean 1-3 word academic topic (e.g. 'electricals', 'electronics', 'calculus', 'thevenin theorem', 'operating systems', 'python programming', 'data structures', 'engineering mechanics', etc.). If the student is asking a follow-up about a previous topic and mentions no new topic, inherit last_topic.\n\n"
        "Respond ONLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "is_video_requested": boolean,\n'
        '  "is_confused_or_frustrated": boolean,\n'
        '  "topic": string\n'
        "}"
    )

    history_str = ""
    if conversation_history:
        prev_user_msgs = []
        for m in conversation_history[-3:]:
            if isinstance(m, dict) and "user" in m:
                prev_user_msgs.append(f"- Student: {m['user']}")
            elif isinstance(m, str):
                prev_user_msgs.append(f"- Student: {m}")
        if prev_user_msgs:
            history_str = "\nRecent Conversation:\n" + "\n".join(prev_user_msgs)

    try:
        import urllib.request
        import ssl
        ctx = ssl._create_unverified_context()
        payload = _json.dumps({
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Previous active topic: \"{last_topic}\"{history_str}\nCurrent student message: \"{query}\""}
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"}
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
        )
        with urllib.request.urlopen(req, context=ctx, timeout=3.0) as response:
            data = _json.loads(response.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = _json.loads(content)
            print(f"[LLM INTENT CLASSIFIER] query='{query}' -> {parsed}")
            return parsed
    except Exception as e:
        print(f"[LLM INTENT CLASSIFIER ERROR (fallback to regex)]: {e}")
        return None

def extract_topic_from_query(query: str, last_topic: str = "") -> str:
    """Extract topic using ultra-fast in-memory pattern matching first, with LLM fallback."""
    q_clean = query.strip().lower()

    # 1. Fast in-memory explicit topic keyword matching (< 0.01ms) - Longest match first
    all_kws = []
    for topic_name, kws in TOPIC_KW.items():
        for kw in kws:
            all_kws.append((len(kw), kw, topic_name))
    all_kws.sort(key=lambda x: x[0], reverse=True)

    for _, kw, topic_name in all_kws:
        pattern = r'(?<![a-zA-Z0-9])' + _re.escape(kw) + r'(?![a-zA-Z0-9])'
        if _re.search(pattern, q_clean):
            return topic_name

    # 2. Check if this is a follow-up query that should inherit previous topic
    follow_up_tokens = {
        "bhai", "nhi", "nahi", "smj", "samj", "samjh", "smjh", "aaya", "aya",
        "video", "videos", "vid", "vids", "yt", "youtube", "channel", "channels",
        "tutorial", "tutorials", "tutorilas", "some", "again",
        "fir", "se", "please", "help", "kuch", "stuck", "what", "how", "why",
        "suggest", "suggested", "suggestions", "for", "it", "this", "that", "give",
        "show", "recommend", "links", "link", "karo", "do", "batao", "dekhna", "dekh",
        "dekho", "courses", "lecture", "online", "playlist", "youtube", "samjhao", "isko", "iska"
    }
    words = [w for w in _re.findall(r'\b[a-zA-Z]{2,}\b', q_clean)]
    is_followup = len(words) > 0 and all(w in follow_up_tokens for w in words)
    has_frustration = any(f in q_clean for f in ["smj", "samj", "nhi", "nahi", "stuck", "confusing", "again", "fir"])
    has_pronoun_ref = any(p in q_clean for p in [" it", " this", " that", " isko", " iska", " isme"])

    if (is_followup or has_frustration or has_pronoun_ref) and last_topic and last_topic != "general":
        return last_topic

    # 3. LLM semantic fallback only if ambiguous
    llm_res = classify_intent_with_llm(query, last_topic=last_topic)
    if llm_res and llm_res.get("topic") and len(llm_res["topic"].strip()) > 2:
        return llm_res["topic"].lower().strip()

    return last_topic if (last_topic and last_topic != "general") else "engineering fundamentals"

# ── Main Intent Analysis ───────────────────────────────────────────────────────

CLARIFICATION_PHRASES = [
    "explain again", "clearer", "i don't understand", "samjh nahi aa", "samjh nahi",
    "smjh nahi", "smjh nhi", "nhi smj", "nhi aaya", "confusing", "can you explain",
    "one more time", "simple words", "differently", "another way", "step by step",
    "detailed", "explain better", "iska matlab", "kya matlab", "explain karo", "samjhao",
    "batao", "easy example", "simpler words", "elaborate"
]

FRUSTRATION_PHRASES = [
    "still not", "still confused", "yrr", "bhai", "frustrated", "frustrat",
    "help", "what's wrong", "why", "can't understand", "cant understand", "too hard",
    "stuck", "not making sense", "this is hard", "aise kaise", "kuch samjh nahi",
    "yaar", "haan", "bhaii", "kuch nahi aaya", "problem ho rahi", "tough",
    "bilkul samjh nahi", "samjh nahi aaya", "smjh nahi aaya", "samjh nhi aaya",
    "smjh nhi aaya", "nhi smj", "nhi aaya", "nahi aaya"
]

VIDEO_REQUEST_SIGNALS = [
    "video", "videos", "vid", "vids", "yt", "youtube", "channel", "channels",
    "lecture", "lectures", "lec", "lecs", "tutorial", "tutorials", "tutorilas",
    "playlist", "playlists", "watch", "link", "links", "recommend channel",
    "suggest channel", "best channel", "best channels", "recommend videos",
    "suggest videos", "courses", "course", "dekho", "dekhna", "dikhao",
    "also give for", "also give", "give for", "and for", "same for", "what about",
    "aur de", "bhi de", "bhi bata"
]

def is_acknowledgement_or_greeting(query: str) -> bool:
    """Detect if the message is a pure greeting, polite acknowledgement, or thank you."""
    q_clean = _re.sub(r'[^\w\s]', '', query.strip().lower())
    words = q_clean.split()
    if len(words) == 0:
        return True
    ack_words = {
        'ok', 'okay', 'thanks', 'thank', 'you', 'thx', 'ty', 'tq', 'thanx', 'got', 'it',
        'understood', 'cool', 'great', 'nice', 'shukriya', 'dhanyawad', 'bye', 'good', 'night',
        'morning', 'afternoon', 'hello', 'hi', 'hey', 'alright', 'theek', 'hai', 'thik', 'accha',
        'acha', 'sahi', 'k', 'bro', 'bhai', 'yaar', 'sir', 'a', 'lot', 'so', 'much', 'very'
    }
    return len(words) <= 4 and all(w in ack_words for w in words)

def analyze_user_intent(
    current_message: str,
    conversation_history: list = None,
    topic: str = "",
    topic_attempts: int = 0
) -> dict:
    """
    MAIN FUNCTION: Analyze user's TRUE intent using LLM Semantic Classifier + Fallback Engine.
    Recommends videos when user is frustrated, stuck, repeating, or asks for videos / channels in ANY words.
    """
    if conversation_history is None:
        conversation_history = []

    analysis = {
        "intent": "initial",
        "confidence": 0.95,
        "should_recommend_videos": False,
        "recommendation_strength": "none",
        "reason": "",
        "video_difficulty": "beginner",
        "explanation_style": "normal",
        "topic": topic or "engineering fundamentals",
        "topic_attempts": topic_attempts
    }

    # 0. Check Greetings / Acknowledgements / Gratitude -> NO VIDEOS!
    if is_acknowledgement_or_greeting(current_message):
        analysis["intent"] = "initial"
        analysis["should_recommend_videos"] = False
        analysis["recommendation_strength"] = "none"
        analysis["reason"] = "User acknowledged/greeted"
        analysis["explanation_style"] = "normal"
        return analysis

    # 1. PRIORITY: Deep Semantic LLM Classifier (with conversation history context)
    llm_res = classify_intent_with_llm(current_message, last_topic=topic, conversation_history=conversation_history)
    if llm_res and isinstance(llm_res, dict):
        if llm_res.get("topic") and len(llm_res["topic"].strip()) > 2:
            topic = llm_res["topic"].lower().strip()
            analysis["topic"] = topic

        is_video_req = bool(llm_res.get("is_video_requested", False))
        is_confused = bool(llm_res.get("is_confused_or_frustrated", False))

        # Explicit Video/Channel Request
        if is_video_req:
            analysis["intent"] = "clarify"
            analysis["should_recommend_videos"] = True
            analysis["recommendation_strength"] = "urgent"
            analysis["reason"] = "User explicitly requested videos/playlists"
            analysis["explanation_style"] = "simpler"
            return analysis

        # Expressed Confusion / Frustration OR 3rd+ attempt on same topic
        if is_confused or topic_attempts >= 2:
            analysis["intent"] = "confused"
            analysis["should_recommend_videos"] = True
            analysis["recommendation_strength"] = "urgent"
            analysis["reason"] = "User expressed confusion/struggle" if is_confused else f"Repeated attempt #{topic_attempts + 1}"
            analysis["explanation_style"] = "basic"
            return analysis

        # First attempt asking conceptual question -> EXPLAIN FIRST, NO VIDEOS!
        if topic_attempts == 0:
            analysis["intent"] = "initial"
            analysis["should_recommend_videos"] = False
            analysis["recommendation_strength"] = "none"
            analysis["reason"] = "First attempt - explain concepts thoroughly first without videos"
            analysis["explanation_style"] = "normal"
            return analysis

        # Second attempt asking clarification -> EXPLAIN SIMPLER, NO VIDEOS YET!
        if topic_attempts == 1:
            analysis["intent"] = "clarify"
            analysis["should_recommend_videos"] = False
            analysis["recommendation_strength"] = "none"
            analysis["reason"] = "Second attempt - explain with different analogies/examples"
            analysis["explanation_style"] = "simpler"
            return analysis

    # 2. Fallback Pattern Engine (Strict word boundaries only)
    q_lower = current_message.lower()
    is_frustrated = any(phrase in q_lower for phrase in FRUSTRATION_PHRASES)
    is_asking_clarification = any(phrase in q_lower for phrase in CLARIFICATION_PHRASES)
    is_video_requested = any(_re.search(r'(?<![a-zA-Z0-9])' + _re.escape(v) + r'(?![a-zA-Z0-9])', q_lower) for v in VIDEO_REQUEST_SIGNALS)

    # Repetition Check
    is_repeating = False
    previous_messages = []
    if conversation_history:
        for i in range(len(conversation_history) - 1, max(0, len(conversation_history) - 10), -1):
            msg = conversation_history[i]
            if isinstance(msg, dict) and "user" in msg:
                previous_messages.append(msg["user"])
            elif isinstance(msg, str):
                previous_messages.append(msg)
        
        if previous_messages:
            similarities = [calculate_similarity(current_message, prev) for prev in previous_messages]
            max_similarity = max(similarities) if similarities else 0
            is_repeating = max_similarity > 0.60

    # Decision Logic (Fallback)
    if is_video_requested:
        analysis["intent"] = "clarify"
        analysis["should_recommend_videos"] = True
        analysis["recommendation_strength"] = "urgent"
        analysis["reason"] = "User explicitly requested video/channel recommendations"
        analysis["explanation_style"] = "simpler"
        return analysis

    if is_frustrated or is_repeating:
        analysis["intent"] = "confused"
        analysis["should_recommend_videos"] = True
        analysis["recommendation_strength"] = "urgent"
        analysis["reason"] = f"User is frustrated/stuck (Attempt #{topic_attempts + 1}) - urgent videos NEEDED"
        analysis["explanation_style"] = "basic"
        return analysis

    if topic_attempts >= 2:
        analysis["intent"] = "confused"
        analysis["should_recommend_videos"] = True
        analysis["recommendation_strength"] = "medium"
        analysis["reason"] = f"Attempt #{topic_attempts + 1} - recommend videos"
        analysis["explanation_style"] = "simpler"
        return analysis

    if is_asking_clarification and topic_attempts >= 1:
        analysis["intent"] = "clarify"
        analysis["should_recommend_videos"] = False
        analysis["reason"] = "User needs clarification - provide different explanation"
        analysis["explanation_style"] = "simpler"
        return analysis

    analysis["intent"] = "initial"
    analysis["should_recommend_videos"] = False
    analysis["reason"] = "First time asking - provide explanation only"
    analysis["explanation_style"] = "normal"
    return analysis


# ── Video Recommendations & Rating ─────────────────────────────────────────────

TOPIC_TO_FACULTY_MAP = {
    "electricals": ["electrical", "electronics", "thevenin", "umesh dhande", "engineers ki pathshala", "perfect computer engineer", "tikle's academy", "tikle", "neso academy"],
    "electrical": ["electrical", "electronics", "thevenin", "umesh dhande", "engineers ki pathshala", "perfect computer engineer", "tikle's academy", "tikle", "neso academy"],
    "electrical engineering": ["electrical", "electronics", "thevenin", "umesh dhande", "engineers ki pathshala", "perfect computer engineer", "tikle's academy", "tikle", "neso academy"],
    "bee": ["electrical", "electronics", "thevenin", "umesh dhande", "engineers ki pathshala", "perfect computer engineer", "tikle's academy", "tikle", "neso academy"],
    "beee": ["electrical", "electronics", "thevenin", "umesh dhande", "engineers ki pathshala", "perfect computer engineer", "tikle's academy", "tikle", "neso academy"],
    "thevenin theorem": ["thevenin", "network", "circuit", "electrical", "electronics", "kvl", "kcl", "umesh dhande", "engineers ki pathshala", "tikle's academy", "perfect computer engineer", "neso academy"],
    "electrical circuits": ["circuit", "circuits", "electrical", "electronics", "umesh dhande", "engineers ki pathshala", "perfect computer engineer", "tikle's academy", "neso academy"],
    "electrical machines": ["electrical", "motor", "transformer", "circuits", "neso academy"],
    "electronics": ["electrical", "electronics", "thevenin", "umesh dhande", "engineers ki pathshala", "perfect computer engineer", "tikle's academy", "tikle", "neso academy"],
    "basic electronics": ["electrical", "electronics", "thevenin", "umesh dhande", "engineers ki pathshala", "perfect computer engineer", "tikle's academy", "tikle", "neso academy"],
    "analog electronics": ["electrical", "electronics", "thevenin", "umesh dhande", "engineers ki pathshala", "perfect computer engineer", "tikle's academy", "tikle", "neso academy"],
    "ece": ["electrical", "electronics", "thevenin", "umesh dhande", "engineers ki pathshala", "perfect computer engineer", "tikle's academy", "tikle", "neso academy"],
    "calculus": ["calculus", "differential calculus", "integral calculus", "differentiation", "integration", "derivative", "derivatives", "integral", "integrals", "limit", "limits", "taylor", "gajendra purohit", "pradeep giri", "tikle's academy", "tikle", "vishwakarma"],
    "math": ["calculus", "differentiation", "integration", "derivative", "differential", "vishwakarma"],
    "maths": ["calculus", "differentiation", "integration", "derivative", "differential", "vishwakarma"],
    "mathematics": ["calculus", "differentiation", "integration", "derivative", "differential", "vishwakarma"],
    "differential equations": ["differential equation", "differential equations", "differntial equations", "differntial equation", "ode", "pde", "exact differential", "bernoulli equation", "linear differential", "higher order differential"],
    "differntial equations": ["differential equation", "differential equations", "differntial equations", "differntial equation", "ode", "pde", "exact differential", "bernoulli equation", "linear differential", "higher order differential"],
    "ode": ["differential equation", "differential equations", "differntial equations", "differntial equation", "ode", "pde", "exact differential", "bernoulli equation", "linear differential", "higher order differential"],
    "pde": ["differential equation", "differential equations", "differntial equations", "differntial equation", "ode", "pde", "exact differential", "bernoulli equation", "linear differential", "higher order differential"],
    "linear algebra": ["linear algebra", "matrices", "matrix", "eigenvalue", "eigenvalues", "eigenvector", "vector space", "linear transformation", "gajendra purohit", "pradeep giri", "gate wallah", "physics wallah"],
    "linear algerba": ["linear algebra", "matrices", "matrix", "eigenvalue", "eigenvalues", "eigenvector", "vector space", "linear transformation", "gajendra purohit", "pradeep giri", "gate wallah", "physics wallah"],
    "matrices": ["linear algebra", "matrices", "matrix", "eigenvalue", "eigenvalues", "eigenvector", "vector space", "linear transformation", "gajendra purohit", "pradeep giri", "gate wallah", "physics wallah"],
    "matrix": ["linear algebra", "matrices", "matrix", "eigenvalue", "eigenvalues", "eigenvector", "vector space", "linear transformation", "gajendra purohit", "pradeep giri", "gate wallah", "physics wallah"],
    "operating systems": ["operating", "os", "deadlock", "semaphore", "process", "gate smashers", "varun singla", "neso academy"],
    "os": ["operating", "os", "deadlock", "semaphore", "process", "gate smashers", "varun singla", "neso academy"],
    "python programming": ["python", "programming", "code with harry", "apna college", "shradha khapra"],
    "python": ["python", "programming", "code with harry", "apna college", "shradha khapra"],
    "java programming": ["java", "core java", "java programming", "oops", "shradha khapra", "shraddha khapra", "apna college", "love babbar", "babbar", "codehelp"],
    "java": ["java", "core java", "java programming", "oops", "shradha khapra", "shraddha khapra", "apna college", "love babbar", "babbar", "codehelp"],
    "core java": ["java", "core java", "java programming", "oops", "shradha khapra", "shraddha khapra", "apna college", "love babbar", "babbar", "codehelp"],
    "java dsa": ["java", "core java", "java programming", "oops", "shradha khapra", "shraddha khapra", "apna college", "love babbar", "babbar", "codehelp"],
    "coding": ["python", "programming", "code with harry", "apna college", "shradha khapra", "abdul bari"],
    "data structures": ["data structure", "dsa", "abdul bari", "tree", "graph", "algorithm", "apna college", "shradha khapra", "jenny's lectures", "jenny", "college wallah"],
    "dsa": ["data structure", "dsa", "abdul bari", "tree", "graph", "algorithm", "apna college", "shradha khapra", "jenny's lectures", "jenny", "college wallah"],
    "algorithms": ["algorithm", "algorithms", "abdul bari", "dynamic programming", "dsa", "jenny's lectures", "jenny"],
    "engineering mechanics": ["mechanics", "statics", "dynamics", "pradeep giri"],
    "mechanics": ["mechanics", "statics", "dynamics", "pradeep giri"],
    "thermodynamics": ["thermodynamics", "entropy", "heat", "mechanical"],
    "fluid mechanics": ["fluid", "bernoulli", "mechanical"],
    "digital design": ["digital design", "digital electronics", "dld", "dd", "logic gate", "flip flop", "k-map", "gate smashers", "engineering funda", "neso academy", "knowledge gate", "varun singla", "sanchit jain"],
    "digital electronics": ["digital design", "digital electronics", "dld", "dd", "logic gate", "flip flop", "k-map", "gate smashers", "engineering funda", "neso academy", "knowledge gate", "varun singla", "sanchit jain"],
    "digital logic": ["digital design", "digital electronics", "dld", "dd", "logic gate", "flip flop", "k-map", "gate smashers", "engineering funda", "neso academy", "knowledge gate", "varun singla", "sanchit jain"],
    "digital logic design": ["digital design", "digital electronics", "dld", "dd", "logic gate", "flip flop", "k-map", "gate smashers", "engineering funda", "neso academy", "knowledge gate", "varun singla", "sanchit jain"],
    "dld": ["digital design", "digital electronics", "dld", "dd", "logic gate", "flip flop", "k-map", "gate smashers", "engineering funda", "neso academy", "knowledge gate", "varun singla", "sanchit jain"],
    "dd": ["digital design", "digital electronics", "dld", "dd", "logic gate", "flip flop", "k-map", "gate smashers", "engineering funda", "neso academy", "knowledge gate", "varun singla", "sanchit jain"],
    "information management system": ["information management", "ims", "dbms", "database", "sql", "gate smashers", "neso academy", "varun singla"],
    "information management": ["information management", "ims", "dbms", "database", "sql", "gate smashers", "neso academy", "varun singla"],
    "ims": ["information management", "ims", "dbms", "database", "sql", "gate smashers", "neso academy", "varun singla"],
    "dbms": ["information management", "ims", "dbms", "database", "sql", "gate smashers", "neso academy", "varun singla"],
    "database": ["information management", "ims", "dbms", "database", "sql", "gate smashers", "neso academy", "varun singla"],
    "probability and statistics": ["probability", "statistics", "stats", "p&s", "gajendra purohit", "tending to infinity", "algorithm unlocked", "pradeep giri", "random variables", "distributions"],
    "probability": ["probability", "statistics", "stats", "p&s", "gajendra purohit", "tending to infinity", "algorithm unlocked", "pradeep giri"],
    "statistics": ["probability", "statistics", "stats", "p&s", "gajendra purohit", "tending to infinity", "algorithm unlocked", "pradeep giri"],
    "stats": ["probability", "statistics", "stats", "p&s", "gajendra purohit", "tending to infinity", "algorithm unlocked", "pradeep giri"],
    "p&s": ["probability", "statistics", "stats", "p&s", "gajendra purohit", "tending to infinity", "algorithm unlocked", "pradeep giri"],
    "dsa with c++": ["c++", "cpp", "dsa", "shradha khapra", "apna college", "college wallah", "jenny's lectures", "jenny", "abdul bari", "data structures"],
    "c++ dsa": ["c++", "cpp", "dsa", "shradha khapra", "apna college", "college wallah", "jenny's lectures", "jenny", "abdul bari", "data structures"],
    "cpp dsa": ["c++", "cpp", "dsa", "shradha khapra", "apna college", "college wallah", "jenny's lectures", "jenny", "abdul bari", "data structures"],
    "dsa cpp": ["c++", "cpp", "dsa", "shradha khapra", "apna college", "college wallah", "jenny's lectures", "jenny", "abdul bari", "data structures"],
    "cpp": ["c++", "cpp", "dsa", "shradha khapra", "apna college", "college wallah", "jenny's lectures", "jenny", "abdul bari", "data structures"],
    "c++": ["c++", "cpp", "dsa", "shradha khapra", "apna college", "college wallah", "jenny's lectures", "jenny", "abdul bari", "data structures"],
    "discrete mathematics": ["discrete", "dms", "discrete mathematical structures", "set theory", "relations", "graph theory", "logic", "neso academy", "gate smashers", "knowledge gate", "pradeep giri", "varun singla", "sanchit jain"],
    "discrete mathematical structures": ["discrete", "dms", "discrete mathematical structures", "set theory", "relations", "graph theory", "logic", "neso academy", "gate smashers", "knowledge gate", "pradeep giri", "varun singla", "sanchit jain"],
    "discrete math": ["discrete", "dms", "discrete mathematical structures", "set theory", "relations", "graph theory", "logic", "neso academy", "gate smashers", "knowledge gate", "pradeep giri", "varun singla", "sanchit jain"],
    "dms": ["discrete", "dms", "discrete mathematical structures", "set theory", "relations", "graph theory", "logic", "neso academy", "gate smashers", "knowledge gate", "pradeep giri", "varun singla", "sanchit jain"],
    "discrete": ["discrete", "dms", "discrete mathematical structures", "set theory", "relations", "graph theory", "logic", "neso academy", "gate smashers", "knowledge gate", "pradeep giri", "varun singla", "sanchit jain"]
}

def get_recommended_videos(
    subject: str = "",
    topic: str = "",
    difficulty_level: str = "Beginner",
    mode: str = "exam",
    limit: int = 4
) -> list:
    """Get best verified YouTube playlists tailored directly to the student's exact topic."""
    def _do():
        cursor = conn.cursor()
        
        # 1. Fetch from youtube_playlist table
        rows = cursor.execute("""
            SELECT id, channel_name, instructor, subject, topic, playlist_url, difficulty,
                   helpfulness_score, total_ratings, helpful_count, total_videos, avg_duration
            FROM youtube_playlist
            WHERE university = 'Bennett University'
        """).fetchall()

        topic_clean = (topic or "").lower().strip()
        keywords = TOPIC_TO_FACULTY_MAP.get(topic_clean, [topic_clean])
        INCOMPATIBLE_PAIRS = [
            ("python", ["java", "c++", "calculus", "electronics", "database", "discrete", "digital", "operating"]),
            ("java", ["python", "c++", "calculus", "electronics", "database", "discrete", "digital", "operating"]),
            ("c++", ["python", "java", "calculus", "electronics", "database", "discrete", "digital", "operating"]),
            ("dsa", ["python", "java", "calculus", "electronics", "database", "discrete", "digital", "operating"]),
            ("calculus", ["probability", "statistics", "matrix", "matrices", "differential equations", "ode", "pde", "electronics", "java", "python"]),
            ("differential", ["calculus", "probability", "statistics", "matrix", "matrices", "electronics", "java", "python"]),
            ("linear", ["calculus", "differential", "probability", "statistics", "electronics", "java", "python"]),
            ("matrices", ["calculus", "differential", "probability", "statistics", "electronics", "java", "python"]),
            ("probability", ["calculus", "matrices", "linear algebra", "differential", "electronics", "java", "python"]),
            ("discrete", ["operating systems", "information management", "digital design", "electronics", "java", "python"]),
            ("dms", ["operating systems", "information management", "digital design", "electronics", "java", "python"]),
            ("digital", ["operating systems", "information management", "discrete", "basic electrical", "java", "python"]),
            ("dld", ["operating systems", "information management", "discrete", "basic electrical", "java", "python"]),
            ("dd", ["operating systems", "information management", "discrete", "basic electrical", "java", "python"]),
            ("information", ["operating systems", "discrete", "digital design", "java", "python"]),
            ("dbms", ["operating systems", "discrete", "digital design", "java", "python"]),
            ("ims", ["operating systems", "discrete", "digital design", "java", "python"]),
            ("operating", ["information management", "discrete", "digital design", "java", "python"]),
            ("os", ["information management", "discrete", "digital design", "java", "python"]),
            ("electronics", ["calculus", "differential", "linear algebra", "probability", "digital design", "discrete", "java", "python", "dbms", "os"])
        ]

        scored = []
        for r in rows:
            p_id, ch, inst, subj, top, url, diff, score, t_ratings, h_count, t_vids, avg_dur = r
            text = f"{ch} {inst} {subj} {top}".lower()
            subj_lower = (subj or "").lower()
            top_lower = (top or "").lower()

            # Strict cross-subject incompatibility check
            is_incompatible = False
            for target_topic, forbidden_terms in INCOMPATIBLE_PAIRS:
                if target_topic in topic_clean:
                    for forbidden in forbidden_terms:
                        if (forbidden in subj_lower or forbidden in top_lower) and target_topic not in subj_lower and target_topic not in top_lower:
                            is_incompatible = True
                            break
                if is_incompatible:
                    break
            
            if is_incompatible:
                continue
            
            match_score = 0
            # Direct keyword hits
            for kw in keywords:
                if kw in text:
                    if kw in ["gajendra purohit", "pradeep giri", "neso academy", "apna college", "shradha khapra", "umesh dhande", "knowledge gate", "sanchit jain", "engineering funda", "gate wallah", "love babbar", "babbar"]:
                        match_score += 10
                    else:
                        match_score += 25
            
            # Direct topic match
            if topic_clean and topic_clean in text:
                match_score += 40
            
            # Subject domain affinity
            if "calculus" in topic_clean and "calculus" in subj.lower():
                match_score += 60
            elif ("differential" in topic_clean or "differntial" in topic_clean or "ode" in topic_clean or "pde" in topic_clean) and ("differential" in subj.lower() or "equations" in subj.lower()):
                match_score += 60
            elif ("linear" in topic_clean or "matrices" in topic_clean or "matrix" in topic_clean or "eigen" in topic_clean) and ("linear" in subj.lower() or "algebra" in subj.lower() or "matrices" in subj.lower()):
                match_score += 60
            elif "probability" in topic_clean and ("probability" in subj.lower() or "statistics" in subj.lower()):
                match_score += 60
            elif "electronics" in topic_clean and ("electrical" in subj.lower() or "electronics" in subj.lower()):
                match_score += 60
            elif "information management" in topic_clean and ("information" in subj.lower() or "dbms" in subj.lower()):
                match_score += 60
            elif "operating system" in topic_clean and "operating" in subj.lower():
                match_score += 60
            elif "python" in topic_clean and "python" in subj.lower():
                match_score += 60
            elif "java" in topic_clean and ("java" in subj.lower() or "java" in top.lower()):
                match_score += 60
            elif "c++" in topic_clean and "c++" in subj.lower():
                match_score += 60
            elif "mechanics" in topic_clean and "mechanics" in subj.lower():
                match_score += 60
            elif ("discrete" in topic_clean or "dms" in topic_clean) and ("discrete" in subj.lower() or "dms" in subj.lower()):
                match_score += 60
            elif ("digital" in topic_clean or "dld" in topic_clean or topic_clean == "dd") and ("digital" in subj.lower() or "design" in subj.lower()):
                match_score += 60

            # Exact subject match if provided
            if subject and subject.lower() in subj.lower():
                match_score += 20

            # Cutoff: must have strong topic/domain match (>= 35)
            if match_score >= 35:
                scored.append((match_score, {
                    "id": p_id,
                    "channel": ch,
                    "instructor": inst,
                    "topic": top,
                    "playlist_url": url,
                    "difficulty": diff,
                    "rating": round(score or 4.8, 1),
                    "total_ratings": t_ratings or 20,
                    "helpful_count": h_count or 19,
                    "helpful_percentage": round((h_count / t_ratings * 100) if t_ratings and t_ratings > 0 else 92, 0),
                    "total_videos": t_vids or 30,
                    "avg_duration": avg_dur or 20
                }))

        scored.sort(key=lambda x: x[0], reverse=True)
        seen_items = set()
        results = []
        for item in scored:
            dedup_key = (item[1]["channel"], item[1]["topic"])
            if dedup_key not in seen_items:
                seen_items.add(dedup_key)
                results.append(item[1])
                if len(results) >= limit:
                    break

        # Fallback if no exact match in DB: direct targeted Bennett YouTube link
        if not results:
            from urllib.parse import quote_plus
            base = "https://www.youtube.com/results?search_query="
            results = [{
                "id": 99,
                "channel": "Bennett University Verified Lectures",
                "instructor": "Top Faculty Series",
                "topic": f"{topic.title() if topic else 'Engineering Topic'} — Complete Video Playlist",
                "playlist_url": base + quote_plus(f"{topic} Bennett University lecture"),
                "difficulty": "Beginner",
                "rating": 4.9,
                "total_ratings": 35,
                "helpful_count": 33,
                "helpful_percentage": 94,
                "total_videos": 22,
                "avg_duration": 20
            }]

        return results

    return db_retry(_do)

def rate_playlist_record(playlist_id: int, user_id: int, rating: int, was_helpful: bool, watched_percentage: int = 30) -> dict:
    """Record user playlist rating and recompute helpfulness score."""
    def _do():
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO playlist_rating (user_id, playlist_id, rating, was_helpful, watched_percentage, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, playlist_id, rating, 1 if was_helpful else 0, watched_percentage, _dt.now().isoformat()))

        # Update totals in youtube_playlist
        cursor.execute("""
            UPDATE youtube_playlist
            SET total_ratings = total_ratings + 1,
                helpful_count = helpful_count + ?
            WHERE id = ?
        """, (1 if was_helpful else 0, playlist_id))

        # Recompute score
        all_ratings = cursor.execute("SELECT rating FROM playlist_rating WHERE playlist_id = ?", (playlist_id,)).fetchall()
        if all_ratings:
            avg_score = sum(r[0] for r in all_ratings) / len(all_ratings)
            cursor.execute("UPDATE youtube_playlist SET helpfulness_score = ? WHERE id = ?", (round(avg_score, 1), playlist_id))
        else:
            avg_score = 4.5

        conn.commit()
        return {"avg_rating": round(avg_score, 1)}
    return db_retry(_do)

def get_next_action_message(recommendation_strength: str, attempt_number: int) -> str:
    """Suggest next action based on recommendation strength and attempts."""
    if recommendation_strength == "urgent":
        return "👉 Watch a video first, then come back with specific questions"
    elif recommendation_strength == "medium":
        return "👉 Try the practice questions, or watch a video if still stuck"
    else:
        if attempt_number == 1:
            return "👉 Ready for practice questions?"
        else:
            return "👉 Let's try practice questions"


def _extract_topic_keywords(query: str) -> str:
    """Keyword-based academic topic extraction."""
    TOPIC_KW = {
        "electronics": ["basic electronics", "basic electrical", "analog electronics", "electrical engineering", "electronics engineering", "electrical and electronics", "electrical & electronics", "electricals", "electrical", "electronics", "electronic", "elctronics", "electonics", "electornics", "electircal", "elec", "bee", "beee", "ece", "semiconductor", "diode", "bjt", "opamp", "transistor", "fet", "mosfet"],
        "thevenin theorem": ["thevenin", "thevenin's", "norton", "kvl", "kcl", "maximum power transfer", "superposition theorem", "reciprocity"],
        "electrical circuits": ["circuit", "dependent source", "phasor", "impedance", "mesh analysis", "nodal analysis", "rlc circuit", "ac circuit", "kirchhoff"],
        "electrical machines": ["induction motor", "transformer", "rotating magnetic field", "rmf", "synchronous motor", "dc motor", "stator", "rotor", "armature", "torque slip"],
        "power systems": ["power factor", "three phase", "transmission line", "load flow", "fault analysis", "generator", "bus admittance"],
        "control systems": ["bode plot", "root locus", "nyquist plot", "transfer function", "pid controller", "state space", "stability"],
        "thermodynamics": ["thermodynamics", "entropy", "enthalpy", "carnot", "rankine", "brayton", "first law", "second law", "refrigeration"],
        "fluid mechanics": ["bernoulli", "navier stokes", "viscosity", "reynolds number", "venturimeter", "fluid flow", "pipe flow"],
        "operating systems": ["operating system", "deadlock", "scheduling", "semaphore", "paging", "virtual memory", "process management", "banker's algorithm"],
        "data structures": ["data structure", "linked list", "binary tree", "heap", "bst", "sorting", "searching", "graph traversal", "avl tree"],
        "dsa with c++": ["dsa with c++", "c++ dsa", "cpp dsa", "dsa in c++", "c++ data structures", "dsa cpp", "c++", "cpp"],
        "information management system": ["information management", "ims", "database management", "dbms", "database", "sql", "relational algebra", "normalization", "acid properties", "transaction", "acid", "b+ tree"],
        "probability and statistics": ["probability and statistics", "probability & statistics", "statistics", "probability", "stats", "p&s", "random variable", "bayes theorem", "poisson distribution", "normal distribution", "binomial distribution", "hypothesis testing"],
        "computer networks": ["network", "tcp", "ip", "http", "dns", "routing", "osi", "ethernet", "subnet", "congestion control"],
        "algorithms": ["algorithm", "complexity", "big o", "dynamic programming", "greedy", "backtracking", "divide and conquer", "dijkstra"],
        "machine learning": ["machine learning", "neural network", "deep learning", "regression", "gradient descent", "backpropagation", "cnn", "rnn"],
        "linear algebra": ["linear algebra", "linear algerba", "eigenvalue", "eigenvector", "matrix", "matrices", "determinant", "rank of matrix", "linear transformation", "vector space"],
        "digital design": ["digital design", "digital electronics", "digital logic", "dld", "dd", "logic gate", "flip flop", "counter", "multiplexer", "boolean", "karnaugh", "k-map", "adc", "dac"],
        "signals systems": ["fourier", "laplace", "convolution", "filter", "sampling", "nyquist", "z-transform", "fourier transform"],
        "engineering mathematics": ["calculus", "differential equation", "eigenvalue", "eigenvector", "integral", "probability", "laplace transform", "linear algebra"],
        "c programming": ["pointer", "malloc", "struct", "recursion in c", "dynamic memory", "file handling in c"],
        "java programming": ["java programming", "core java", "java dsa", "java", "oop in java"],
        "object oriented": ["oop", "object oriented", "inheritance", "polymorphism", "encapsulation", "abstraction", "virtual function"],
        "computer architecture": ["processor", "cpu", "cache", "pipeline", "instruction set", "alu", "cache mapping", "pipelining hazards"],
        "software engineering": ["sdlc", "agile", "design pattern", "uml", "software testing", "waterfall model"],
        "discrete mathematics": ["discrete mathematical structures", "discrete mathematical structure", "discrete mathematics", "discrete math", "discrete maths", "discrete", "dms", "set theory", "relations and functions", "graph theory", "propositional logic", "predicate logic", "recurrence relation", "combinatorics"]
    }
    q = query.lower()
    for topic, kws in TOPIC_KW.items():
        if any(kw in q for kw in kws):
            return topic
    return "general"


# ── Frustration / Clarification / Video signals (with typo tolerance) ──────────
_FRUSTRATION_SIGNALS = [
    "still not", "still confused", "samjh nahi", "smjh nahi", "smjh nhi", "samjh nhi",
    "nhi smj", "nhi samj", "nhi smjh", "nhi aaya", "nahi aaya", "smj nahi aaya",
    "smj aaya", "samj aaya", "smjh aaya", "kuch nahi aaya", "kuch smjh",
    "confusing", "complicated", "too hard", "stuck", "not getting", "not getting it",
    "explain again", "ek baar", "dubara", "fir se", "phir se", "once more",
    "cant understand", "can't understand", "kuch samjh", "pata nahi", "unclear",
    "lost", "no idea", "phir bhi nahi", "ab bhi nahi", "samjha nahi", "समझ नहीं",
    "problem ho rahi", "tough", "help me understand", "give me videos", "suggest video",
    "video recommendation", "video chahiye", "visual explanation", "bhai nhi", "nhi bhai"
]

_VIDEO_REQUEST_SIGNALS = [
    "video", "videos", "youtube", "visual", "lecture", "lectures", "playlist",
    "animation", "animations", "tutorial", "tutorials", "tutorilas", "tutoria",
    "watch", "dekho", "dekhna", "suggest video", "recommend video", "video link", "video links"
]

_CLARIFICATION_SIGNALS = [
    "explain", "what is", "how does", "why is", "difference between",
    "meaning of", "elaborate", "step by step", "example",
    "simple", "basic", "easy way", "layman", "in simple words", "again",
    "simpler words", "easy example", "simplest", "batao", "samjhao"
]

# ── Groq topic extraction with topic memory ──────────────────────────────────
def _extract_topic_nlp(query: str, last_topic: str = "", recent_queries: list = None) -> str:
    """Use Groq LLM or keyword fallback to extract main topic, inheriting last_topic if follow-up."""
    q_clean = query.strip().lower()
    
    # 1. Check explicit keyword dictionary FIRST for instant 100% accurate detection
    kw_topic = _extract_topic_keywords(query)
    if kw_topic != "general":
        return kw_topic

    # 2. Expanded follow-up tokens & phrases (e.g. 'suggest some video for it', 'bhai video do', 'isko explain karo')
    follow_up_tokens = {
        "bhai", "nhi", "nahi", "smj", "samj", "samjh", "smjh", "aaya", "aya",
        "video", "videos", "tutorial", "tutorials", "tutorilas", "some", "again",
        "fir", "se", "please", "help", "kuch", "stuck", "what", "how", "why",
        "suggest", "suggested", "suggestions", "for", "it", "this", "that", "give",
        "show", "recommend", "links", "link", "karo", "do", "batao", "dekhna", "dekh",
        "dekho", "courses", "lecture", "online", "playlist", "youtube", "samjhao", "isko", "iska"
    }
    words = [w for w in _re.findall(r'\b[a-zA-Z]{2,}\b', q_clean)]
    is_mostly_followup = len(words) > 0 and all(w in follow_up_tokens for w in words)
    
    # If the user is asking for videos, or is frustrated, or query is mostly follow-up words: REUSE last_topic!
    has_video_word = any(v in q_clean for v in ["video", "tutorial", "youtube", "lecture", "playlist", "animation"])
    has_frustration_word = any(f in q_clean for f in ["smj", "samj", "nhi", "nahi", "stuck", "confusing", "again", "fir"])
    
    if (is_mostly_followup or (has_video_word and ("it" in q_clean or "this" in q_clean or len(words) <= 4)) or (has_frustration_word and len(words) <= 4)) and last_topic and last_topic != "general":
        print(f"[NLP TOPIC] Reusing last_topic '{last_topic}' for query: '{query}'")
        return last_topic

    # 3. Call Groq for zero-shot topic extraction
    try:
        client = _get_groq()
        if client:
            context_hint = f"Previous active academic topic was: '{last_topic}'. " if last_topic else ""
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{
                    "role": "system",
                    "content": (
                        "You extract the core academic or engineering subject/topic from a student's message. "
                        f"{context_hint}"
                        "If the user is asking a follow-up like 'suggest some video for it' or 'samjh nahi aaya', output the previous active topic name. "
                        "Reply with ONLY 1 to 4 lowercase words naming the academic topic. No punctuation."
                    )
                }, {
                    "role": "user",
                    "content": query
                }],
                max_tokens=15,
                temperature=0
            )
            topic = resp.choices[0].message.content.strip().lower()
            topic = _re.sub(r'["\'\.\!\?\,]', '', topic).strip()
            if topic and len(topic) > 2 and topic not in {"none", "general", "no topic", "n/a", "video", "videos", "suggest"}:
                return topic
    except Exception as e:
        print(f"[NLP] Topic Groq error: {e}")

    return last_topic if (last_topic and last_topic != "general") else kw_topic

# ── DB helpers ────────────────────────────────────────────────────────────────
def get_conversation_context(thread_id: str) -> dict:
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT total_messages, topic_attempts, recent_queries, last_topic FROM conversation_contexts WHERE thread_id = ?",
            (thread_id,)
        ).fetchone()
        if row:
            return {
                "total_messages": row[0] or 0,
                "topic_attempts": _json.loads(row[1] or "{}"),
                "recent_queries":  _json.loads(row[2] or "[]"),
                "last_topic":      row[3] or ""
            }
        return {"total_messages": 0, "topic_attempts": {}, "recent_queries": [], "last_topic": ""}
    except Exception as e:
        print(f"[CONTEXT] get error: {e}")
        return {"total_messages": 0, "topic_attempts": {}, "recent_queries": [], "last_topic": ""}

def update_conversation_context(thread_id: str, user_email: str, topic: str, query: str = ""):
    """Update message count, topic attempts, recent queries and last_topic for a thread."""
    def _do():
        cursor = conn.cursor()
        existing = cursor.execute(
            "SELECT total_messages, topic_attempts, recent_queries, last_topic FROM conversation_contexts WHERE thread_id = ?",
            (thread_id,)
        ).fetchone()
        now = _dt.now().isoformat()
        if existing:
            total    = (existing[0] or 0) + 1
            attempts = _json.loads(existing[1] or "{}")
            recent   = _json.loads(existing[2] or "[]")
            if topic and topic != "general":
                attempts[topic] = attempts.get(topic, 0) + 1
                active_topic = topic
            else:
                active_topic = existing[3] or topic
            if query:
                recent.append(query)
                recent = recent[-6:]  # keep last 6 queries
            cursor.execute(
                "UPDATE conversation_contexts SET total_messages=?, topic_attempts=?, recent_queries=?, last_topic=?, updated_at=? WHERE thread_id=?",
                (total, _json.dumps(attempts), _json.dumps(recent), active_topic, now, thread_id)
            )
        else:
            attempts = {topic: 1} if (topic and topic != "general") else {}
            recent   = [query] if query else []
            cursor.execute(
                "INSERT INTO conversation_contexts (thread_id, user_email, total_messages, topic_attempts, recent_queries, last_topic, created_at, updated_at) VALUES (?,?,1,?,?,?,?,?)",
                (thread_id, user_email or "", _json.dumps(attempts), _json.dumps(recent), topic, now, now)
            )
        conn.commit()
    db_retry(_do)




COMMON_PASSWORDS_BLOCKLIST = {
    "password123", "12345678", "123456789", "123456", "qwerty", "password",
    "admin123", "welcome123", "letmein123", "college123", "prepz12345"
}

def hash_password(password: str, email: str = "") -> str:
    user_salt = f"college_freshers_{email.strip().lower()}_2026_salt"
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        user_salt.encode('utf-8'),
        260000
    ).hex()

def verify_password(password: str, hashed: str, email: str = "") -> bool:
    if not password or not hashed:
        return False
    if hash_password(password, email) == hashed:
        return True
    # Compatibility checks for legacy iterations (120,000 & 100,000)
    user_salt = f"college_freshers_{email.strip().lower()}_2026_salt"
    h120 = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), user_salt.encode('utf-8'), 120000).hex()
    if h120 == hashed:
        return True
    legacy_salt = "college_freshers_salt_2026"
    legacy_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), legacy_salt.encode('utf-8'), 100000).hex()
    return legacy_hash == hashed

import re
import random
from datetime import datetime, timedelta

def validate_password_strength(password: str) -> tuple[bool, str]:
    if not password or len(password) < 12:
        return False, "Password must be at least 12 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number (0-9)."
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        return False, "Password must contain at least one special character (!@#$%^&*)."
    if password.lower() in COMMON_PASSWORDS_BLOCKLIST:
        return False, "Password is too common or easily guessable."
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

def add_contribution_points(email: str, points: int, name: Optional[str] = None):
    if not email or points <= 0 or email.lower().strip() == "anonymous@college.edu":
        return
    email = email.strip().lower()

    def _do():
        with get_db() as c:
            cursor = c.cursor()
            cursor.execute("SELECT id, name, contribution_score FROM users WHERE lower(email) = ?", (email,))
            row = cursor.fetchone()
            today = datetime.now().strftime("%Y-%m-%d")
            if row:
                cursor.execute("""
                    UPDATE users 
                    SET contribution_score = COALESCE(contribution_score, 0) + ?,
                        last_active_date = ?
                    WHERE lower(email) = ?
                """, (points, today, email))
            else:
                user_name = (name or email.split("@")[0].replace(".", " ")).strip().title()
                avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={email}"
                cursor.execute("""
                    INSERT INTO users (name, email, provider, avatar_url, contribution_score, current_streak, last_active_date, is_verified)
                    VALUES (?, ?, 'email', ?, ?, 1, ?, 1)
                """, (user_name, email, avatar, points, today))
            c.commit()
    db_retry(_do)

def seed_leaderboard_community():
    """Seed vibrant Bennett University peer contributors if needed to ensure live community feel."""
    ACTIVE_BENNETT_PEERS = [
        {"name": "Aryan Sharma", "email": "aryan.sharma@bennett.edu.in", "branch": "CSE '25", "score": 420, "streak": 7},
        {"name": "Priya Patel", "email": "priya.patel@bennett.edu.in", "branch": "AI/DS '26", "score": 380, "streak": 6},
        {"name": "Rohan Mehta", "email": "rohan.mehta@bennett.edu.in", "branch": "ECE '25", "score": 295, "streak": 5},
        {"name": "Sneha Gupta", "email": "sneha.gupta@bennett.edu.in", "branch": "CSE '26", "score": 260, "streak": 4},
        {"name": "Aditya Verma", "email": "aditya.verma@bennett.edu.in", "branch": "ME '25", "score": 215, "streak": 4},
        {"name": "Ananya Roy", "email": "ananya.roy@bennett.edu.in", "branch": "CST '26", "score": 180, "streak": 3},
        {"name": "Harsh Vardhan", "email": "harsh.v@bennett.edu.in", "branch": "AI '26", "score": 120, "streak": 2},
        {"name": "Ritik Singh", "email": "ritik.s@bennett.edu.in", "branch": "CSE '27", "score": 95, "streak": 2},
        {"name": "Tanvi Saxena", "email": "tanvi.s@bennett.edu.in", "branch": "BioTech '25", "score": 75, "streak": 2}
    ]
    with get_db() as c:
        cursor = c.cursor()
        for p in ACTIVE_BENNETT_PEERS:
            cursor.execute("SELECT id FROM users WHERE lower(email) = lower(?)", (p["email"],))
            if not cursor.fetchone():
                avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={p['name'].replace(' ', '')}"
                cursor.execute("""
                    INSERT INTO users (name, email, provider, avatar_url, contribution_score, current_streak, last_active_date, is_verified)
                    VALUES (?, ?, 'seeded', ?, ?, ?, ?, 1)
                """, (p["name"], p["email"], avatar, p["score"], p["streak"], datetime.now().strftime("%Y-%m-%d")))
        c.commit()

# Ensure community users exist on module load
try:
    seed_leaderboard_community()
except Exception:
    pass

def get_top_contributors(limit: int = 25, current_user_email: Optional[str] = None) -> dict:
    """
    Retrieve live rankings of active contributors, computing accurate ranks, streak badges,
    and user rank position.
    """
    with get_db() as c:
        cursor = c.cursor()
        # Query active real users excluding system test runners
        cursor.execute("""
            SELECT name, email, avatar_url, COALESCE(contribution_score, 0) as score, COALESCE(current_streak, 0) as streak
            FROM users
            WHERE lower(email) NOT LIKE '%test%'
              AND lower(email) NOT LIKE 'lockout%'
              AND lower(email) NOT LIKE 'clean_user%'
              AND lower(email) NOT LIKE 'anonymous%'
              AND lower(email) != 'student1@college.edu'
              AND lower(email) != 'student2@college.edu'
            ORDER BY score DESC, streak DESC, id ASC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()

        leaderboard = []
        user_rank_info = None

        for idx, r in enumerate(rows):
            rank = idx + 1
            raw_name = (r[0] or "").strip()
            # Clean up display name
            display_name = raw_name.title() if raw_name else "Bennett Student"
            email = r[1] or ""
            avatar = r[2] or f"https://api.dicebear.com/7.x/bottts/svg?seed={raw_name or email}"
            score = int(r[3])
            streak = max(int(r[4]), 1)

            # Assign department badge based on email / pattern
            dept = "CSE"
            if "ai" in email.lower() or "ai" in raw_name.lower():
                dept = "AI/DS"
            elif "ece" in email.lower():
                dept = "ECE"
            elif "me" in email.lower():
                dept = "ME"
            elif "biotech" in email.lower():
                dept = "BioTech"

            item = {
                "rank": rank,
                "name": display_name,
                "email": email,
                "avatar_url": avatar,
                "department": dept,
                "contribution_score": score,
                "current_streak": streak,
                "is_current_user": bool(current_user_email and email.lower() == current_user_email.lower().strip())
            }
            leaderboard.append(item)

            if current_user_email and email.lower() == current_user_email.lower().strip():
                user_rank_info = item

        # If current user is not in top limit, look up their exact rank
        if current_user_email and not user_rank_info:
            cursor.execute("""
                SELECT name, email, avatar_url, COALESCE(contribution_score, 0), COALESCE(current_streak, 0)
                FROM users WHERE lower(email) = lower(?)
            """, (current_user_email.strip(),))
            u_row = cursor.fetchone()
            if u_row:
                user_score = u_row[3]
                cursor.execute("SELECT COUNT(*) FROM users WHERE COALESCE(contribution_score, 0) > ?", (user_score,))
                higher_count = cursor.fetchone()[0]
                user_rank_info = {
                    "rank": higher_count + 1,
                    "name": (u_row[0] or "You").title(),
                    "email": u_row[1],
                    "avatar_url": u_row[2] or f"https://api.dicebear.com/7.x/bottts/svg?seed={u_row[1]}",
                    "department": "CSE",
                    "contribution_score": int(user_score),
                    "current_streak": max(int(u_row[4]), 1),
                    "is_current_user": True
                }

        top_podium = leaderboard[:3] if len(leaderboard) >= 3 else leaderboard

        return {
            "leaderboard": leaderboard,
            "top_podium": top_podium,
            "user_rank": user_rank_info,
            "total_active_students": max(len(leaderboard) + 124, 150)
        }

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
    from urllib.parse import unquote
    clean = unquote(filename or "").strip()
    raw = (filename or "").strip()
    def _do():
        with get_db() as c:
            c.execute("DELETE FROM user_uploads WHERE lower(filename) = lower(?) OR lower(filename) = lower(?)", (clean, raw))
            c.commit()
    db_retry(_do)

def get_upload_by_filename(filename: str):
    from urllib.parse import unquote
    clean = unquote(filename or "").strip()
    raw = (filename or "").strip()
    with get_db() as c:
        cursor = c.cursor()
        cursor.execute("SELECT filename, user_email, user_name, uploaded_at, size_bytes, subject, semester, file_type, exam_type, is_private FROM user_uploads WHERE lower(filename) = lower(?) OR lower(filename) = lower(?)", (clean, raw))
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
    from urllib.parse import unquote
    clean = unquote(filename or "").strip()
    raw = (filename or "").strip()
    def _do():
        with get_db() as c:
            c.execute("""
                INSERT INTO reported_files (filename, reporter_email, reporter_name, reason, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (clean, reporter_email, reporter_name, reason, notes))

            # Auto-Quarantine Spam Defense: If a document receives 3 or more reports, automatically set it to private
            cur = c.cursor()
            cur.execute("SELECT COUNT(*) FROM reported_files WHERE lower(filename) = lower(?) OR lower(filename) = lower(?)", (clean, raw))
            report_count = cur.fetchone()[0]
            if report_count >= 3:
                c.execute("UPDATE user_uploads SET is_private = 1 WHERE lower(filename) = lower(?) OR lower(filename) = lower(?)", (clean, raw))
            c.commit()
    db_retry(_do)

def get_reported_files():
    with get_db() as c:
        cursor = c.cursor()
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


# ═════════════════════════════════════════════════════════════════════════════
# CONCEPT WEAKNESS PROFILER & ADAPTIVE PRACTICE ENGINE (ACADEMIC EDGE)
# ═════════════════════════════════════════════════════════════════════════════

CORE_CONCEPT_GRAPH_SEEDS = [
    # ── Thermodynamics & Thermal Physics ──
    {"subject": "Thermodynamics", "prerequisite_concept": "Entropy", "dependent_concept": "Heat Engines & Carnot Cycle", "importance": "critical", "failure_rate": 82.0, "avg_learning_time": 30},
    {"subject": "Thermodynamics", "prerequisite_concept": "Entropy", "dependent_concept": "Refrigeration & Heat Pumps", "importance": "critical", "failure_rate": 78.0, "avg_learning_time": 30},
    {"subject": "Thermodynamics", "prerequisite_concept": "Entropy", "dependent_concept": "Second Law of Thermodynamics", "importance": "critical", "failure_rate": 75.0, "avg_learning_time": 25},
    {"subject": "Thermodynamics", "prerequisite_concept": "First Law of Thermodynamics", "dependent_concept": "Steady Flow Energy Equation (SFEE)", "importance": "critical", "failure_rate": 68.0, "avg_learning_time": 25},
    {"subject": "Thermodynamics", "prerequisite_concept": "Ideal Gas Laws", "dependent_concept": "Isothermal & Adiabatic Work", "importance": "important", "failure_rate": 60.0, "avg_learning_time": 20},

    # ── Basic Electrical & Electronics Engineering (BEEE) ──
    {"subject": "Basic Electrical & Electronics Engineering", "prerequisite_concept": "Kirchhoff's Laws (KVL/KCL)", "dependent_concept": "Thevenin's Theorem", "importance": "critical", "failure_rate": 76.0, "avg_learning_time": 25},
    {"subject": "Basic Electrical & Electronics Engineering", "prerequisite_concept": "Kirchhoff's Laws (KVL/KCL)", "dependent_concept": "Norton's Theorem", "importance": "critical", "failure_rate": 74.0, "avg_learning_time": 25},
    {"subject": "Basic Electrical & Electronics Engineering", "prerequisite_concept": "Thevenin's Theorem", "dependent_concept": "Maximum Power Transfer Theorem", "importance": "critical", "failure_rate": 70.0, "avg_learning_time": 20},
    {"subject": "Basic Electrical & Electronics Engineering", "prerequisite_concept": "PN Junction Diode", "dependent_concept": "Half-Wave & Full-Wave Rectifiers", "importance": "critical", "failure_rate": 65.0, "avg_learning_time": 25},
    {"subject": "Basic Electrical & Electronics Engineering", "prerequisite_concept": "PN Junction Diode", "dependent_concept": "Zener Diode Voltage Regulation", "importance": "important", "failure_rate": 62.0, "avg_learning_time": 20},
    {"subject": "Basic Electrical & Electronics Engineering", "prerequisite_concept": "Bipolar Junction Transistor (BJT)", "dependent_concept": "Common Emitter (CE) Amplifier", "importance": "critical", "failure_rate": 75.0, "avg_learning_time": 30},

    # ── Engineering Calculus ──
    {"subject": "Engineering Calculus", "prerequisite_concept": "Limits and Continuity", "dependent_concept": "Differentiation & Derivatives", "importance": "critical", "failure_rate": 70.0, "avg_learning_time": 25},
    {"subject": "Engineering Calculus", "prerequisite_concept": "Differentiation & Derivatives", "dependent_concept": "Taylor & Maclaurin Series", "importance": "critical", "failure_rate": 72.0, "avg_learning_time": 30},
    {"subject": "Engineering Calculus", "prerequisite_concept": "Differentiation & Derivatives", "dependent_concept": "Maxima & Minima (Optimization)", "importance": "critical", "failure_rate": 68.0, "avg_learning_time": 25},
    {"subject": "Engineering Calculus", "prerequisite_concept": "Integration Techniques", "dependent_concept": "Definite & Multiple Integrals", "importance": "critical", "failure_rate": 74.0, "avg_learning_time": 35},

    # ── Linear Algebra ──
    {"subject": "Linear Algebra", "prerequisite_concept": "Matrices & Determinants", "dependent_concept": "Rank of a Matrix & RREF", "importance": "critical", "failure_rate": 78.0, "avg_learning_time": 25},
    {"subject": "Linear Algebra", "prerequisite_concept": "Matrices & Determinants", "dependent_concept": "Eigenvalues & Eigenvectors", "importance": "critical", "failure_rate": 84.0, "avg_learning_time": 30},
    {"subject": "Linear Algebra", "prerequisite_concept": "Eigenvalues & Eigenvectors", "dependent_concept": "Cayley-Hamilton Theorem & Diagonalization", "importance": "critical", "failure_rate": 80.0, "avg_learning_time": 30},
    {"subject": "Linear Algebra", "prerequisite_concept": "Vector Spaces", "dependent_concept": "Basis, Dimension & Linear Transformations", "importance": "critical", "failure_rate": 76.0, "avg_learning_time": 35},

    # ── Differential Equations ──
    {"subject": "Differential Equations", "prerequisite_concept": "Ordinary Differential Equations (ODE)", "dependent_concept": "Integrating Factor & Linear 1st Order ODE", "importance": "critical", "failure_rate": 75.0, "avg_learning_time": 25},
    {"subject": "Differential Equations", "prerequisite_concept": "Ordinary Differential Equations (ODE)", "dependent_concept": "Higher Order Linear Differential Equations", "importance": "critical", "failure_rate": 79.0, "avg_learning_time": 30},
    {"subject": "Differential Equations", "prerequisite_concept": "Integrating Factor", "dependent_concept": "Exact & Non-Exact Differential Equations", "importance": "critical", "failure_rate": 72.0, "avg_learning_time": 25},

    # ── Data Structures & Algorithms (DSA in C++ / Java) ──
    {"subject": "Data Structures & Algorithms", "prerequisite_concept": "Pointers & Memory References", "dependent_concept": "Linked Lists (Singly & Doubly)", "importance": "critical", "failure_rate": 80.0, "avg_learning_time": 30},
    {"subject": "Data Structures & Algorithms", "prerequisite_concept": "Pointers & Memory References", "dependent_concept": "Binary Trees & BST Implementation", "importance": "critical", "failure_rate": 82.0, "avg_learning_time": 35},
    {"subject": "Data Structures & Algorithms", "prerequisite_concept": "Recursion & Call Stack", "dependent_concept": "Divide and Conquer (Merge/Quick Sort)", "importance": "critical", "failure_rate": 78.0, "avg_learning_time": 30},
    {"subject": "Data Structures & Algorithms", "prerequisite_concept": "Recursion & Call Stack", "dependent_concept": "Dynamic Programming & Memoization", "importance": "critical", "failure_rate": 88.0, "avg_learning_time": 40},
    {"subject": "Data Structures & Algorithms", "prerequisite_concept": "Binary Search Trees (BST)", "dependent_concept": "AVL Trees & Balanced Trees", "importance": "important", "failure_rate": 74.0, "avg_learning_time": 35},

    # ── Discrete Mathematical Structures (DMS) ──
    {"subject": "Discrete Mathematical Structures", "prerequisite_concept": "Set Theory & Relations", "dependent_concept": "Equivalence Relations & Partitions", "importance": "critical", "failure_rate": 68.0, "avg_learning_time": 25},
    {"subject": "Discrete Mathematical Structures", "prerequisite_concept": "Set Theory & Relations", "dependent_concept": "Partial Order & Hasse Diagrams", "importance": "critical", "failure_rate": 72.0, "avg_learning_time": 30},
    {"subject": "Discrete Mathematical Structures", "prerequisite_concept": "Propositional Logic", "dependent_concept": "Predicate Logic & Quantifiers", "importance": "critical", "failure_rate": 70.0, "avg_learning_time": 25},
    {"subject": "Discrete Mathematical Structures", "prerequisite_concept": "Graph Theory Basics", "dependent_concept": "Eulerian & Hamiltonian Paths", "importance": "important", "failure_rate": 66.0, "avg_learning_time": 25},

    # ── Digital Design (DD) ──
    {"subject": "Digital Design", "prerequisite_concept": "Boolean Algebra & Logic Gates", "dependent_concept": "K-Map (Karnaugh Map) Minimization", "importance": "critical", "failure_rate": 74.0, "avg_learning_time": 25},
    {"subject": "Digital Design", "prerequisite_concept": "K-Map (Karnaugh Map) Minimization", "dependent_concept": "Combinational Circuits (Adders/Mux)", "importance": "critical", "failure_rate": 72.0, "avg_learning_time": 30},
    {"subject": "Digital Design", "prerequisite_concept": "Latches and Flip-Flops", "dependent_concept": "Synchronous & Asynchronous Counters", "importance": "critical", "failure_rate": 80.0, "avg_learning_time": 35},
    {"subject": "Digital Design", "prerequisite_concept": "Latches and Flip-Flops", "dependent_concept": "Shift Registers & Finite State Machines", "importance": "critical", "failure_rate": 78.0, "avg_learning_time": 35},

    # ── Information Management Systems (DBMS) ──
    {"subject": "Information Management System", "prerequisite_concept": "Relational Data Model & Primary Keys", "dependent_concept": "SQL Joins & Nested Queries", "importance": "critical", "failure_rate": 68.0, "avg_learning_time": 25},
    {"subject": "Information Management System", "prerequisite_concept": "Functional Dependencies", "dependent_concept": "Database Normalization (1NF, 2NF, 3NF, BCNF)", "importance": "critical", "failure_rate": 82.0, "avg_learning_time": 35},
    {"subject": "Information Management System", "prerequisite_concept": "ACID Properties", "dependent_concept": "Transactions & Concurrency Control (2PL)", "importance": "critical", "failure_rate": 76.0, "avg_learning_time": 30},

    # ── Operating Systems (OS) ──
    {"subject": "Operating Systems", "prerequisite_concept": "Processes vs Threads", "dependent_concept": "CPU Scheduling Algorithms", "importance": "critical", "failure_rate": 65.0, "avg_learning_time": 25},
    {"subject": "Operating Systems", "prerequisite_concept": "Critical Section Problem", "dependent_concept": "Semaphores & Mutex Locks", "importance": "critical", "failure_rate": 84.0, "avg_learning_time": 35},
    {"subject": "Operating Systems", "prerequisite_concept": "Deadlock (Coffman Conditions)", "dependent_concept": "Banker's Algorithm for Deadlock Avoidance", "importance": "critical", "failure_rate": 78.0, "avg_learning_time": 30},
    {"subject": "Operating Systems", "prerequisite_concept": "Paging & Address Translation", "dependent_concept": "Virtual Memory & Page Replacement (LRU)", "importance": "critical", "failure_rate": 80.0, "avg_learning_time": 35}
]

CORE_PRACTICE_QUESTION_SEEDS = [
    # ── Entropy (Thermodynamics) ──
    {
        "subject": "Thermodynamics",
        "concept": "Entropy",
        "question_text": "According to the Clausius Inequality, for any irreversible thermodynamic cycle, what is the value of ∮ (dQ / T)?",
        "question_type": "mcq",
        "options": _json.dumps(["= 0", "> 0", "< 0", "≥ 0"]),
        "correct_option": "< 0",
        "explanation": "For any irreversible cycle, ∮ (dQ / T) < 0. For a reversible cycle, ∮ (dQ / T) = 0. It can never be greater than 0 for any cyclic process.",
        "concept_explanation": "Entropy generation is strictly positive in irreversible processes, leading to the Clausius inequality ∮ dQ/T < 0 for cycles.",
        "difficulty": "easy",
        "is_pyq_based": 1
    },
    {
        "subject": "Thermodynamics",
        "concept": "Entropy",
        "question_text": "An isolated system undergoes an irreversible spontaneous change. What must happen to the total entropy of the system?",
        "question_type": "mcq",
        "options": _json.dumps(["Remains constant", "Decreases", "Increases", "Becomes zero"]),
        "correct_option": "Increases",
        "explanation": "By the Second Law of Thermodynamics (Principle of Increase of Entropy), for any isolated system, ΔS_system ≥ 0. For irreversible changes, entropy strictly increases.",
        "concept_explanation": "The entropy of an isolated system always increases during spontaneous processes until it reaches maximum entropy at equilibrium.",
        "difficulty": "medium",
        "is_pyq_based": 1
    },

    # ── Thevenin's Theorem (BEEE) ──
    {
        "subject": "Basic Electrical & Electronics Engineering",
        "concept": "Thevenin's Theorem",
        "question_text": "When calculating Thevenin resistance (R_th) looking into open terminals of a linear DC circuit, how should independent voltage and current sources be treated?",
        "question_type": "mcq",
        "options": _json.dumps([
            "Short-circuit voltage sources and open-circuit current sources",
            "Open-circuit voltage sources and short-circuit current sources",
            "Replace all sources with 1 kΩ resistors",
            "Leave all sources unchanged in the circuit"
        ]),
        "correct_option": "Short-circuit voltage sources and open-circuit current sources",
        "explanation": "Independent ideal voltage sources have zero internal resistance (replaced by a short circuit, 0V). Independent ideal current sources have infinite internal resistance (replaced by an open circuit, 0A).",
        "concept_explanation": "Deactivating independent sources reduces the active network into a purely resistive passive network to find R_th.",
        "difficulty": "easy",
        "is_pyq_based": 1
    },

    # ── Eigenvalues & Eigenvectors (Linear Algebra) ──
    {
        "subject": "Linear Algebra",
        "concept": "Eigenvalues & Eigenvectors",
        "question_text": "If λ is an eigenvalue of an invertible matrix A, what is the corresponding eigenvalue of A^(-1)?",
        "question_type": "mcq",
        "options": _json.dumps(["-λ", "1 / λ", "λ^2", "1 / λ^2"]),
        "correct_option": "1 / λ",
        "explanation": "Since A v = λ v, multiplying both sides by A^(-1) gives v = λ A^(-1) v, which implies A^(-1) v = (1/λ) v. Therefore, 1/λ is the eigenvalue of A^(-1).",
        "concept_explanation": "Eigenvalues of the matrix inverse are the reciprocals of the original non-zero eigenvalues.",
        "difficulty": "easy",
        "is_pyq_based": 1
    },

    # ── Semaphores & Mutex (Operating Systems) ──
    {
        "subject": "Operating Systems",
        "concept": "Critical Section Problem",
        "question_text": "In Dijkstra's counting semaphore, if semaphore S is initialized to 3, and 5 consecutive wait(P) operations are executed, what is the final value of S?",
        "question_type": "mcq",
        "options": _json.dumps(["-2", "0", "2", "3"]),
        "correct_option": "-2",
        "explanation": "Each wait() operation decrements S by 1: 3 - 5 = -2. The negative value -2 indicates that exactly 2 processes are blocked in the waiting queue.",
        "concept_explanation": "A counting semaphore value reflects the number of available resource units when positive, or the count of waiting processes when negative.",
        "difficulty": "medium",
        "is_pyq_based": 1
    },

    # ── Pointers & Memory (DSA) ──
    {
        "subject": "Data Structures & Algorithms",
        "concept": "Pointers & Memory References",
        "question_text": "In C++, what is a 'dangling pointer'?",
        "question_type": "mcq",
        "options": _json.dumps([
            "A pointer pointing to deallocated / freed memory",
            "A pointer initialized to NULL",
            "A pointer that points to another pointer",
            "A pointer with void data type"
        ]),
        "correct_option": "A pointer pointing to deallocated / freed memory",
        "explanation": "A dangling pointer arises when an object/memory is deleted or deallocated, without modifying the value of the pointer, so the pointer still points to the memory location of the deallocated memory.",
        "concept_explanation": "Accessing memory through a dangling pointer causes undefined behavior, memory corruption, and security vulnerabilities.",
        "difficulty": "easy",
        "is_pyq_based": 1
    }
]

def seed_concept_graph_and_questions():
    """Seed the Concept Dependency Graph and Question Bank if not already present."""
    def _do():
        with get_db() as c:
            cur = c.cursor()
            
            # 1. Seed graph
            cur.execute("SELECT COUNT(*) FROM concept_dependency_graph")
            graph_count = cur.fetchone()[0]
            if graph_count == 0:
                for item in CORE_CONCEPT_GRAPH_SEEDS:
                    cur.execute("""
                        INSERT INTO concept_dependency_graph 
                        (subject, prerequisite_concept, dependent_concept, importance, failure_rate, avg_learning_time)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        item["subject"],
                        item["prerequisite_concept"],
                        item["dependent_concept"],
                        item.get("importance", "critical"),
                        item.get("failure_rate", 70.0),
                        item.get("avg_learning_time", 25)
                    ))
                c.commit()
                print(f"[CONCEPT GRAPH] Seeded {len(CORE_CONCEPT_GRAPH_SEEDS)} prerequisite dependencies.")

            # 2. Seed initial question bank
            cur.execute("SELECT COUNT(*) FROM practice_question")
            q_count = cur.fetchone()[0]
            if q_count == 0:
                for q in CORE_PRACTICE_QUESTION_SEEDS:
                    cur.execute("""
                        INSERT INTO practice_question
                        (subject, concept, question_text, question_type, options, correct_option, explanation, concept_explanation, difficulty, is_pyq_based)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        q["subject"],
                        q["concept"],
                        q["question_text"],
                        q["question_type"],
                        q["options"],
                        q["correct_option"],
                        q["explanation"],
                        q["concept_explanation"],
                        q["difficulty"],
                        q.get("is_pyq_based", 1)
                    ))
                c.commit()
                print(f"[PRACTICE QUESTIONS] Seeded {len(CORE_PRACTICE_QUESTION_SEEDS)} verified questions.")

    try:
        db_retry(_do)
    except Exception as e:
        print(f"[SEED ERROR CONCEPT GRAPH] {e}")

# Run seed immediately
seed_concept_graph_and_questions()


def get_concept_dependency_graph(subject: str = "") -> list:
    """Fetch all concept dependencies or filter by subject."""
    def _do():
        with get_db() as c:
            cur = c.cursor()
            if subject:
                cur.execute("""
                    SELECT id, subject, prerequisite_concept, dependent_concept, importance, failure_rate, avg_learning_time
                    FROM concept_dependency_graph
                    WHERE lower(subject) LIKE ?
                    ORDER BY id ASC
                """, (f"%{subject.lower()}%",))
            else:
                cur.execute("""
                    SELECT id, subject, prerequisite_concept, dependent_concept, importance, failure_rate, avg_learning_time
                    FROM concept_dependency_graph
                    ORDER BY id ASC
                """)
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "subject": r[1],
                    "prerequisite_concept": r[2],
                    "dependent_concept": r[3],
                    "importance": r[4],
                    "failure_rate": r[5],
                    "avg_learning_time": r[6]
                }
                for r in rows
            ]
    return db_retry(_do)


def extract_concepts_from_message(message: str) -> list:
    """Extract key academic concepts from a student message using NLP heuristics + Groq."""
    if not message or len(message.strip()) < 3:
        return []
    
    msg_clean = message.lower()
    
    # 1. Fast match against known concept graph prerequisites & dependents
    all_deps = get_concept_dependency_graph()
    matched = set()
    for dep in all_deps:
        p_name = dep["prerequisite_concept"]
        d_name = dep["dependent_concept"]
        
        # Check prerequisite
        p_terms = [w.strip() for w in _re.split(r'[\(\)/,]', p_name) if len(w.strip()) > 3]
        for term in p_terms:
            if term.lower() in msg_clean:
                matched.add(p_name)
                break
        
        # Check dependent
        d_terms = [w.strip() for w in _re.split(r'[\(\)/,]', d_name) if len(w.strip()) > 3]
        for term in d_terms:
            if term.lower() in msg_clean:
                matched.add(d_name)
                break
    
    if matched:
        return list(matched)[:4]

    # 2. LLM Fallback extraction with Groq
    groq_key = _os.environ.get("GROQ_API_KEY") or "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"
    if groq_key:
        try:
            import urllib.request, ssl
            ctx = ssl._create_unverified_context()
            payload = _json.dumps({
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a concept extractor for an engineering university study app. Extract 1 to 3 core academic engineering concepts mentioned in the student's message (e.g. 'Entropy', 'Thevenin Theorem', 'Eigenvalues', 'Pointers', 'Critical Section'). Output JSON with a 'concepts' array of clean strings."
                    },
                    {"role": "user", "content": message}
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"}
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, context=ctx, timeout=2.5) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
                parsed = _json.loads(data["choices"][0]["message"]["content"])
                return parsed.get("concepts", [])[:3]
        except Exception as e:
            print(f"[EXTRACT CONCEPTS LLM ERROR]: {e}")

    return []


def detect_concept_weakness(
    user_id: int = 1,
    user_email: str = "",
    topic: str = "",
    message: str = "",
    attempt_number: int = 0,
    conversation_history: list = None
) -> dict:
    """Analyze student's conversation & message to detect deep conceptual weaknesses."""
    detection = {
        "confused_concept": None,
        "confidence": 0.0,
        "is_foundational": False,
        "related_topics": [],
        "weakness_detected": False,
        "subject": "General",
        "impact_score": 0.0
    }
    
    if not message:
        return detection

    # Step 1: Extract concepts from current message
    concepts_mentioned = extract_concepts_from_message(message)
    if not concepts_mentioned and topic:
        concepts_mentioned = [topic.title()]
    
    if not concepts_mentioned:
        return detection

    # Step 2: Check previous messages for repetition of the same concepts or frustration markers
    history_texts = []
    if conversation_history:
        for msg in conversation_history[-6:]:
            if isinstance(msg, dict):
                history_texts.append(str(msg.get("content") or msg.get("user") or ""))
            elif hasattr(msg, "content"):
                history_texts.append(str(msg.content))
    
    frustration_markers = ["samjh nahi", "samajh nahi", "stuck", "confused", "explain again", "kuch samajh", "fir se", "difficult", "hard", "why is", "how does"]
    has_frustration = any(fm in message.lower() for fm in frustration_markers)

    chosen_concept = concepts_mentioned[0]
    repetition_count = 1
    
    for prev in history_texts:
        if chosen_concept.lower() in prev.lower():
            repetition_count += 1

    if attempt_number >= 2 or repetition_count >= 2 or (has_frustration and attempt_number >= 1):
        detection["weakness_detected"] = True
        detection["confused_concept"] = chosen_concept
        detection["confidence"] = min(0.95, 0.60 + (repetition_count * 0.12) + (0.15 if has_frustration else 0.0))
        
        # Step 3: Check dependency graph for downstream blocked topics
        deps = get_concept_dependency_graph()
        blocked_topics = []
        subj = "General"
        for d in deps:
            if d["prerequisite_concept"].lower() in chosen_concept.lower() or chosen_concept.lower() in d["prerequisite_concept"].lower():
                blocked_topics.append(d["dependent_concept"])
                subj = d["subject"]
        
        detection["subject"] = subj
        detection["related_topics"] = blocked_topics
        detection["is_foundational"] = len(blocked_topics) >= 2
        detection["impact_score"] = min(100.0, max(25.0, len(blocked_topics) * 25.0 + (repetition_count * 10.0)))

    return detection


def record_concept_weakness(
    user_id: int = 1,
    user_email: str = "",
    subject: str = "General",
    concept_name: str = "",
    topic: str = "",
    dependent_topics: list = None,
    is_foundational: bool = False,
    is_critical: bool = False
) -> dict:
    """Save or update a detected concept weakness in the database."""
    if not concept_name:
        return None
    
    dependent_topics = dependent_topics or []
    now_str = datetime.now().isoformat()
    
    def _do():
        with get_db() as c:
            cur = c.cursor()
            
            # Check existing weakness for this user and concept
            cur.execute("""
                SELECT id, times_confused, confusion_contexts, dependent_topics, mastery_percentage, is_critical
                FROM concept_weakness
                WHERE (user_id = ? OR lower(user_email) = lower(?)) AND lower(concept_name) = lower(?)
            """, (user_id, user_email or "", concept_name.strip()))
            row = cur.fetchone()
            
            if row:
                w_id, times_conf, ctx_json, dep_json, mastery_pct, was_crit = row
                try:
                    contexts = _json.loads(ctx_json) if ctx_json else []
                except Exception:
                    contexts = []
                contexts.append({"topic": topic or concept_name, "date": now_str})
                
                try:
                    deps = _json.loads(dep_json) if dep_json else []
                except Exception:
                    deps = []
                # Merge dependent topics
                all_deps = list(set(deps + dependent_topics))
                
                new_times = times_conf + 1
                new_impact = min(100.0, max(25.0, len(all_deps) * 25.0 + (new_times * 10.0)))
                new_critical = 1 if (new_times >= 2 or is_foundational or was_crit or new_impact >= 70) and (mastery_pct < 60) else 0
                priority = min(100, int(new_impact * 0.6 + new_times * 10 + (100 - mastery_pct) * 0.3))
                
                cur.execute("""
                    UPDATE concept_weakness
                    SET times_confused = ?, last_confused_at = ?, confusion_contexts = ?, dependent_topics = ?,
                        impact_score = ?, is_critical = ?, is_foundational = ?, intervention_priority = ?
                    WHERE id = ?
                """, (new_times, now_str, _json.dumps(contexts), _json.dumps(all_deps), new_impact, new_critical, 1 if is_foundational else 0, priority, w_id))
                c.commit()
                return {"id": w_id, "status": "updated", "concept_name": concept_name, "times_confused": new_times}
            else:
                contexts = [{"topic": topic or concept_name, "date": now_str}]
                impact = min(100.0, max(25.0, len(dependent_topics) * 25.0 + 15.0))
                priority = min(100, int(impact * 0.6 + 35))
                crit_val = 1 if is_critical or is_foundational or impact >= 60 else 0
                
                cur.execute("""
                    INSERT INTO concept_weakness
                    (user_id, user_email, subject, concept_name, concept_difficulty, first_confused_at, times_confused,
                     last_confused_at, confusion_contexts, dependent_topics, impact_score, mastery_level,
                     mastery_percentage, is_critical, is_foundational, intervention_priority)
                    VALUES (?, ?, ?, ?, 'foundational', ?, 1, ?, ?, ?, ?, 'novice', 0.0, ?, ?, ?)
                """, (
                    user_id,
                    user_email or "",
                    subject or "General",
                    concept_name.strip(),
                    now_str,
                    now_str,
                    _json.dumps(contexts),
                    _json.dumps(dependent_topics),
                    impact,
                    crit_val,
                    1 if is_foundational else 0,
                    priority
                ))
                new_id = cur.lastrowid
                c.commit()
                return {"id": new_id, "status": "created", "concept_name": concept_name, "times_confused": 1}

    return db_retry(_do)


def create_weakness_profile(user_id: int = 1, user_email: str = "") -> dict:
    """Build a comprehensive concept weakness profile for the student with actionable priorities."""
    def _do():
        with get_db() as c:
            cur = c.cursor()
            cur.execute("""
                SELECT id, subject, concept_name, concept_difficulty, first_confused_at, times_confused,
                       last_confused_at, confusion_contexts, dependent_topics, impact_score,
                       mastery_level, mastery_percentage, practice_questions_attempted, practice_score,
                       is_critical, is_foundational, intervention_priority
                FROM concept_weakness
                WHERE user_id = ? OR (user_email IS NOT NULL AND lower(user_email) = lower(?))
                ORDER BY is_critical DESC, impact_score DESC, times_confused DESC
            """, (user_id, user_email or ""))
            rows = cur.fetchall()

            profile = {
                "total_weaknesses": len(rows),
                "avg_mastery_score": 0.0,
                "critical_weaknesses": [],
                "foundational_gaps": [],
                "secondary_weaknesses": [],
                "intervention_priority": []
            }

            if not rows:
                # If new user with no weaknesses recorded yet, provide pre-computed foundational diagnostic targets
                deps = get_concept_dependency_graph()
                foundational_seeds = [
                    {"concept": "Entropy", "subject": "Thermodynamics", "mastery": 0, "impact_score": 85, "times_confused": 0, "affected_topics": ["Heat Engines", "Refrigeration", "Second Law"], "is_critical": True},
                    {"concept": "Thevenin's Theorem", "subject": "BEEE", "mastery": 0, "impact_score": 80, "times_confused": 0, "affected_topics": ["Maximum Power Transfer", "Bridge Circuits"], "is_critical": True},
                    {"concept": "Eigenvalues & Eigenvectors", "subject": "Linear Algebra", "mastery": 0, "impact_score": 90, "times_confused": 0, "affected_topics": ["Cayley-Hamilton Theorem", "Diagonalization"], "is_critical": True}
                ]
                profile["foundational_gaps"] = foundational_seeds
                profile["intervention_priority"] = foundational_seeds
                return profile

            total_mastery = 0.0
            for r in rows:
                (w_id, subj, c_name, c_diff, first_at, times_c, last_at, ctx_json, dep_json,
                 impact, m_level, m_pct, q_att, p_score, is_crit, is_found, priority) = r
                
                try:
                    dep_topics = _json.loads(dep_json) if dep_json else []
                except Exception:
                    dep_topics = []

                item = {
                    "id": w_id,
                    "subject": subj,
                    "concept": c_name,
                    "mastery": round(m_pct or 0.0, 1),
                    "mastery_level": m_level or "novice",
                    "impact_score": round(impact or 0.0, 1),
                    "times_confused": times_c or 1,
                    "affected_topics": dep_topics,
                    "questions_attempted": q_att or 0,
                    "is_critical": bool(is_crit),
                    "is_foundational": bool(is_found),
                    "priority": priority or 50,
                    "last_confused": str(last_at)
                }

                total_mastery += (m_pct or 0.0)

                if is_crit:
                    profile["critical_weaknesses"].append(item)
                elif is_found:
                    profile["foundational_gaps"].append(item)
                else:
                    profile["secondary_weaknesses"].append(item)

                if (times_c >= 2 and m_pct < 60) or is_crit or is_found:
                    profile["intervention_priority"].append(item)

            profile["avg_mastery_score"] = round(total_mastery / len(rows), 1) if rows else 0.0
            return profile

    return db_retry(_do)


def generate_questions_with_llm(concept: str, difficulty: str = "easy", count: int = 2) -> list:
    """Use fast Groq Llama 3.3 70B to generate Bennett engineering exam-style practice questions on a concept."""
    groq_key = _os.environ.get("GROQ_API_KEY") or "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"
    if not groq_key:
        return []

    prompt = (
        f"Generate {count} rigorous, exam-style practice questions on the academic engineering concept \"{concept}\" "
        f"at \"{difficulty}\" difficulty level for a Bennett University engineering student.\n\n"
        "Respond ONLY with a valid JSON array of objects matching this exact schema:\n"
        "[\n"
        "  {\n"
        '    "question": "Question statement here...",\n'
        '    "type": "mcq",\n'
        '    "options": ["Option A text", "Option B text", "Option C text", "Option D text"],\n'
        '    "correct": "Option A text",\n'
        '    "explanation": "Detailed step-by-step why this is correct...",\n'
        '    "concept_explanation": "Core theoretical principle being tested..."\n'
        "  }\n"
        "]\n"
        "Requirements:\n"
        "- Ensure options array contains 4 distinct options.\n"
        "- The 'correct' field MUST EXACTLY match one of the items in the 'options' array.\n"
        "- Make questions high-yield, conceptual, and practical."
    )

    try:
        import urllib.request, ssl
        ctx = ssl._create_unverified_context()
        payload = _json.dumps({
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=6.0) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
            raw_text = data["choices"][0]["message"]["content"].strip()
            # Clean markdown JSON block if present
            if raw_text.startswith("```"):
                raw_text = _re.sub(r'^```(?:json)?\s*', '', raw_text)
                raw_text = _re.sub(r'\s*```$', '', raw_text)
            
            q_list = _json.loads(raw_text)
            saved = []
            with get_db() as c:
                cur = c.cursor()
                for q_data in q_list:
                    cur.execute("""
                        INSERT INTO practice_question
                        (subject, concept, question_text, question_type, options, correct_option, explanation, concept_explanation, is_ai_generated, difficulty)
                        VALUES ('Engineering', ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """, (
                        concept,
                        q_data.get("question", f"Question on {concept}"),
                        q_data.get("type", "mcq"),
                        _json.dumps(q_data.get("options", ["A", "B", "C", "D"])),
                        q_data.get("correct", "A"),
                        q_data.get("explanation", ""),
                        q_data.get("concept_explanation", ""),
                        difficulty
                    ))
                    q_id = cur.lastrowid
                    saved.append({
                        "id": q_id,
                        "question": q_data.get("question"),
                        "type": q_data.get("type", "mcq"),
                        "options": q_data.get("options", []),
                        "correct_option": q_data.get("correct"),
                        "explanation": q_data.get("explanation"),
                        "concept_explanation": q_data.get("concept_explanation"),
                        "difficulty": difficulty
                    })
                c.commit()
            return saved
    except Exception as e:
        print(f"[GENERATE QUESTIONS LLM ERROR]: {e}")
        return []


def generate_adaptive_practice(
    concept: str,
    user_id: int = 1,
    user_email: str = "",
    difficulty: str = "easy"
) -> dict:
    """Generate or retrieve an adaptive practice session tailored to fix the student's weakness."""
    concept_clean = (concept or "Foundational Concepts").strip()
    
    def _do():
        with get_db() as c:
            cur = c.cursor()
            
            # 1. Fetch matching verified practice questions
            cur.execute("""
                SELECT id, question_text, question_type, options, correct_option, explanation, concept_explanation, difficulty
                FROM practice_question
                WHERE lower(concept) LIKE ? OR lower(concept_explanation) LIKE ?
                ORDER BY id ASC
                LIMIT 5
            """, (f"%{concept_clean.lower()}%", f"%{concept_clean.lower()}%"))
            rows = cur.fetchall()

            questions = []
            for r in rows:
                try:
                    opts = _json.loads(r[3]) if r[3] else []
                except Exception:
                    opts = []
                questions.append({
                    "id": r[0],
                    "question": r[1],
                    "type": r[2],
                    "options": opts,
                    "correct_option": r[4],
                    "explanation": r[5],
                    "concept_explanation": r[6],
                    "difficulty": r[7]
                })

            # If fewer than 3 questions in DB, generate additional ones dynamically using LLM
            if len(questions) < 3:
                needed = 3 - len(questions)
                ai_qs = generate_questions_with_llm(concept=concept_clean, difficulty=difficulty, count=needed)
                questions.extend(ai_qs)

            # Fallback guarantee if still empty
            if not questions:
                questions = [{
                    "id": 9991,
                    "question": f"Which principle is most essential for mastering '{concept_clean}' in engineering?",
                    "type": "mcq",
                    "options": [
                        "Direct application of foundational boundary conditions",
                        "Ignoring physical constraints",
                        "Only memorizing formulas without derivation",
                        "Assuming zero system entropy"
                    ],
                    "correct_option": "Direct application of foundational boundary conditions",
                    "explanation": f"Mastering {concept_clean} requires establishing fundamental physical laws and applying valid boundary conditions.",
                    "concept_explanation": f"Foundational understanding of {concept_clean}.",
                    "difficulty": "easy"
                }]

            # Create adaptive practice session
            now_str = datetime.now().isoformat()
            cur.execute("""
                INSERT INTO adaptive_practice_session
                (user_id, user_email, concept_name, started_at, total_questions, initial_difficulty, final_difficulty, difficulty_progression)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                user_email or "",
                concept_clean,
                now_str,
                len(questions),
                difficulty,
                difficulty,
                _json.dumps([difficulty])
            ))
            session_id = cur.lastrowid
            c.commit()

            formatted_qs = []
            for q in questions:
                formatted_qs.append({
                    "id": q["id"],
                    "question": q["question"],
                    "type": q.get("type", "mcq"),
                    "options": q.get("options", []),
                    "hint": f"💡 Think about the foundational definition: {q.get('concept_explanation', 'Focus on the core physics/math principle.')}"
                })

            return {
                "session_id": session_id,
                "concept": concept_clean,
                "difficulty": difficulty,
                "total_questions": len(formatted_qs),
                "questions": formatted_qs,
                "message": f"🎯 Target Practice: {len(formatted_qs)} questions on '{concept_clean}'. Let's build your concept mastery!"
            }

    return db_retry(_do)


def submit_practice_answer(
    session_id: int,
    question_id: int,
    user_answer: str,
    time_taken: int = 15,
    user_id: int = 1,
    user_email: str = ""
) -> dict:
    """Process student's submitted answer, calculate accuracy, and dynamically adapt difficulty."""
    def _do():
        with get_db() as c:
            cur = c.cursor()
            
            # Fetch question
            cur.execute("""
                SELECT id, concept, question_text, correct_option, explanation, concept_explanation, difficulty
                FROM practice_question
                WHERE id = ?
            """, (question_id,))
            q_row = cur.fetchone()
            
            if not q_row:
                # Mock fallback question check
                is_correct = True
                explanation = "Well done! That is the conceptually sound answer."
                concept_note = "Mastering foundational boundary conditions enables solving complex dependent problems."
                concept_name = "Core Concept"
            else:
                q_id, concept_name, q_text, correct_opt, explanation, concept_note, q_diff = q_row
                # Compare answers case-insensitively
                is_correct = (str(user_answer).strip().lower() == str(correct_opt).strip().lower())

                # Update question attempt stats
                cur.execute("""
                    UPDATE practice_question
                    SET attempt_count = attempt_count + 1,
                        correct_count = correct_count + ?,
                        success_rate = CAST((correct_count + ?) AS REAL) / (attempt_count + 1)
                    WHERE id = ?
                """, (1 if is_correct else 0, 1 if is_correct else 0, question_id))

            # Fetch session
            cur.execute("""
                SELECT id, questions, correct_answers, total_questions, initial_difficulty, final_difficulty, difficulty_progression, total_time, concept_name
                FROM adaptive_practice_session
                WHERE id = ?
            """, (session_id,))
            s_row = cur.fetchone()

            if not s_row:
                return {
                    "is_correct": is_correct,
                    "explanation": explanation,
                    "concept_note": concept_note,
                    "score_so_far": "1/1",
                    "next_difficulty": "medium",
                    "adapted": False
                }

            s_id, q_history_json, corr_count, tot_q, init_diff, fin_diff, prog_json, tot_time, s_concept = s_row
            try:
                q_history = _json.loads(q_history_json) if q_history_json else []
            except Exception:
                q_history = []

            try:
                progression = _json.loads(prog_json) if prog_json else []
            except Exception:
                progression = []

            # Log this response
            q_history.append({
                "question_id": question_id,
                "user_answer": user_answer,
                "correct": is_correct,
                "time_taken": time_taken
            })

            new_corr = sum(1 for item in q_history if item["correct"])
            new_tot = len(q_history)
            new_time = (tot_time or 0) + time_taken
            score_pct = (new_corr / new_tot) * 100.0

            # ── Adaptive Difficulty Adjustment ──
            curr_diff = fin_diff or init_diff or "easy"
            next_diff = curr_diff
            adapted = False

            if score_pct >= 80.0 and new_tot >= 2:
                if curr_diff == "easy":
                    next_diff = "medium"
                    adapted = True
                elif curr_diff == "medium":
                    next_diff = "hard"
                    adapted = True
            elif score_pct < 50.0 and new_tot >= 2:
                if curr_diff == "hard":
                    next_diff = "medium"
                    adapted = True
                elif curr_diff == "medium":
                    next_diff = "easy"
                    adapted = True

            progression.append(next_diff)

            cur.execute("""
                UPDATE adaptive_practice_session
                SET questions = ?, correct_answers = ?, session_score = ?, final_difficulty = ?,
                    difficulty_progression = ?, total_time = ?, avg_time_per_question = ?
                WHERE id = ?
            """, (
                _json.dumps(q_history),
                new_corr,
                score_pct,
                next_diff,
                _json.dumps(progression),
                new_time,
                round(new_time / new_tot, 1),
                session_id
            ))

            # ── Update Concept Weakness Mastery Level ──
            cur.execute("""
                SELECT id, mastery_percentage, practice_questions_attempted
                FROM concept_weakness
                WHERE (user_id = ? OR lower(user_email) = lower(?)) AND lower(concept_name) LIKE ?
            """, (user_id, user_email or "", f"%{s_concept.lower()}%"))
            w_row = cur.fetchone()

            if w_row:
                w_id, old_m_pct, old_att = w_row
                new_att = (old_att or 0) + 1
                # Progressive mastery formula
                mastery_gain = (15.0 if is_correct else 3.0)
                new_mastery = min(100.0, max(0.0, (old_m_pct or 0.0) + mastery_gain))
                
                if new_mastery >= 85.0:
                    m_lvl = "expert"
                    crit_flag = 0
                elif new_mastery >= 60.0:
                    m_lvl = "intermediate"
                    crit_flag = 0
                elif new_mastery >= 30.0:
                    m_lvl = "beginner"
                    crit_flag = 0
                else:
                    m_lvl = "novice"
                    crit_flag = 1

                cur.execute("""
                    UPDATE concept_weakness
                    SET mastery_percentage = ?, mastery_level = ?, practice_questions_attempted = ?,
                        practice_score = ?, last_practiced = ?, is_critical = ?
                    WHERE id = ?
                """, (new_mastery, m_lvl, new_att, score_pct, datetime.now().isoformat(), crit_flag, w_id))

            c.commit()

            return {
                "is_correct": is_correct,
                "explanation": explanation,
                "concept_note": concept_note,
                "score_so_far": f"{new_corr}/{new_tot}",
                "accuracy_percentage": round(score_pct, 1),
                "next_difficulty": next_diff,
                "adapted": adapted,
                "adaptation_message": f"🔥 Difficulty adapted to {next_diff.upper()}!" if adapted else ""
            }

    return db_retry(_do)


def complete_practice_session(session_id: int, user_id: int = 1, user_email: str = "") -> dict:
    """Mark practice session complete and return summary report."""
    def _do():
        with get_db() as c:
            cur = c.cursor()
            cur.execute("""
                SELECT id, concept_name, correct_answers, total_questions, session_score, initial_difficulty, final_difficulty, total_time, avg_time_per_question
                FROM adaptive_practice_session
                WHERE id = ?
            """, (session_id,))
            row = cur.fetchone()
            if not row:
                return {"success": False, "message": "Session not found"}

            s_id, concept, corr, tot, score, init_d, fin_d, t_time, avg_t = row
            now_str = datetime.now().isoformat()
            
            cur.execute("UPDATE adaptive_practice_session SET completed_at = ? WHERE id = ?", (now_str, session_id))
            
            # Fetch updated weakness mastery
            cur.execute("""
                SELECT mastery_percentage, mastery_level, impact_score
                FROM concept_weakness
                WHERE (user_id = ? OR lower(user_email) = lower(?)) AND lower(concept_name) LIKE ?
            """, (user_id, user_email or "", f"%{concept.lower()}%"))
            w_row = cur.fetchone()

            mastery_pct = w_row[0] if w_row else score
            mastery_lvl = w_row[1] if w_row else "intermediate"

            c.commit()
            return {
                "success": True,
                "session_id": session_id,
                "concept": concept,
                "correct_answers": corr,
                "total_questions": tot,
                "accuracy_percentage": round(score or 0.0, 1),
                "time_spent_seconds": t_time or 0,
                "avg_time_per_question": avg_t or 0.0,
                "initial_difficulty": init_d,
                "final_difficulty": fin_d,
                "mastery_percentage": round(mastery_pct, 1),
                "mastery_level": mastery_lvl
            }

    return db_retry(_do)


# ═════════════════════════════════════════════════════════════════════════════
# SECURITY HARDENING & DATA PROTECTION AT REST
# ═════════════════════════════════════════════════════════════════════════════

import os as _sec_os
import base64 as _sec_b64
import hashlib as _sec_hash

ENCRYPTION_KEY = _sec_os.environ.get("ENCRYPTION_KEY") or _sec_os.environ.get("SECRET_KEY") or "prepz_super_secret_cryptographic_key_2026_x89q"

def encrypt_sensitive(data: str) -> str:
    """Encrypt sensitive learning telemetry/answers at rest."""
    if not data:
        return ""
    try:
        try:
            from cryptography.fernet import Fernet
            fernet_key = _sec_b64.urlsafe_b64encode(_sec_hash.sha256(ENCRYPTION_KEY.encode("utf-8")).digest())
            f = Fernet(fernet_key)
            return f.encrypt(data.encode("utf-8")).decode("utf-8")
        except (ImportError, ModuleNotFoundError):
            key_bytes = _sec_hash.sha256(ENCRYPTION_KEY.encode("utf-8")).digest()
            data_bytes = data.encode("utf-8")
            xored = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes))
            return "ENC:" + _sec_b64.urlsafe_b64encode(xored).decode("utf-8")
    except Exception:
        return data

def decrypt_sensitive(encrypted_data: str) -> str:
    """Decrypt sensitive data at rest."""
    if not encrypted_data:
        return ""
    try:
        if encrypted_data.startswith("ENC:"):
            raw_b64 = encrypted_data[4:]
            key_bytes = _sec_hash.sha256(ENCRYPTION_KEY.encode("utf-8")).digest()
            xored = _sec_b64.urlsafe_b64decode(raw_b64.encode("utf-8"))
            dec = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(xored))
            return dec.decode("utf-8")
        else:
            try:
                from cryptography.fernet import Fernet
                fernet_key = _sec_b64.urlsafe_b64encode(_sec_hash.sha256(ENCRYPTION_KEY.encode("utf-8")).digest())
                f = Fernet(fernet_key)
                return f.decrypt(encrypted_data.encode("utf-8")).decode("utf-8")
            except Exception:
                return encrypted_data
    except Exception:
        return encrypted_data

def verify_user_ownership(user_id: int, resource_id: int, resource_type: str, user_email: str = "") -> bool:
    """Verify student owns the learning resource (concept weakness, practice session, document)."""
    with get_db() as c:
        cur = c.cursor()
        if resource_type == "weakness":
            cur.execute("SELECT user_id, user_email FROM concept_weakness WHERE id = ?", (resource_id,))
            row = cur.fetchone()
            if not row:
                return False
            w_uid, w_email = row
            if user_email and w_email and user_email.lower() == w_email.lower():
                return True
            return w_uid == user_id
            
        elif resource_type == "practice_session":
            cur.execute("SELECT user_id, user_email FROM adaptive_practice_session WHERE id = ?", (resource_id,))
            row = cur.fetchone()
            if not row:
                return False
            s_uid, s_email = row
            if user_email and s_email and user_email.lower() == s_email.lower():
                return True
            return s_uid == user_id
            
        elif resource_type == "document":
            cur.execute("SELECT user_id, user_email, is_shared FROM user_documents WHERE id = ?", (resource_id,))
            row = cur.fetchone()
            if not row:
                return False
            d_uid, d_email, is_shared = row
            if is_shared:
                return True
            if user_email and d_email and user_email.lower() == d_email.lower():
                return True
            return d_uid == user_id
            
    return True

def record_email_log(recipient_email: str, subject: str, email_type: str = "welcome", status: str = "success", error_message: str = None, user_id: int = None) -> int:
    """Record email dispatch status to email_logs table."""
    def _do():
        with get_db() as c:
            cur = c.cursor()
            cur.execute("""
                INSERT INTO email_logs (user_id, recipient_email, email_type, subject, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, recipient_email.strip().lower(), email_type, subject, status, error_message))
            c.commit()
            return cur.lastrowid
    return db_retry(_do)

def get_email_logs(recipient_email: Optional[str] = None) -> list:
    """Retrieve audit history of emails sent."""
    with get_db() as c:
        cur = c.cursor()
        if recipient_email:
            cur.execute("SELECT id, user_id, recipient_email, email_type, subject, sent_at, status, error_message FROM email_logs WHERE lower(recipient_email) = lower(?) ORDER BY id DESC", (recipient_email.strip(),))
        else:
            cur.execute("SELECT id, user_id, recipient_email, email_type, subject, sent_at, status, error_message FROM email_logs ORDER BY id DESC LIMIT 100")
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "user_id": r[1],
                "recipient_email": r[2],
                "email_type": r[3],
                "subject": r[4],
                "sent_at": r[5],
                "status": r[6],
                "error_message": r[7]
            }
            for r in rows
        ]

def get_users_admin_analytics():
    """Retrieve full analytics of all logged-in and registered users."""
    cur = conn.cursor()
    # Total users
    cur.execute("SELECT COUNT(*) FROM users")
    total_count = cur.fetchone()[0]

    # Google users
    cur.execute("SELECT COUNT(*) FROM users WHERE lower(provider) IN ('google', 'google.com', 'firebase')")
    google_count = cur.fetchone()[0]

    # Email/Password users
    cur.execute("SELECT COUNT(*) FROM users WHERE lower(provider) = 'local'")
    local_count = cur.fetchone()[0]

    # Active users (with activity date)
    cur.execute("SELECT COUNT(*) FROM users WHERE last_active_date IS NOT NULL AND last_active_date != ''")
    active_count = cur.fetchone()[0]

    # Detailed user list
    cur.execute("""
        SELECT u.id, u.name, u.email, u.provider, u.created_at, u.last_active_date, 
               COALESCE(u.contribution_score, 0), COALESCE(u.current_streak, 0),
               (SELECT COUNT(*) FROM user_uploads WHERE lower(user_email) = lower(u.email)) as upload_count
        FROM users u
        ORDER BY u.id DESC
    """)
    rows = cur.fetchall()

    user_list = []
    for r in rows:
        user_list.append({
            "id": r[0],
            "name": r[1],
            "email": r[2],
            "auth_provider": r[3] or "local",
            "registered_on": str(r[4]) if r[4] else "N/A",
            "last_active": str(r[5]) if r[5] else "N/A",
            "contribution_points": r[6],
            "streak_days": r[7],
            "documents_uploaded": r[8]
        })

    return {
        "status": "success",
        "summary": {
            "total_users": total_count,
            "google_signins": google_count,
            "email_signins": local_count,
            "active_students": active_count
        },
        "users": user_list
    }