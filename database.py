import sqlite3
import os
import re as _re
import json as _json
import secrets as _secrets
import time
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

    conn.commit()

init_user_db()

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
        "subject": "Introduction to Electrical & Electronics",
        "topic": "Thevenin Theorem & Network Theorems",
        "playlist_url": "https://youtube.com/playlist?list=PL9RcWoqXmzaLTYUdnzKhF4bYug3GjGcEc",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "foundation"],
        "avg_duration": 25,
        "total_videos": 45,
        "helpfulness_score": 4.8,
        "total_ratings": 34,
        "helpful_count": 32
    },
    {
        "channel_name": "NESO Academy",
        "instructor": "NESO Academy",
        "subject": "Introduction to Electrical & Electronics",
        "topic": "Electrical Engineering Basics & Circuits",
        "playlist_url": "https://www.youtube.com/@nesoacademy/playlists",
        "difficulty": "Intermediate",
        "best_for": ["deep learning", "exam prep"],
        "avg_duration": 20,
        "total_videos": 38,
        "helpfulness_score": 4.9,
        "total_ratings": 56,
        "helpful_count": 54
    },
    {
        "channel_name": "Gajendra Purohit",
        "instructor": "Dr. Gajendra Purohit",
        "subject": "Engineering Calculus",
        "topic": "Differentiation & Integration",
        "playlist_url": "https://www.youtube.com/playlist?list=PLU6SqdYcYsfIJRl8mo2Rv1MpdvmVD0YyI",
        "difficulty": "Beginner",
        "best_for": ["exam prep", "foundation"],
        "avg_duration": 18,
        "total_videos": 52,
        "helpfulness_score": 4.9,
        "total_ratings": 89,
        "helpful_count": 87
    },
    {
        "channel_name": "Bhagwan Singh Vishwakarma",
        "instructor": "Bhagwan Singh Vishwakarma",
        "subject": "Engineering Calculus",
        "topic": "Advanced Calculus & Differential Equations",
        "playlist_url": "https://www.youtube.com/playlist?list=PLdM-WZokR4tbCBA4mkvfk2vOH12eRPT2Y",
        "difficulty": "Advanced",
        "best_for": ["deep learning", "competitive exams"],
        "avg_duration": 25,
        "total_videos": 48,
        "helpfulness_score": 4.7,
        "total_ratings": 42,
        "helpful_count": 39
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
        "helpful_count": 208
    }
]

def seed_bennett_channels_if_needed():
    """Populate database with Bennett University recommended channels if table empty."""
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
        count = cursor.execute("SELECT COUNT(*) FROM youtube_playlist").fetchone()[0]
        if count == 0:
            for ch in BENNETT_CHANNELS:
                cursor.execute("""
                    INSERT INTO youtube_playlist (
                        channel_name, instructor, subject, topic, playlist_url,
                        difficulty, university, semester, helpfulness_score,
                        total_ratings, helpful_count, total_videos, avg_duration, best_for
                    ) VALUES (?, ?, ?, ?, ?, ?, 'Bennett University', 1, ?, ?, ?, ?, ?, ?)
                """, (
                    ch["channel_name"], ch["instructor"], ch["subject"], ch["topic"], ch["playlist_url"],
                    ch["difficulty"], ch.get("helpfulness_score", 4.5), ch.get("total_ratings", 20),
                    ch.get("helpful_count", 19), ch.get("total_videos", 40), ch.get("avg_duration", 20),
                    _json.dumps(ch.get("best_for", ["exam prep", "foundation"]))
                ))
            conn.commit()
            print(f"[SEED] Seeded {len(BENNETT_CHANNELS)} Bennett University channels.")
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
    "calculus": ["calculus", "differential calculus", "integral calculus", "differentiation", "integration", "derivative", "derivatives", "integral", "integrals", "limit", "limits", "continuity", "maxima", "minima", "taylor series", "maclaurin", "multivariable calculus"],
    "differential equations": ["differential equation", "differential equations", "ode", "pde", "exact differential", "bernoulli equation", "linear differential"],
    "linear algebra": ["eigenvalue", "eigenvalues", "eigenvector", "eigenvectors", "matrix", "matrices", "determinant", "determinants", "rank of matrix", "linear transformation", "vector space"],
    "thevenin theorem": ["thevenin", "thevenin's", "thevenins", "norton", "nortons", "kvl", "kcl", "maximum power transfer", "superposition theorem", "superposition", "reciprocity theorem", "network theorem", "network theorems"],
    "electrical circuits": ["circuit", "circuits", "dependent source", "phasor", "impedance", "mesh analysis", "nodal analysis", "rlc circuit", "ac circuit", "kirchhoff"],
    "electrical machines": ["electrical", "motor", "transformer", "transformers", "rotating magnetic field", "rmf", "synchronous motor", "dc motor", "stator", "rotor", "armature", "torque slip"],
    "power systems": ["power factor", "three phase", "transmission line", "load flow", "fault analysis", "generator", "bus admittance"],
    "control systems": ["bode plot", "root locus", "nyquist plot", "transfer function", "pid controller", "state space", "stability"],
    "operating systems": ["operating system", "operating systems", "deadlock", "deadlocks", "scheduling", "semaphore", "semaphores", "paging", "virtual memory", "process management", "banker's algorithm", "concurrency"],
    "data structures": ["data structure", "data structures", "dsa", "linked list", "linked lists", "binary tree", "binary trees", "heap", "bst", "sorting", "searching", "graph traversal", "avl tree", "stack", "queue"],
    "dbms": ["database", "databases", "dbms", "sql", "normalization", "transaction", "acid", "join", "indexing", "relational algebra", "b+ tree"],
    "computer networks": ["computer network", "computer networks", "networking", "network", "networks", "tcp", "ip", "http", "dns", "routing", "osi model", "ethernet", "subnet", "congestion control"],
    "algorithms": ["algorithm", "algorithms", "complexity", "big o", "dynamic programming", "greedy", "backtracking", "divide and conquer", "dijkstra"],
    "python programming": ["python", "python programming", "numpy", "pandas", "oop in python", "django", "flask"],
    "c programming": ["c programming", "pointer", "pointers", "malloc", "struct", "recursion in c", "dynamic memory", "file handling in c"],
    "engineering mechanics": ["mechanics", "statics", "dynamics", "friction", "centroid", "moment of inertia", "truss", "kinematics", "kinetics"],
    "thermodynamics": ["thermodynamics", "entropy", "enthalpy", "carnot", "rankine", "brayton", "first law", "second law", "refrigeration"],
    "fluid mechanics": ["fluid mechanics", "bernoulli", "navier stokes", "viscosity", "reynolds number", "venturimeter", "fluid flow", "pipe flow"],
    "digital electronics": ["digital electronics", "logic gate", "logic gates", "flip flop", "flip flops", "counter", "multiplexer", "boolean algebra", "karnaugh map", "k-map", "adc", "dac"]
}

def extract_topic_from_query(query: str, last_topic: str = "") -> str:
    """Extract topic using word-boundary matching first, then follow-up memory."""
    q_clean = query.strip().lower()
    
    # 1. PRIORITY: Check explicit topic keyword in current query first
    for topic_name, kws in TOPIC_KW.items():
        for kw in sorted(kws, key=len, reverse=True):
            pattern = r'(?<![a-zA-Z0-9])' + _re.escape(kw) + r'(?![a-zA-Z0-9])'
            if _re.search(pattern, q_clean):
                return topic_name

    # 2. Check if this is a follow-up query that should inherit previous topic
    follow_up_tokens = {
        "bhai", "nhi", "nahi", "smj", "samj", "samjh", "smjh", "aaya", "aya",
        "video", "videos", "tutorial", "tutorials", "tutorilas", "some", "again",
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

def analyze_user_intent(
    current_message: str,
    conversation_history: list = None,
    topic: str = "",
    topic_attempts: int = 0
) -> dict:
    """
    MAIN FUNCTION: Analyze user's TRUE intent.
    Recommends videos when user is frustrated, stuck, repeating, or explicitly asks for videos.
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

    q_lower = current_message.lower()

    # Signals
    is_frustrated = any(phrase in q_lower for phrase in FRUSTRATION_PHRASES)
    is_asking_clarification = any(phrase in q_lower for phrase in CLARIFICATION_PHRASES)
    is_video_requested = any(v in q_lower for v in ["video", "videos", "youtube", "lecture", "tutorial", "tutorials", "tutorilas", "playlist", "watch", "link", "links"])

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

    # ===== DECISION LOGIC (PRIORITIZED) =====

    # 1. Frustration / Stuck / Repeated (🚨 URGENT Mode)
    if is_frustrated or is_repeating:
        analysis["intent"] = "confused"
        analysis["should_recommend_videos"] = True
        analysis["recommendation_strength"] = "urgent"
        analysis["reason"] = f"User is frustrated/stuck (Attempt #{topic_attempts + 1}) - urgent videos NEEDED"
        analysis["explanation_style"] = "basic"
        return analysis

    # 2. Explicit Video Request (🚨 Urgent Video Mode)
    if is_video_requested:
        analysis["intent"] = "clarify" if topic_attempts <= 1 else "confused"
        analysis["should_recommend_videos"] = True
        analysis["recommendation_strength"] = "urgent"
        analysis["reason"] = "User explicitly requested video support"
        analysis["explanation_style"] = "simpler"
        return analysis

    # 3. Third+ Attempt
    if topic_attempts >= 2:
        analysis["intent"] = "confused"
        analysis["should_recommend_videos"] = True
        analysis["recommendation_strength"] = "medium"
        analysis["reason"] = f"Attempt #{topic_attempts + 1} - recommend videos"
        analysis["explanation_style"] = "simpler"
        return analysis

    # 4. Clarification Request (Attempt 2)
    if is_asking_clarification and topic_attempts >= 1:
        analysis["intent"] = "clarify"
        analysis["should_recommend_videos"] = False
        analysis["reason"] = "User needs clarification - provide different explanation"
        analysis["explanation_style"] = "simpler"
        return analysis

    # 5. Normal Initial Learning (First time asking without frustration)
    analysis["intent"] = "initial"
    analysis["should_recommend_videos"] = False
    analysis["reason"] = "First time asking - provide explanation only"
    analysis["explanation_style"] = "normal"
    return analysis


# ── Video Recommendations & Rating ─────────────────────────────────────────────

TOPIC_TO_FACULTY_MAP = {
    "calculus": ["calculus", "math", "differentiation", "integration", "derivative", "differential", "gajendra purohit", "vishwakarma"],
    "differential equations": ["calculus", "math", "differential equations", "vishwakarma", "gajendra purohit"],
    "linear algebra": ["calculus", "math", "linear algebra", "matrices", "gajendra purohit"],
    "thevenin theorem": ["thevenin", "network", "circuit", "electrical", "kvl", "kcl", "umesh dhande", "engineers ki pathshala", "neso academy"],
    "electrical circuits": ["circuit", "circuits", "electrical", "electronics", "neso academy", "umesh dhande"],
    "electrical machines": ["electrical", "motor", "transformer", "circuits", "neso academy"],
    "operating systems": ["operating", "os", "deadlock", "semaphore", "process", "gate smashers", "varun singla", "neso academy"],
    "python programming": ["python", "programming", "code with harry", "apna college", "shradha khapra"],
    "data structures": ["data structure", "dsa", "abdul bari", "tree", "graph", "algorithm", "apna college"],
    "algorithms": ["algorithm", "algorithms", "abdul bari", "dynamic programming", "dsa"],
    "engineering mechanics": ["mechanics", "statics", "dynamics", "pradeep giri"],
    "thermodynamics": ["thermodynamics", "entropy", "heat", "mechanical"],
    "fluid mechanics": ["fluid", "bernoulli", "mechanical"],
    "digital electronics": ["digital", "logic gate", "flip flop", "neso academy"]
}

def get_recommended_videos(
    subject: str = "",
    topic: str = "",
    difficulty_level: str = "Beginner",
    mode: str = "exam",
    limit: int = 3
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

        scored = []
        for r in rows:
            p_id, ch, inst, subj, top, url, diff, score, t_ratings, h_count, t_vids, avg_dur = r
            text = f"{ch} {inst} {subj} {top}".lower()
            
            match_score = 0
            # Direct keyword hits
            for kw in keywords:
                if kw in text:
                    match_score += 15
            # Direct topic match
            if topic_clean and topic_clean in text:
                match_score += 30
            # Exact subject match if provided
            if subject and subject.lower() in subj.lower():
                match_score += 10

            if match_score > 0:
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
        results = [item[1] for item in scored[:limit]]

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
        "thevenin theorem": ["thevenin", "thevenin's", "norton", "kvl", "kcl", "maximum power transfer", "superposition theorem", "reciprocity"],
        "electrical circuits": ["circuit", "dependent source", "phasor", "impedance", "mesh analysis", "nodal analysis", "rlc circuit", "ac circuit", "kirchhoff"],
        "electrical machines": ["induction motor", "transformer", "rotating magnetic field", "rmf", "synchronous motor", "dc motor", "stator", "rotor", "armature", "torque slip"],
        "power systems": ["power factor", "three phase", "transmission line", "load flow", "fault analysis", "generator", "bus admittance"],
        "control systems": ["bode plot", "root locus", "nyquist plot", "transfer function", "pid controller", "state space", "stability"],
        "thermodynamics": ["thermodynamics", "entropy", "enthalpy", "carnot", "rankine", "brayton", "first law", "second law", "refrigeration"],
        "fluid mechanics": ["bernoulli", "navier stokes", "viscosity", "reynolds number", "venturimeter", "fluid flow", "pipe flow"],
        "operating systems": ["operating system", "deadlock", "scheduling", "semaphore", "paging", "virtual memory", "process management", "banker's algorithm"],
        "data structures": ["data structure", "linked list", "binary tree", "heap", "bst", "sorting", "searching", "graph traversal", "avl tree"],
        "dbms": ["database", "dbms", "sql", "normalization", "transaction", "acid", "join", "indexing", "relational algebra", "b+ tree"],
        "computer networks": ["network", "tcp", "ip", "http", "dns", "routing", "osi", "ethernet", "subnet", "congestion control"],
        "algorithms": ["algorithm", "complexity", "big o", "dynamic programming", "greedy", "backtracking", "divide and conquer", "dijkstra"],
        "machine learning": ["machine learning", "neural network", "deep learning", "regression", "gradient descent", "backpropagation", "cnn", "rnn"],
        "digital electronics": ["logic gate", "flip flop", "counter", "multiplexer", "boolean", "karnaugh", "k-map", "adc", "dac"],
        "signals systems": ["fourier", "laplace", "convolution", "filter", "sampling", "nyquist", "z-transform", "fourier transform"],
        "engineering mathematics": ["calculus", "differential equation", "eigenvalue", "eigenvector", "integral", "probability", "laplace transform", "linear algebra"],
        "c programming": ["pointer", "malloc", "struct", "recursion in c", "dynamic memory", "file handling in c"],
        "object oriented": ["oop", "object oriented", "inheritance", "polymorphism", "encapsulation", "abstraction", "virtual function"],
        "computer architecture": ["processor", "cpu", "cache", "pipeline", "instruction set", "alu", "cache mapping", "pipelining hazards"],
        "software engineering": ["sdlc", "agile", "design pattern", "uml", "software testing", "waterfall model"]
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
    
    # 1. Expanded follow-up tokens & phrases (e.g. 'suggest some video for it', 'bhai video do', 'isko explain karo')
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
    
    if (is_mostly_followup or (has_video_word and ("it" in q_clean or "this" in q_clean or len(words) <= 6)) or (has_frustration_word and len(words) <= 6)) and last_topic and last_topic != "general":
        print(f"[NLP TOPIC] Reusing last_topic '{last_topic}' for query: '{query}'")
        return last_topic

    # 2. Check keyword dictionary
    kw_topic = _extract_topic_keywords(query)
    if kw_topic != "general":
        return kw_topic

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