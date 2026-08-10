
import streamlit as st
import sqlite3
import hashlib
import secrets
import json
import random
import requests
import time
from datetime import datetime, date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components

# ============================================================
# MINDMATE - FINAL PROJECT VERSION
# ============================================================
# 12 modules:
# 1 Login
# 2 Dashboard
# 3 Study Planner
# 4 Tomorrow's Plan
# 5 Adaptive Quiz
# 6 Doubt Chatbot
# 7 Coding Tracker
# 8 Stress Monitor
# 9 Puzzle Zone
# 10 Analytics
# 11 Settings
# 12 Logout
#
# Important design:
# - User creates their own account/password.
# - User enters their own semester subjects and exam schedule.
# - No previous-semester CGPA/marks are required.
# - Study timer is required before a topic quiz can be started.
# - Quiz question IDs are permanently recorded per user.
# - Puzzle IDs are permanently recorded per user.
# - Coding activity is tracked by date/language/user coding ID.
# - Analytics use actual current MindMate activity.
# ============================================================

st.set_page_config(
    page_title="MindMate - Smart Study Companion",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "mindmate.db"

# ----------------------------- UI -----------------------------
st.markdown(
    """
    <style>
    .main-header {font-size: 2.8rem; font-weight: 800; color:#4A90E2;}
    .card {padding:18px;border-radius:16px;background:#f7f9fc;border:1px solid #e6eaf0;margin-bottom:12px;}
    .hero {padding:22px;border-radius:18px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;}
    .ok {padding:14px;border-radius:12px;background:#eaf8ee;border-left:5px solid #2e9d50;}
    .warn {padding:14px;border-radius:12px;background:#fff7df;border-left:5px solid #e5a100;}
    .weak {padding:14px;border-radius:12px;background:#fff0f0;border-left:5px solid #e34d59;}
    .stButton>button {border-radius:10px;font-weight:600;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- DB -----------------------------
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subjects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(user_id,name)
        );

        CREATE TABLE IF NOT EXISTS exams(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            exam_time TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS study_sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            planned_minutes INTEGER NOT NULL,
            actual_minutes INTEGER NOT NULL,
            completed INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT
        );

        CREATE TABLE IF NOT EXISTS quiz_questions(
            id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            question TEXT NOT NULL,
            options_json TEXT NOT NULL,
            answer TEXT NOT NULL,
            difficulty TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quiz_attempts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            question_id TEXT NOT NULL,
            selected_answer TEXT NOT NULL,
            correct INTEGER NOT NULL,
            score REAL NOT NULL,
            attempted_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS coding_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            coding_user_id TEXT NOT NULL,
            log_date TEXT NOT NULL,
            platform TEXT NOT NULL,
            language TEXT NOT NULL,
            attempted INTEGER NOT NULL,
            solved INTEGER NOT NULL,
            easy INTEGER NOT NULL,
            medium INTEGER NOT NULL,
            hard INTEGER NOT NULL,
            minutes INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS coding_snapshots(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            coding_user_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            solved_total INTEGER NOT NULL DEFAULT 0,
            attempted_total INTEGER NOT NULL DEFAULT 0,
            language_json TEXT NOT NULL DEFAULT '{}',
            easy_total INTEGER NOT NULL DEFAULT 0,
            medium_total INTEGER NOT NULL DEFAULT 0,
            hard_total INTEGER NOT NULL DEFAULT 0,
            fetched_at TEXT NOT NULL,
            UNIQUE(user_id, coding_user_id, platform, snapshot_date)
        );

        CREATE TABLE IF NOT EXISTS stress_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            level INTEGER NOT NULL,
            note TEXT,
            logged_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS puzzle_attempts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            puzzle_id TEXT NOT NULL,
            puzzle_type TEXT NOT NULL,
            score REAL NOT NULL,
            played_at TEXT NOT NULL,
            UNIQUE(user_id,puzzle_id)
        );

        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_date TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration INTEGER NOT NULL,
            priority TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS topics(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            UNIQUE(user_id,subject,topic)
        );

        CREATE TABLE IF NOT EXISTS profiles(
            user_id INTEGER PRIMARY KEY,
            coding_user_id TEXT DEFAULT '',
            coding_platform TEXT DEFAULT 'Manual',
            semester TEXT DEFAULT ''
        );
        """
    )
    conn.commit()
    conn.close()


init_db()

# ----------------------------- Helpers -----------------------------
def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 120_000
    ).hex()
    return f"{salt}${digest}"


def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 120_000
        ).hex()
        return secrets.compare_digest(check, digest)
    except Exception:
        return False


def create_user(username, name, email, password):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users(username,name,email,password_hash,created_at) VALUES(?,?,?,?,?)",
            (
                username.strip(),
                name.strip(),
                email.strip().lower(),
                hash_password(password),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM users WHERE username=?", (username.strip(),)
        ).fetchone()
        user_id = row[0]
        conn.execute("INSERT INTO profiles(user_id) VALUES(?)", (user_id,))
        conn.commit()
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def authenticate(username, password):
    conn = get_conn()
    row = conn.execute(
        "SELECT id,name,email,password_hash FROM users WHERE username=?",
        (username.strip(),),
    ).fetchone()
    conn.close()
    if row and verify_password(password, row[3]):
        return row
    return None


def user_subjects(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT name FROM subjects WHERE user_id=? ORDER BY name", (user_id,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def add_subject(user_id, subject):
    if not subject.strip():
        return
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO subjects(user_id,name) VALUES(?,?)",
        (user_id, subject.strip()),
    )
    conn.commit()
    conn.close()


def remove_subject(user_id, subject):
    conn = get_conn()
    conn.execute(
        "DELETE FROM subjects WHERE user_id=? AND name=?", (user_id, subject)
    )
    conn.execute("DELETE FROM topics WHERE user_id=? AND subject=?", (user_id, subject))
    conn.commit()
    conn.close()


def user_topics(user_id, subject):
    conn = get_conn()
    rows = conn.execute(
        "SELECT topic FROM topics WHERE user_id=? AND subject=? ORDER BY topic",
        (user_id, subject),
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def add_topic(user_id, subject, topic):
    if not topic.strip():
        return
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO topics(user_id,subject,topic) VALUES(?,?,?)",
        (user_id, subject, topic.strip()),
    )
    conn.commit()
    conn.close()


def save_profile(user_id, coding_id, platform, semester):
    conn = get_conn()
    conn.execute(
        "INSERT INTO profiles(user_id,coding_user_id,coding_platform,semester) "
        "VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET "
        "coding_user_id=excluded.coding_user_id,coding_platform=excluded.coding_platform,"
        "semester=excluded.semester",
        (user_id, coding_id, platform, semester),
    )
    conn.commit()
    conn.close()


def profile(user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT coding_user_id,coding_platform,semester FROM profiles WHERE user_id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row or ("", "Manual", "")


def save_exam(user_id, subject, exam_date, exam_time):
    conn = get_conn()
    conn.execute(
        "INSERT INTO exams(user_id,subject,exam_date,exam_time) VALUES(?,?,?,?)",
        (user_id, subject, str(exam_date), str(exam_time)),
    )
    conn.commit()
    conn.close()


def delete_exam(user_id, exam_id):
    conn = get_conn()
    conn.execute("DELETE FROM exams WHERE id=? AND user_id=?", (exam_id, user_id))
    conn.commit()
    conn.close()


def exams_df(user_id):
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT id,subject,exam_date,exam_time FROM exams "
        "WHERE user_id=? ORDER BY exam_date,exam_time",
        conn,
        params=(user_id,),
    )
    conn.close()
    return df


def save_study(user_id, subject, topic, planned, actual, completed, started, ended):
    conn = get_conn()
    conn.execute(
        "INSERT INTO study_sessions(user_id,subject,topic,planned_minutes,actual_minutes,"
        "completed,started_at,ended_at) VALUES(?,?,?,?,?,?,?,?)",
        (user_id, subject, topic, planned, actual, int(completed), started, ended),
    )
    conn.commit()
    conn.close()


def study_df(user_id):
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM study_sessions WHERE user_id=? ORDER BY started_at DESC",
        conn,
        params=(user_id,),
    )
    conn.close()
    return df


def save_quiz_attempt(user_id, subject, topic, qid, selected, correct, score):
    conn = get_conn()
    conn.execute(
        "INSERT INTO quiz_attempts(user_id,subject,topic,question_id,selected_answer,"
        "correct,score,attempted_at) VALUES(?,?,?,?,?,?,?,?)",
        (
            user_id,
            subject,
            topic,
            qid,
            selected,
            int(correct),
            float(score),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()


def quiz_df(user_id):
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM quiz_attempts WHERE user_id=? ORDER BY attempted_at DESC",
        conn,
        params=(user_id,),
    )
    conn.close()
    return df


def used_question_ids(user_id, subject, topic):
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT question_id FROM quiz_attempts "
        "WHERE user_id=? AND subject=? AND topic=?",
        (user_id, subject, topic),
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}



def save_coding_snapshot(user_id, coding_user_id, platform, snapshot_date,
                         solved_total, attempted_total, language_stats,
                         easy_total=0, medium_total=0, hard_total=0):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO coding_snapshots(
            user_id,coding_user_id,platform,snapshot_date,
            solved_total,attempted_total,language_json,
            easy_total,medium_total,hard_total,fetched_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(user_id,coding_user_id,platform,snapshot_date)
        DO UPDATE SET
            solved_total=excluded.solved_total,
            attempted_total=excluded.attempted_total,
            language_json=excluded.language_json,
            easy_total=excluded.easy_total,
            medium_total=excluded.medium_total,
            hard_total=excluded.hard_total,
            fetched_at=excluded.fetched_at
        """,
        (
            user_id, coding_user_id, platform, str(snapshot_date),
            int(solved_total), int(attempted_total), json.dumps(language_stats),
            int(easy_total), int(medium_total), int(hard_total),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()


def coding_snapshots_df(user_id):
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT * FROM coding_snapshots
        WHERE user_id=?
        ORDER BY snapshot_date ASC
        """,
        conn,
        params=(user_id,),
    )
    conn.close()
    return df


def coding_current_totals(user_id):
    df = coding_snapshots_df(user_id)
    if df.empty:
        return {
            "attempted": 0, "solved": 0, "easy": 0,
            "medium": 0, "hard": 0, "platform": "", "coding_user_id": ""
        }
    latest = df.iloc[-1]
    return {
        "attempted": int(latest["attempted_total"]),
        "solved": int(latest["solved_total"]),
        "easy": int(latest["easy_total"]),
        "medium": int(latest["medium_total"]),
        "hard": int(latest["hard_total"]),
        "platform": latest["platform"],
        "coding_user_id": latest["coding_user_id"],
    }


def coding_df(user_id):
    """
    Return activity changes between automatic snapshots.
    No program counts are entered manually by the student.
    """
    snapshots = coding_snapshots_df(user_id)
    if snapshots.empty:
        return pd.DataFrame(
            columns=[
                "log_date", "platform", "language", "attempted",
                "solved", "minutes", "easy", "medium", "hard"
            ]
        )

    rows = []
    previous = None

    for _, row in snapshots.iterrows():
        current_languages = json.loads(row["language_json"] or "{}")
        previous_languages = json.loads(previous["language_json"] or "{}") if previous is not None else {}

        if previous is None:
            # First sync is a baseline. Do not pretend all historical problems
            # happened today.
            solved_delta = 0
            attempted_delta = 0
            easy_delta = medium_delta = hard_delta = 0
        else:
            solved_delta = max(0, int(row["solved_total"]) - int(previous["solved_total"]))
            attempted_delta = max(0, int(row["attempted_total"]) - int(previous["attempted_total"]))
            easy_delta = max(0, int(row["easy_total"]) - int(previous["easy_total"]))
            medium_delta = max(0, int(row["medium_total"]) - int(previous["medium_total"]))
            hard_delta = max(0, int(row["hard_total"]) - int(previous["hard_total"]))

        # Per-language cumulative stats -> per-language delta since previous sync.
        languages = set(current_languages) | set(previous_languages)
        if not languages:
            rows.append({
                "log_date": row["snapshot_date"],
                "platform": row["platform"],
                "language": "Unknown",
                "attempted": attempted_delta,
                "solved": solved_delta,
                "minutes": 0,
                "easy": easy_delta,
                "medium": medium_delta,
                "hard": hard_delta,
            })
        else:
            for language in languages:
                cur = current_languages.get(language, {})
                prev = previous_languages.get(language, {})
                rows.append({
                    "log_date": row["snapshot_date"],
                    "platform": row["platform"],
                    "language": language,
                    "attempted": max(0, int(cur.get("attempted", 0)) - int(prev.get("attempted", 0))),
                    "solved": max(0, int(cur.get("solved", 0)) - int(prev.get("solved", 0))),
                    "minutes": 0,
                    "easy": 0,
                    "medium": 0,
                    "hard": 0,
                })

        previous = row

    return pd.DataFrame(rows)


def codeforces_sync(username):
    url = "https://codeforces.com/api/user.status"
    response = requests.get(
        url,
        params={"handle": username, "from": 1, "count": 10000},
        timeout=15,
        headers={"User-Agent": "MindMate/1.0"},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "OK":
        raise ValueError(data.get("comment", "Codeforces returned an error."))

    submissions = data.get("result", [])
    language_stats = {}
    solved_problem_keys = set()
    solved_by_difficulty = {"easy": 0, "medium": 0, "hard": 0}

    for sub in submissions:
        lang = sub.get("programmingLanguage") or "Unknown"
        bucket = language_stats.setdefault(lang, {"attempted": 0, "solved": 0})
        bucket["attempted"] += 1

        problem = sub.get("problem", {})
        problem_key = f"{problem.get('contestId', '')}-{problem.get('index', '')}"
        if sub.get("verdict") == "OK":
            if problem_key not in solved_problem_keys:
                solved_problem_keys.add(problem_key)
                bucket["solved"] += 1

                rating = problem.get("rating")
                if rating is None or rating < 1300:
                    solved_by_difficulty["easy"] += 1
                elif rating < 1800:
                    solved_by_difficulty["medium"] += 1
                else:
                    solved_by_difficulty["hard"] += 1

    return {
        "attempted_total": len(submissions),
        "solved_total": len(solved_problem_keys),
        "language_stats": language_stats,
        "easy_total": solved_by_difficulty["easy"],
        "medium_total": solved_by_difficulty["medium"],
        "hard_total": solved_by_difficulty["hard"],
        "message": f"Synced {len(submissions)} recent submissions from Codeforces.",
    }


def leetcode_sync(username):
    endpoint = "https://leetcode.com/graphql"
    query = """
    query userStats($username: String!) {
      matchedUser(username: $username) {
        username
        submitStatsGlobal {
          acSubmissionNum { difficulty count submissions }
          totalSubmissionNum { difficulty count submissions }
        }
        languageProblemCount {
          languageName
          problemsSolved
        }
      }
    }
    """
    response = requests.post(
        endpoint,
        json={"query": query, "variables": {"username": username}},
        timeout=20,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "MindMate/1.0",
            "Referer": "https://leetcode.com/",
        },
    )
    response.raise_for_status()
    payload = response.json()

    matched = (payload.get("data") or {}).get("matchedUser")
    if not matched:
        raise ValueError("LeetCode user not found or profile is unavailable.")

    stats = matched.get("submitStatsGlobal") or {}
    accepted = stats.get("acSubmissionNum") or []
    total = stats.get("totalSubmissionNum") or []

    def total_for(items, difficulty):
        for item in items:
            if item.get("difficulty") == difficulty:
                return int(item.get("count") or 0)
        return 0

    solved_total = total_for(accepted, "All")
    attempted_submissions = total_for(total, "All")
    language_stats = {}

    for item in matched.get("languageProblemCount") or []:
        lang = item.get("languageName") or "Unknown"
        solved = int(item.get("problemsSolved") or 0)
        language_stats[lang] = {
            # LeetCode exposes solved-problem totals by language, not a
            # reliable lifetime attempted count by language.
            "attempted": solved,
            "solved": solved,
        }

    return {
        "attempted_total": attempted_submissions,
        "solved_total": solved_total,
        "language_stats": language_stats,
        "easy_total": total_for(accepted, "Easy"),
        "medium_total": total_for(accepted, "Medium"),
        "hard_total": total_for(accepted, "Hard"),
        "message": "LeetCode profile totals synced. Daily changes appear after repeated snapshots.",
    }


def sync_coding_account(user_id, coding_id, platform):
    if not coding_id.strip():
        raise ValueError("Enter your coding-platform user ID/handle first.")

    if platform == "Codeforces":
        data = codeforces_sync(coding_id.strip())
    elif platform == "LeetCode":
        data = leetcode_sync(coding_id.strip())
    else:
        raise ValueError(
            "Automatic sync is currently supported for Codeforces and LeetCode. "
            "Choose one of these platforms; no manual problem-count entry is used."
        )

    save_coding_snapshot(
        user_id,
        coding_id.strip(),
        platform,
        date.today(),
        data["solved_total"],
        data["attempted_total"],
        data["language_stats"],
        data["easy_total"],
        data["medium_total"],
        data["hard_total"],
    )
    return data


def save_stress(user_id, level, note):
    conn = get_conn()
    conn.execute(
        "INSERT INTO stress_logs(user_id,level,note,logged_at) VALUES(?,?,?,?)",
        (user_id, level, note, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def stress_df(user_id):
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM stress_logs WHERE user_id=? ORDER BY logged_at",
        conn,
        params=(user_id,),
    )
    conn.close()
    return df


def save_task(user_id, task_date, subject, topic, start_time, duration, priority):
    conn = get_conn()
    conn.execute(
        "INSERT INTO tasks(user_id,task_date,subject,topic,start_time,duration,priority)"
        " VALUES(?,?,?,?,?,?,?)",
        (user_id, str(task_date), subject, topic, start_time, duration, priority),
    )
    conn.commit()
    conn.close()


def tasks_df(user_id, task_date=None):
    conn = get_conn()
    if task_date:
        df = pd.read_sql_query(
            "SELECT * FROM tasks WHERE user_id=? AND task_date=? ORDER BY start_time",
            conn,
            params=(user_id, str(task_date)),
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM tasks WHERE user_id=? ORDER BY task_date,start_time",
            conn,
            params=(user_id,),
        )
    conn.close()
    return df


def toggle_task(user_id, task_id, completed):
    conn = get_conn()
    conn.execute(
        "UPDATE tasks SET completed=? WHERE id=? AND user_id=?",
        (int(completed), task_id, user_id),
    )
    conn.commit()
    conn.close()


# ----------------------------- Question bank -----------------------------
# The user can add more questions from Settings. Built-ins are only a starter
# bank. Every question has a permanent ID, enabling true non-repetition.
QUESTION_BANK = [
    ("DBMS", "SQL Basics", "DBMS-001", "Which SQL command retrieves rows from a table?",
     ["SELECT", "INSERT", "UPDATE", "DELETE"], "SELECT", "Easy"),
    ("DBMS", "SQL Basics", "DBMS-002", "Which clause filters rows?",
     ["WHERE", "ORDER BY", "GROUP BY", "JOIN"], "WHERE", "Easy"),
    ("DBMS", "SQL Basics", "DBMS-003", "Which key uniquely identifies a row?",
     ["Foreign key", "Primary key", "Candidate value", "Index only"], "Primary key", "Easy"),
    ("DBMS", "Normalization", "DBMS-004", "Which normal form removes repeating groups?",
     ["1NF", "2NF", "3NF", "BCNF"], "1NF", "Medium"),
    ("DBMS", "Normalization", "DBMS-005", "3NF mainly removes:",
     ["Transitive dependency", "All keys", "All redundancy", "Every foreign key"],
     "Transitive dependency", "Medium"),

    ("Data Structures", "Trees", "DS-001", "Which structure is a binary search tree?",
     ["A tree ordered by key", "A queue", "A stack", "A graph without edges"],
     "A tree ordered by key", "Easy"),
    ("Data Structures", "Stacks", "DS-002", "A stack follows which principle?",
     ["FIFO", "LIFO", "Random", "Priority only"], "LIFO", "Easy"),
    ("Data Structures", "Queues", "DS-003", "A queue follows which principle?",
     ["LIFO", "FIFO", "Random", "Tree order"], "FIFO", "Easy"),
    ("Data Structures", "Graphs", "DS-004", "BFS normally uses a:",
     ["Queue", "Stack", "Heap", "Hash table"], "Queue", "Medium"),
    ("Data Structures", "Graphs", "DS-005", "DFS commonly uses:",
     ["Queue", "Stack or recursion", "Only heap", "Only array"],
     "Stack or recursion", "Medium"),

    ("Python", "Functions", "PY-001", "Which keyword defines a Python function?",
     ["def", "func", "define", "function"], "def", "Easy"),
    ("Python", "Exceptions", "PY-002", "Which keyword handles an exception?",
     ["except", "catch", "handle", "error"], "except", "Easy"),
    ("Python", "OOP", "PY-003", "Which method initializes an object?",
     ["__init__", "__start__", "constructor()", "initiate"], "__init__", "Medium"),

    ("COA", "Cache", "COA-001", "Cache memory is generally:",
     ["Faster than main memory", "Slower than a hard disk", "Permanent storage", "An input device"],
     "Faster than main memory", "Easy"),
    ("COA", "DMA", "COA-002", "DMA stands for:",
     ["Direct Memory Access", "Data Memory Allocation", "Digital Memory Array", "Direct Module Access"],
     "Direct Memory Access", "Easy"),

    ("Modern Physics", "Photoelectric Effect", "PHY-001",
     "The minimum frequency required for photoemission is called:",
     ["Threshold frequency", "Resonant frequency", "Natural frequency", "Clock frequency"],
     "Threshold frequency", "Medium"),
    ("Modern Physics", "Dual Nature", "PHY-002",
     "Photon energy is given by:",
     ["E=hf", "E=mc", "E=IR", "E=Pt"],
     "E=hf", "Easy"),

    ("CRTC", "Number Systems", "CRTC-001", "Hexadecimal has base:",
     ["2", "8", "10", "16"], "16", "Easy"),
    ("CRTC", "Percentages", "CRTC-002", "20% of 150 is:",
     ["20", "25", "30", "35"], "30", "Easy"),

    ("DAE", "Basics", "DAE-001", "In data analysis, a dataset is primarily a collection of:",
     ["Observations", "Only images", "Only programs", "Only passwords"],
     "Observations", "Easy"),
    ("DAE", "Basics", "DAE-002", "A missing value is commonly represented as:",
     ["Null/NaN", "CPU", "Loop", "Pointer only"], "Null/NaN", "Easy"),

    ("ASE", "Basics", "ASE-001", "Software testing is primarily used to:",
     ["Find defects", "Increase monitor size", "Replace requirements", "Delete source code"],
     "Find defects", "Easy"),
    ("ASE", "Basics", "ASE-002", "A requirement describes:",
     ["What a system should do", "Only the UI color", "Only a variable name", "Only hardware cost"],
     "What a system should do", "Easy"),

    ("AI", "Machine Learning", "AI-001", "Supervised learning uses:",
     ["Labeled data", "No data", "Only random guesses", "Only images"],
     "Labeled data", "Easy"),
    ("AI", "Machine Learning", "AI-002", "Classification predicts:",
     ["Categories", "Only continuous values", "Database rows", "CPU cycles"],
     "Categories", "Easy"),

    ("C++", "Basics", "CPP-001", "Which symbol ends a typical C++ statement?",
     [";", ":", ".", ","], ";", "Easy"),
    ("C++", "OOP", "CPP-002", "Which concept lets a class derive from another?",
     ["Inheritance", "Iteration", "Compilation", "Hashing"],
     "Inheritance", "Easy"),

    ("P&S", "Statistics", "PS-001", "The arithmetic average is called:",
     ["Mean", "Median", "Mode", "Range"], "Mean", "Easy"),
    ("P&S", "Probability", "PS-002", "A probability must lie between:",
     ["0 and 1", "-1 and 1", "1 and 100", "Any values"],
     "0 and 1", "Easy"),

    ("ADSAA", "Algorithms", "ADSAA-001", "Binary search requires the data to be:",
     ["Sorted", "Random", "Encrypted", "Duplicated"],
     "Sorted", "Easy"),
    ("ADSAA", "Algorithms", "ADSAA-002", "Average quicksort complexity is:",
     ["O(n log n)", "O(1)", "O(log n)", "O(n!)"],
     "O(n log n)", "Medium"),
]


def seed_questions():
    conn = get_conn()
    for subject, topic, qid, question, options, answer, difficulty in QUESTION_BANK:
        conn.execute(
            "INSERT OR IGNORE INTO quiz_questions(id,subject,topic,question,options_json,answer,difficulty)"
            " VALUES(?,?,?,?,?,?,?)",
            (qid, subject, topic, question, json.dumps(options), answer, difficulty),
        )
    conn.commit()
    conn.close()


seed_questions()


def get_questions(subject, topic):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id,question,options_json,answer,difficulty FROM quiz_questions "
        "WHERE subject=? AND topic=?",
        (subject, topic),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "question": r[1],
            "options": json.loads(r[2]),
            "answer": r[3],
            "difficulty": r[4],
        }
        for r in rows
    ]


def insert_custom_question(subject, topic, question, options, answer, difficulty):
    qid = f"CUSTOM-{secrets.token_hex(6)}"
    conn = get_conn()
    conn.execute(
        "INSERT INTO quiz_questions(id,subject,topic,question,options_json,answer,difficulty)"
        " VALUES(?,?,?,?,?,?,?)",
        (qid, subject, topic, question, json.dumps(options), answer, difficulty),
    )
    conn.commit()
    conn.close()


# ----------------------------- Puzzle bank -----------------------------
# Each puzzle has a unique ID. Only unsolved/unused puzzles are selected.
PUZZLES = [
    ("SUD-001", "Sudoku", "Sudoku 4x4", "Fill the grid so every row and column has 1-4."),
    ("ARR-001", "Arrows", "Arrow Memory", "Remember the arrow sequence shown in the game."),
    ("SNA-001", "Snake", "Snake Game", "Collect food without hitting the wall or yourself."),
    ("DINO-001", "Dinosaur", "Dino Runner", "Jump over obstacles and survive as long as possible."),
    ("SUD-002", "Sudoku", "Sudoku 4x4", "Solve another 4x4 Sudoku board."),
    ("ARR-002", "Arrows", "Arrow Memory", "Repeat a longer arrow sequence."),
    ("SNA-002", "Snake", "Snake Game", "Survive a new snake round."),
    ("DINO-002", "Dinosaur", "Dino Runner", "Survive a faster dino round."),
]


def used_puzzles(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT puzzle_id FROM puzzle_attempts WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}


def record_puzzle(user_id, puzzle_id, puzzle_type, score):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO puzzle_attempts(user_id,puzzle_id,puzzle_type,score,played_at)"
        " VALUES(?,?,?,?,?)",
        (user_id, puzzle_id, puzzle_type, score, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


# ----------------------------- State -----------------------------
defaults = {
    "logged_in": False,
    "user_id": None,
    "username": "",
    "name": "",
    "page": "Dashboard",
    "timer_running": False,
    "timer_started": None,
    "timer_end": None,
    "timer_planned": 25,
    "timer_subject": "",
    "timer_topic": "",
    "timer_completed": False,
    "quiz_questions": [],
    "quiz_index": 0,
    "quiz_score": 0,
    "quiz_started": False,
    "quiz_submitted": False,
    "quiz_answered_ids": set(),
    "chat": [],
    "selected_puzzle": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def go(page):
    st.session_state.page = page


# ============================================================
# LOGIN
# ============================================================
if not st.session_state.logged_in:
    st.markdown(
        '<div class="main-header">🧠 MindMate</div>'
        '<div style="text-align:center;font-size:1.2rem">Smart Study Companion</div>',
        unsafe_allow_html=True,
    )

    login_tab, register_tab = st.tabs(["🔐 Login", "📝 Create Account"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                user = authenticate(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.name = user[1]
                    st.session_state.username = username
                    st.session_state.page = "Dashboard"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Full name")
            username = st.text_input("Create username")
            email = st.text_input("Email")
            password = st.text_input("Create password", type="password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)

            if submitted:
                if not all([name.strip(), username.strip(), email.strip(), password]):
                    st.warning("Fill in all fields.")
                elif len(password) < 6:
                    st.warning("Password must contain at least 6 characters.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = create_user(username, name, email, password)
                    if ok:
                        st.success("Account created. Go to Login.")
                    else:
                        st.error(msg)

    st.info("Each user creates their own password. No fixed project-wide password is required.")
    st.stop()


# ============================================================
# GLOBAL TIMER
# ============================================================
if st.session_state.timer_running:
    remaining = max(0, int(st.session_state.timer_end - time.time()))
    if remaining <= 0:
        st.session_state.timer_running = False
        st.session_state.timer_completed = True
        planned = st.session_state.timer_planned
        save_study(
            st.session_state.user_id,
            st.session_state.timer_subject,
            st.session_state.timer_topic,
            planned,
            planned,
            True,
            datetime.fromtimestamp(st.session_state.timer_started).isoformat(timespec="seconds"),
            datetime.now().isoformat(timespec="seconds"),
        )


# ============================================================
# SIDEBAR / 12 MODULES
# ============================================================
with st.sidebar:
    st.markdown("## 🧠 MindMate")
    st.write(f"Welcome, **{st.session_state.name}**")

    pages = [
        "Dashboard",
        "Study Planner",
        "Tomorrow's Plan",
        "Adaptive Quiz",
        "Doubt Chatbot",
        "Coding Tracker",
        "Stress Monitor",
        "Puzzle Zone",
        "Analytics",
        "Settings",
    ]

    selected = st.radio(
        "Navigation",
        pages,
        index=pages.index(st.session_state.page) if st.session_state.page in pages else 0,
    )
    st.session_state.page = selected

    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        logout()

# ============================================================
# DASHBOARD
# ============================================================
if st.session_state.page == "Dashboard":
    st.title("🏠 Dashboard")
    st.caption("Your study, coding and wellbeing command center.")

    subjects = user_subjects(st.session_state.user_id)
    qdf = quiz_df(st.session_state.user_id)
    sdf = study_df(st.session_state.user_id)
    cdf = coding_df(st.session_state.user_id)
    edf = exams_df(st.session_state.user_id)

    total_study = int(sdf["actual_minutes"].sum()) if not sdf.empty else 0
    today_study = int(
        sdf[sdf["started_at"].str[:10] == str(date.today())]["actual_minutes"].sum()
    ) if not sdf.empty else 0
    quiz_avg = round(qdf["score"].mean(), 1) if not qdf.empty else 0
    coding_totals = coding_current_totals(st.session_state.user_id)
    solved = int(coding_totals["solved"])

    exams_future = edf[edf["exam_date"] >= str(date.today())] if not edf.empty else edf
    next_exam = exams_future.iloc[0] if not exams_future.empty else None

    a, b, c, d, e = st.columns(5)
    a.metric("📚 Today Study", f"{today_study} min")
    b.metric("📝 Quiz Average", f"{quiz_avg}%")
    c.metric("💻 Programs Solved", solved)
    d.metric("📖 Subjects", len(subjects))
    e.metric("🔥 Study Sessions", len(sdf))

    st.subheader("⏰ Next Exam")
    if next_exam is not None:
        exam_dt = datetime.strptime(
            f"{next_exam['exam_date']} {next_exam['exam_time']}", "%Y-%m-%d %H:%M"
        )
        days = max(0, (exam_dt.date() - date.today()).days)
        st.success(
            f"**{next_exam['subject']}** — {exam_dt.strftime('%d %b %Y, %I:%M %p')} "
            f"— **{days} day(s) remaining**"
        )
    else:
        st.info("Add your exam schedule in Settings.")

    st.subheader("🎯 Today's Focus")
    if st.session_state.timer_running:
        remaining = max(0, int(st.session_state.timer_end - time.time()))
        st.warning(
            f"⏱️ Studying **{st.session_state.timer_subject} → "
            f"{st.session_state.timer_topic}** | "
            f"{remaining // 60:02d}:{remaining % 60:02d} remaining"
        )
        st.progress(
            min(1, max(0, 1 - remaining / (st.session_state.timer_planned * 60)))
        )
    elif st.session_state.timer_completed:
        st.success(
            f"Study completed: **{st.session_state.timer_subject} → "
            f"{st.session_state.timer_topic}**. Take your quiz now."
        )
        if st.button("📝 Take Quiz Now"):
            go("Adaptive Quiz")
            st.rerun()
    else:
        st.info("Start a focused study session from Study Planner.")

    ws = None
    if not qdf.empty:
        topic_perf = qdf.groupby(["subject", "topic"])["score"].mean().reset_index()
        topic_perf = topic_perf.sort_values("score")
        if not topic_perf.empty:
            ws = topic_perf.iloc[0]

    if ws is not None:
        st.markdown(
            f'<div class="weak">🎯 <b>Weak topic:</b> {ws["subject"]} → '
            f'{ws["topic"]} ({ws["score"]:.0f}%). Prioritize it in your next study session.</div>',
            unsafe_allow_html=True,
        )

    st.subheader("📅 Exam & Subject Snapshot")
    if subjects:
        st.write(" • ".join(subjects))
    else:
        st.warning("Add your semester subjects in Settings.")

# ============================================================
# STUDY PLANNER
# ============================================================
elif st.session_state.page == "Study Planner":
    st.title("📚 Study Planner")
    st.caption("Focus timer first. Quiz unlocks only after the session finishes.")

    subjects = user_subjects(st.session_state.user_id)
    if not subjects:
        st.warning("Add your semester subjects in Settings first.")
        st.stop()

    subject = st.selectbox("Subject", subjects)
    topics = user_topics(st.session_state.user_id, subject)

    st.markdown("### 📌 Topic")
    if topics:
        topic_choice = st.selectbox("Select topic", topics)
    else:
        topic_choice = st.text_input("Enter topic for this session")

    duration = st.selectbox("Focused study duration", [15, 25, 30, 45, 60, 90])

    if st.session_state.timer_running:
        remaining = max(0, int(st.session_state.timer_end - time.time()))
        mins, secs = divmod(remaining, 60)
        st.metric("⏱️ Time remaining", f"{mins:02d}:{secs:02d}")
        st.progress(
            min(1, max(0, 1 - remaining / (st.session_state.timer_planned * 60)))
        )

        if st.button("⏹️ Stop Early"):
            elapsed = max(
                1,
                round((time.time() - st.session_state.timer_started) / 60),
            )
            save_study(
                st.session_state.user_id,
                st.session_state.timer_subject,
                st.session_state.timer_topic,
                st.session_state.timer_planned,
                elapsed,
                False,
                datetime.fromtimestamp(st.session_state.timer_started).isoformat(timespec="seconds"),
                datetime.now().isoformat(timespec="seconds"),
            )
            st.session_state.timer_running = False
            st.session_state.timer_completed = False
            st.rerun()

        time.sleep(1)
        st.rerun()

    elif st.session_state.timer_completed:
        st.success(
            f"🎉 Session complete! **{st.session_state.timer_subject} → "
            f"{st.session_state.timer_topic}** quiz is unlocked."
        )
        if st.button("📝 Take Topic Quiz"):
            st.session_state.page = "Adaptive Quiz"
            st.rerun()
        if st.button("Start Another Session"):
            st.session_state.timer_completed = False
            st.rerun()

    else:
        if st.button("▶️ Start Focused Study Timer", use_container_width=True):
            if not topic_choice.strip():
                st.warning("Enter a topic first.")
            else:
                if not topics:
                    add_topic(st.session_state.user_id, subject, topic_choice)
                st.session_state.timer_subject = subject
                st.session_state.timer_topic = topic_choice.strip()
                st.session_state.timer_planned = duration
                st.session_state.timer_started = time.time()
                st.session_state.timer_end = time.time() + duration * 60
                st.session_state.timer_running = True
                st.session_state.timer_completed = False
                st.rerun()

    st.divider()
    st.subheader("📝 Add Study Task")
    with st.form("task_form"):
        task_date = st.date_input("Date", date.today())
        task_subject = st.selectbox("Task subject", subjects)
        task_topics = user_topics(st.session_state.user_id, task_subject)
        task_topic = st.text_input(
            "Task topic",
            value=task_topics[0] if task_topics else "",
        )
        start_time = st.time_input("Start time", datetime.now().time().replace(second=0, microsecond=0))
        task_duration = st.number_input("Duration (minutes)", 15, 300, 45, 15)
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        if st.form_submit_button("➕ Add Task"):
            save_task(
                st.session_state.user_id,
                task_date,
                task_subject,
                task_topic,
                start_time.strftime("%H:%M"),
                task_duration,
                priority,
            )
            st.success("Task added.")

    today_tasks = tasks_df(st.session_state.user_id, date.today())
    if not today_tasks.empty:
        st.subheader("Today's Timetable")
        for _, row in today_tasks.iterrows():
            checked = st.checkbox(
                f"{row['start_time']} — {row['subject']} → {row['topic']} "
                f"({row['duration']} min, {row['priority']})",
                value=bool(row["completed"]),
                key=f"task_{row['id']}",
            )
            if checked != bool(row["completed"]):
                toggle_task(st.session_state.user_id, int(row["id"]), checked)
                st.rerun()

# ============================================================
# TOMORROW'S PLAN
# ============================================================
elif st.session_state.page == "Tomorrow's Plan":
    st.title("📅 Tomorrow's Plan")
    st.caption("Automatically prioritizes weak topics and upcoming exams.")

    qdf = quiz_df(st.session_state.user_id)
    edf = exams_df(st.session_state.user_id)
    subjects = user_subjects(st.session_state.user_id)

    weak = []
    if not qdf.empty:
        weak_df = (
            qdf.groupby(["subject", "topic"])["score"]
            .mean()
            .reset_index()
            .sort_values("score")
        )
        weak = weak_df[weak_df["score"] < 80].head(3).to_dict("records")

    plan = []
    for item in weak:
        plan.append(
            {
                "time": "09:00",
                "subject": item["subject"],
                "topic": item["topic"],
                "minutes": 45,
                "reason": f"Weak topic ({item['score']:.0f}%)",
            }
        )

    used_slots = {x["time"] for x in plan}
    fallback_subjects = subjects[:]
    slot_times = ["11:00", "14:00", "16:00", "19:00"]
    for slot, subj in zip(slot_times, fallback_subjects):
        if slot in used_slots:
            continue
        topics = user_topics(st.session_state.user_id, subj)
        plan.append(
            {
                "time": slot,
                "subject": subj,
                "topic": topics[0] if topics else "Revision",
                "minutes": 45,
                "reason": "Semester subject revision",
            }
        )

    if not plan:
        st.info("Add subjects and complete some study/quiz sessions to generate a plan.")
    else:
        for item in plan[:6]:
            st.markdown(
                f'<div class="card"><b>{item["time"]}</b> — '
                f'<b>{item["subject"]}</b> → {item["topic"]}<br>'
                f'{item["minutes"]} min • {item["reason"]}</div>',
                unsafe_allow_html=True,
            )

    if not edf.empty:
        future = edf[edf["exam_date"] >= str(date.today())]
        if not future.empty:
            exam = future.iloc[0]
            st.info(
                f"Upcoming exam priority: **{exam['subject']}** on "
                f"**{exam['exam_date']} at {exam['exam_time']}**."
            )

# ============================================================
# ADAPTIVE QUIZ
# ============================================================
elif st.session_state.page == "Adaptive Quiz":
    st.title("📝 Adaptive Topic Quiz")
    st.caption(
        "A completed study session unlocks the quiz. Questions already attempted "
        "by this student/topic are excluded."
    )

    subjects = user_subjects(st.session_state.user_id)
    if not subjects:
        st.warning("Add subjects first.")
        st.stop()

    unlocked = st.session_state.timer_completed

    if unlocked:
        subject = st.session_state.timer_subject
        topic = st.session_state.timer_topic
        st.success(f"🔓 Unlocked: **{subject} → {topic}**")
    else:
        subject = st.selectbox("Subject", subjects)
        topics = user_topics(st.session_state.user_id, subject)
        topic = st.selectbox("Topic", topics) if topics else st.text_input("Topic")
        st.info("Complete a focused study timer for this topic before starting the quiz.")

    available = get_questions(subject, topic)
    used = used_question_ids(st.session_state.user_id, subject, topic)
    fresh = [q for q in available if q["id"] not in used]

    st.write(f"Question bank: **{len(available)}** | Fresh for you: **{len(fresh)}**")

    if not available:
        st.warning(
            "No questions exist for this topic yet. Add questions in Settings → Question Bank."
        )

    if not st.session_state.quiz_started:
        if unlocked and available:
            count = min(5, len(fresh))
            if count == 0:
                st.warning(
                    "You have already attempted every question currently available "
                    "for this topic. Add new questions to continue without repetition."
                )
            elif st.button("🎯 Start Fresh Topic Quiz", use_container_width=True):
                selected_questions = random.sample(fresh, count)
                st.session_state.quiz_questions = selected_questions
                st.session_state.quiz_index = 0
                st.session_state.quiz_score = 0
                st.session_state.quiz_started = True
                st.session_state.quiz_submitted = False
                st.session_state.quiz_answered_ids = set()
                st.rerun()
        elif available and not unlocked:
            st.info("Finish the Study Planner timer first.")

    if st.session_state.quiz_started:
        questions = st.session_state.quiz_questions
        idx = st.session_state.quiz_index

        if idx < len(questions):
            q = questions[idx]
            st.progress(idx / len(questions))
            st.markdown(f"### Question {idx + 1} / {len(questions)}")
            st.caption(f"Difficulty: {q['difficulty']}")
            st.write(q["question"])

            answer = st.radio(
                "Choose one answer",
                q["options"],
                key=f"answer_{q['id']}",
            )

            if st.button("Submit Answer", use_container_width=True):
                correct = answer == q["answer"]
                save_quiz_attempt(
                    st.session_state.user_id,
                    subject,
                    topic,
                    q["id"],
                    answer,
                    correct,
                    100 if correct else 0,
                )
                st.session_state.quiz_answered_ids.add(q["id"])
                if correct:
                    st.session_state.quiz_score += 1
                    st.success("✅ Correct")
                else:
                    st.error(f"❌ Correct answer: {q['answer']}")

                st.session_state.quiz_index += 1
                st.rerun()
        else:
            total = len(questions)
            score = round(st.session_state.quiz_score / total * 100, 1)
            st.success(f"🎉 Quiz completed — **{score}%**")

            if score >= 80:
                st.markdown(
                    '<div class="ok">🟢 Strong understanding. Next time, use harder questions.</div>',
                    unsafe_allow_html=True,
                )
            elif score >= 50:
                st.markdown(
                    '<div class="warn">🟡 Okay. Revise the topic and practice again.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="weak">🔴 Weak topic. MindMate will prioritize it tomorrow.</div>',
                    unsafe_allow_html=True,
                )

            st.session_state.quiz_started = False
            st.session_state.quiz_submitted = True
            st.session_state.timer_completed = False

            if st.button("📚 Study This Topic Again"):
                go("Study Planner")
                st.rerun()

# ============================================================
# DOUBT CHATBOT
# ============================================================
elif st.session_state.page == "Doubt Chatbot":
    st.title("💬 Doubt Chatbot")
    st.caption("A local study assistant for explanations and study guidance.")

    if not st.session_state.chat:
        st.session_state.chat = [
            {
                "role": "assistant",
                "content": "Tell me the subject, topic and your doubt. I can give a simple explanation or a study approach."
            }
        ]

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input("Type your doubt...")
    if prompt:
        st.session_state.chat.append({"role": "user", "content": prompt})
        text = prompt.lower()

        if "quiz" in text:
            response = "Study one topic with the focus timer first. After completion, MindMate unlocks a fresh topic quiz."
        elif "weak" in text:
            response = "Check Analytics. MindMate identifies weak topics from your actual quiz scores and recommends them for tomorrow."
        elif "coding" in text or "program" in text:
            response = "Set your Codeforces or LeetCode user ID in Settings, then use Sync in Coding Tracker. MindMate calculates dated activity and language strength from the platform data instead of asking you to enter problem counts."
        elif "stress" in text:
            response = "Use Stress Monitor to record your current stress level. If it is high, take a short break before another focused session."
        else:
            response = (
                "For a precise academic answer, include the subject and topic, "
                "for example: 'DBMS — explain normalization' or 'C++ — explain inheritance'."
            )

        st.session_state.chat.append({"role": "assistant", "content": response})
        st.rerun()

# ============================================================
# CODING TRACKER
# ============================================================
elif st.session_state.page == "Coding Tracker":
    st.title("💻 Coding Tracker")
    st.caption(
        "Enter your coding-platform ID once. MindMate fetches public activity "
        "and builds dated snapshots — you do not enter program counts manually."
    )

    coding_id, platform, semester = profile(st.session_state.user_id)

    if platform not in ["Codeforces", "LeetCode"]:
        st.warning(
            "Automatic coding tracking currently supports **Codeforces** and "
            "**LeetCode**. Set your platform and user ID in Settings."
        )

    a, b = st.columns([2, 1])
    with a:
        st.write(f"**Coding User ID:** `{coding_id or 'Not set'}`")
        st.write(f"**Platform:** `{platform}`")
    with b:
        if st.button("🔄 Sync Coding Activity", use_container_width=True):
            if not coding_id:
                st.error("Set your coding user ID in Settings first.")
            elif platform not in ["Codeforces", "LeetCode"]:
                st.error("Choose Codeforces or LeetCode for automatic tracking.")
            else:
                try:
                    with st.spinner("Fetching coding activity..."):
                        result = sync_coding_account(
                            st.session_state.user_id,
                            coding_id,
                            platform,
                        )
                    st.success(result["message"])
                    st.rerun()
                except requests.RequestException:
                    st.error(
                        "Could not reach the coding platform right now. "
                        "Check your internet connection and try again."
                    )
                except Exception as exc:
                    st.error(str(exc))

    totals = coding_current_totals(st.session_state.user_id)
    cdf = coding_df(st.session_state.user_id)

    if totals["platform"]:
        solve_rate = (
            round(totals["solved"] / totals["attempted"] * 100, 1)
            if totals["attempted"] else 0
        )
        a, b, c, d, e = st.columns(5)
        a.metric("Programs Solved", totals["solved"])
        b.metric("Submissions", totals["attempted"])
        c.metric("Solve Rate", f"{solve_rate}%")
        d.metric("Easy / Med / Hard",
                 f"{totals['easy']} / {totals['medium']} / {totals['hard']}")
        e.metric("Sync Snapshots", len(coding_snapshots_df(st.session_state.user_id)))

        if not cdf.empty:
            st.subheader("📅 Activity Tracked by Date")
            daily = cdf.groupby("log_date", as_index=False).agg(
                solved=("solved", "sum"),
                attempted=("attempted", "sum"),
            )
            st.plotly_chart(
                px.bar(
                    daily,
                    x="log_date",
                    y="solved",
                    title="New Programs Solved Between Syncs",
                    labels={"log_date": "Date", "solved": "New Solved"},
                ),
                use_container_width=True,
            )

            st.subheader("🧠 Language Skill")
            lang = (
                cdf.groupby("language", as_index=False)
                .agg(
                    attempted=("attempted", "sum"),
                    solved=("solved", "sum"),
                )
            )
            lang["skill"] = (
                lang["solved"] / lang["attempted"].replace(0, 1) * 100
            ).round(1)
            # If only solved-language totals are available (LeetCode), treat
            # those languages as strong by coverage rather than inventing
            # failed attempts.
            lang.loc[lang["attempted"] == lang["solved"], "skill"] = 100.0
            lang["status"] = lang["skill"].apply(
                lambda x: "🟢 Strong" if x >= 80
                else ("🟡 OK" if x >= 50 else "🔴 Weak")
            )
            st.dataframe(lang, use_container_width=True, hide_index=True)

            st.plotly_chart(
                px.bar(
                    lang,
                    x="language",
                    y="skill",
                    range_y=[0, 100],
                    title="Language Skill Analysis",
                    labels={"skill": "Skill (%)"},
                ),
                use_container_width=True,
            )

            st.info(
                "Skill is estimated from automatically synced activity. "
                "It becomes more meaningful after multiple snapshots."
            )
        else:
            st.info(
                "This is the first snapshot. Sync again on later days to build "
                "date-wise improvement graphs."
            )
    else:
        st.info(
            "Go to Settings → Profile, select Codeforces or LeetCode, and enter "
            "your coding user ID. Then return here and press Sync."
        )

# ============================================================
# STRESS MONITOR
# ============================================================
elif st.session_state.page == "Stress Monitor":
    st.title("😌 Stress Monitor")

    level = st.slider("Current stress level", 1, 10, 5)
    note = st.text_input("Optional note")

    if st.button("💾 Record Stress"):
        save_stress(st.session_state.user_id, level, note)
        st.success("Stress recorded.")

    if level <= 3:
        st.success("🟢 Low stress — good for focused study.")
    elif level <= 6:
        st.warning("🟡 Moderate stress — use shorter focused sessions.")
    else:
        st.error("🔴 High stress — take a break before continuing.")

    sdf = stress_df(st.session_state.user_id)
    if not sdf.empty:
        fig = px.line(
            sdf,
            x="logged_at",
            y="level",
            markers=True,
            range_y=[0, 10],
            title="Stress Trend",
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PUZZLE ZONE
# ============================================================
elif st.session_state.page == "Puzzle Zone":
    st.title("🧩 Puzzle Zone")
    st.caption("Sudoku, Arrow Memory, Snake and Dinosaur games.")

    used = used_puzzles(st.session_state.user_id)
    fresh = [p for p in PUZZLES if p[0] not in used]

    if not fresh:
        st.success(
            "🎉 You have completed every puzzle currently in the bank. "
            "No puzzle will be silently repeated."
        )
    else:
        if st.session_state.selected_puzzle is None:
            p = random.choice(fresh)
            st.session_state.selected_puzzle = p
        else:
            p = st.session_state.selected_puzzle
            if p[0] in used:
                st.session_state.selected_puzzle = random.choice(fresh)
                p = st.session_state.selected_puzzle

        puzzle_id, ptype, title, description = p
        st.subheader(f"{title} — {ptype}")
        st.write(description)

        # Sudoku: simple playable 4x4 board
        if ptype == "Sudoku":
            solution = [[1, 2, 3, 4], [3, 4, 1, 2], [2, 1, 4, 3], [4, 3, 2, 1]]
            givens = {(0, 0): 1, (0, 3): 4, (1, 1): 4, (2, 2): 4, (3, 0): 4}
            st.write("Fill the blank cells with numbers 1–4.")
            grid = []
            for r in range(4):
                cols = st.columns(4)
                row = []
                for c in range(4):
                    if (r, c) in givens:
                        cols[c].number_input(
                            f"r{r+1}c{c+1}", value=givens[(r, c)],
                            min_value=1, max_value=4, disabled=True,
                            key=f"{puzzle_id}_{r}_{c}_g"
                        )
                        row.append(givens[(r, c)])
                    else:
                        value = cols[c].number_input(
                            f"r{r+1}c{c+1}", min_value=1, max_value=4, value=1,
                            key=f"{puzzle_id}_{r}_{c}"
                        )
                        row.append(value)
                grid.append(row)

            if st.button("Check Sudoku"):
                if grid == solution:
                    record_puzzle(st.session_state.user_id, puzzle_id, ptype, 100)
                    st.success("🎉 Sudoku solved!")
                    st.session_state.selected_puzzle = None
                    st.rerun()
                else:
                    st.error("Not correct yet. Check rows and columns.")

        # Arrow memory: playable sequence memory
        elif ptype == "Arrows":
            arrows = ["U", "D", "L", "R"]
            if "arrow_sequence" not in st.session_state:
                st.session_state.arrow_sequence = [
                    random.choice(arrows) for _ in range(4)
                ]
                st.session_state.show_arrows = True

            if st.session_state.show_arrows:
                st.info(
                    "Memorize this sequence: "
                    + "  ".join(st.session_state.arrow_sequence)
                )
                if st.button("Hide Sequence"):
                    st.session_state.show_arrows = False
                    st.rerun()
            else:
                user_sequence = st.text_input(
                    "Enter the sequence in order (example: U D L R)",
                    key=f"arrow_answer_{puzzle_id}",
                )
                if st.button("Check Arrow Game"):
                    entered = [x.strip().upper() for x in user_sequence.split()]
                    if entered == st.session_state.arrow_sequence:
                        record_puzzle(
                            st.session_state.user_id, puzzle_id, ptype, 100
                        )
                        st.success("🎉 Correct arrow sequence!")
                        st.session_state.selected_puzzle = None
                        st.session_state.pop("arrow_sequence", None)
                        st.session_state.pop("show_arrows", None)
                        st.rerun()
                    else:
                        st.error("❌ Incorrect sequence. This puzzle remains available to retry.")

                if st.button("New Arrow Round"):
                    st.session_state.arrow_sequence = [
                        random.choice(arrows) for _ in range(4)
                    ]
                    st.session_state.show_arrows = True
                    st.rerun()

        # Snake and Dinosaur: actual browser mini-games
        elif ptype in ("Snake", "Dinosaur"):
            if ptype == "Snake":
                html = """
                <div style="font-family:Arial;text-align:center">
                <canvas id="game" width="360" height="240" style="border:2px solid #333"></canvas>
                <p>Use arrow keys. Eat the red food. Press Enter to restart.</p>
                </div>
                <script>
                const c=document.getElementById("game"),x=c.getContext("2d");
                let s=[{x:10,y:10}],d={x:1,y:0},f={x:15,y:10},score=0;
                document.addEventListener("keydown",e=>{
                  if(e.key==="ArrowUp"&&d.y===0)d={x:0,y:-1};
                  if(e.key==="ArrowDown"&&d.y===0)d={x:0,y:1};
                  if(e.key==="ArrowLeft"&&d.x===0)d={x:-1,y:0};
                  if(e.key==="ArrowRight"&&d.x===0)d={x:1,y:0};
                  if(e.key==="Enter"){s=[{x:10,y:10}];d={x:1,y:0};score=0;}
                });
                setInterval(()=>{
                  let h={x:s[0].x+d.x,y:s[0].y+d.y};
                  if(h.x<0||h.y<0||h.x>=30||h.y>=20||s.some(z=>z.x===h.x&&z.y===h.y)){
                    s=[{x:10,y:10}];d={x:1,y:0};score=0;return;
                  }
                  s.unshift(h);
                  if(h.x===f.x&&h.y===f.y){score++;f={x:Math.floor(Math.random()*30),y:Math.floor(Math.random()*20)}}
                  else s.pop();
                  x.clearRect(0,0,360,240);x.fillStyle="#39a852";s.forEach(z=>x.fillRect(z.x*12,z.y*12,11,11));
                  x.fillStyle="#e33";x.fillRect(f.x*12,f.y*12,11,11);x.fillStyle="#111";x.fillText("Score: "+score,8,232);
                },110);
                </script>
                """
            else:
                html = """
                <div style="font-family:Arial;text-align:center">
                <canvas id="dino" width="500" height="180" style="border:2px solid #333"></canvas>
                <p>Press Space to jump. Avoid the cactus. Press Enter to restart.</p>
                </div>
                <script>
                const c=document.getElementById("dino"),x=c.getContext("2d");
                let py=130,vy=0,obs=500,score=0,alive=true;
                document.addEventListener("keydown",e=>{
                  if(e.code==="Space"&&py>=130){vy=-11}
                  if(e.key==="Enter"){py=130;vy=0;obs=500;score=0;alive=true}
                });
                setInterval(()=>{
                  if(!alive)return;
                  vy+=0.6;py+=vy;if(py>130){py=130;vy=0}
                  obs-=6;if(obs<0){obs=500+Math.random()*160;score++}
                  if(obs<60&&obs>25&&py>105){alive=false}
                  x.clearRect(0,0,500,180);x.fillStyle="#444";x.fillRect(0,150,500,3);
                  x.fillStyle="#222";x.fillRect(50,py,30,20);
                  x.fillStyle="#3a3";x.fillRect(obs,125,12,25);
                  x.fillStyle="#111";x.fillText("Score: "+score+(alive?"":"  GAME OVER"),10,20);
                },30);
                </script>
                """
            components.html(html, height=250)
            st.info("When you finish the game, record this puzzle as completed so MindMate will not select it again.")
            game_score = st.number_input(
                "Your game score",
                min_value=0,
                max_value=10000,
                value=0,
                step=1,
                key=f"game_score_{puzzle_id}",
            )
            if st.button("✅ Finish & Record This Game", key=f"finish_{puzzle_id}"):
                record_puzzle(
                    st.session_state.user_id,
                    puzzle_id,
                    ptype,
                    float(game_score),
                )
                st.session_state.selected_puzzle = None
                st.success("Puzzle recorded. It will not be selected again for you.")
                st.rerun()

        if st.button("➡️ Next New Puzzle"):
            st.session_state.selected_puzzle = None
            st.rerun()

# ============================================================
# ANALYTICS
# ============================================================
elif st.session_state.page == "Analytics":
    st.title("📊 Analytics")
    st.caption("Current MindMate performance — no previous-semester data required.")

    sdf = study_df(st.session_state.user_id)
    qdf = quiz_df(st.session_state.user_id)
    cdf = coding_df(st.session_state.user_id)
    stress = stress_df(st.session_state.user_id)

    total_study = int(sdf["actual_minutes"].sum()) if not sdf.empty else 0
    quiz_avg = float(qdf["score"].mean()) if not qdf.empty else 0
    coding_totals = coding_current_totals(st.session_state.user_id)
    solved = int(coding_totals["solved"])

    a, b, c = st.columns(3)
    a.metric("Study Time", f"{total_study} min")
    b.metric("Quiz Average", f"{quiz_avg:.1f}%")
    c.metric("Programs Solved", solved)

    st.subheader("📈 Weekly Study Improvement")
    if not sdf.empty:
        temp = sdf.copy()
        temp["date"] = temp["started_at"].str[:10]
        daily = temp.groupby("date")["actual_minutes"].sum().reset_index()
        daily["date"] = pd.to_datetime(daily["date"])
        fig = px.line(daily, x="date", y="actual_minutes", markers=True,
                      title="Study Minutes by Date")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Complete study sessions to see this graph.")

    st.subheader("📝 Quiz Performance")
    if not qdf.empty:
        qtemp = qdf.copy()
        qtemp["date"] = qtemp["attempted_at"].str[:10]
        weekly = qtemp.groupby("date")["score"].mean().reset_index()
        weekly["date"] = pd.to_datetime(weekly["date"])
        fig = px.bar(weekly, x="date", y="score", range_y=[0, 100],
                     title="Quiz Marks by Date")
        st.plotly_chart(fig, use_container_width=True)

        topic = qdf.groupby(["subject", "topic"])["score"].mean().reset_index()
        topic["label"] = topic["subject"] + " — " + topic["topic"]
        fig = px.bar(topic.sort_values("score"), x="score", y="label",
                     orientation="h", range_x=[0, 100],
                     title="Topic Strength")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Take quizzes after study sessions to generate quiz analytics.")

    st.subheader("💻 Coding Skill")
    if not cdf.empty:
        lang = cdf.groupby("language").agg(
            attempted=("attempted", "sum"),
            solved=("solved", "sum")
        ).reset_index()
        lang["skill"] = lang["solved"] / lang["attempted"].replace(0, 1) * 100
        lang["status"] = lang["skill"].apply(
            lambda x: "Strong" if x >= 80 else ("OK" if x >= 50 else "Weak")
        )
        fig = px.bar(lang, x="language", y="skill", range_y=[0, 100],
                     title="Language Strength")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(lang, use_container_width=True, hide_index=True)

    st.subheader("😌 Stress Trend")
    if not stress.empty:
        fig = px.line(stress, x="logged_at", y="level", markers=True,
                      range_y=[0, 10], title="Stress Level Over Time")
        st.plotly_chart(fig, use_container_width=True)

    # Current marks are quiz marks. There is no previous-semester CGPA/marks.
    st.subheader("🎓 Current Performance Summary")
    summary = pd.DataFrame(
        {
            "Metric": ["Study time", "Quiz average", "Programs solved", "Quiz attempts"],
            "Value": [
                f"{total_study} min",
                f"{quiz_avg:.1f}%",
                solved,
                len(qdf),
            ],
        }
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)

# ============================================================
# SETTINGS
# ============================================================
elif st.session_state.page == "Settings":
    st.title("⚙️ Settings")
    st.caption("You control your semester subjects, topics, exams and coding identity. Coding counts are fetched from the selected platform; they are never entered manually.")

    tab_profile, tab_subjects, tab_exams, tab_questions = st.tabs(
        ["👤 Profile", "📚 Semester Subjects", "🗓️ Exam Schedule", "📝 Question Bank"]
    )

    with tab_profile:
        coding_id, platform, semester = profile(st.session_state.user_id)
        st.write(f"**Account:** {st.session_state.username}")
        st.write(f"**Name:** {st.session_state.name}")

        new_semester = st.text_input("Semester", value=semester)
        new_coding_id = st.text_input("Coding User ID", value=coding_id)
        new_platform = st.selectbox(
            "Coding Platform",
            ["Codeforces", "LeetCode"],
            index=["Codeforces", "LeetCode"].index(platform)
            if platform in ["Codeforces", "LeetCode"] else 0,
        )

        if st.button("💾 Save Profile"):
            save_profile(st.session_state.user_id, new_coding_id, new_platform, new_semester)
            st.success("Profile saved.")

    with tab_subjects:
        st.subheader("Your Semester Subjects")
        subjects = user_subjects(st.session_state.user_id)

        with st.form("add_subject"):
            new_subject = st.text_input("Enter your subject name")
            if st.form_submit_button("➕ Add Subject"):
                add_subject(st.session_state.user_id, new_subject)
                st.rerun()

        for subject in subjects:
            cols = st.columns([3, 2, 1])
            cols[0].write(f"📘 {subject}")
            topics = user_topics(st.session_state.user_id, subject)
            cols[1].write(f"{len(topics)} topic(s)")
            if cols[2].button("Remove", key=f"remove_sub_{subject}"):
                remove_subject(st.session_state.user_id, subject)
                st.rerun()

        if subjects:
            st.subheader("Add Topic to a Subject")
            selected_subject = st.selectbox("Subject", subjects)
            new_topic = st.text_input("Topic name")
            if st.button("➕ Add Topic"):
                add_topic(st.session_state.user_id, selected_subject, new_topic)
                st.success("Topic added.")

    with tab_exams:
        subjects = user_subjects(st.session_state.user_id)
        if not subjects:
            st.info("Add subjects first.")
        else:
            with st.form("exam_form"):
                exam_subject = st.selectbox("Exam subject", subjects)
                exam_date = st.date_input("Exam date", date.today())
                exam_time = st.time_input("Exam time", datetime.now().time().replace(second=0, microsecond=0))
                if st.form_submit_button("➕ Add Exam"):
                    save_exam(
                        st.session_state.user_id,
                        exam_subject,
                        exam_date,
                        exam_time.strftime("%H:%M"),
                    )
                    st.success("Exam schedule saved.")

        edf = exams_df(st.session_state.user_id)
        if not edf.empty:
            st.dataframe(edf, use_container_width=True, hide_index=True)
            for _, row in edf.iterrows():
                if st.button(
                    f"Delete {row['subject']} — {row['exam_date']} {row['exam_time']}",
                    key=f"del_exam_{row['id']}",
                ):
                    delete_exam(st.session_state.user_id, int(row["id"]))
                    st.rerun()

    with tab_questions:
        st.subheader("Add Your Own Quiz Questions")
        subjects = user_subjects(st.session_state.user_id)
        if not subjects:
            st.info("Add semester subjects first.")
        else:
            with st.form("question_form"):
                qs = st.selectbox("Subject", subjects)
                qt = st.text_input("Topic")
                qq = st.text_area("Question")
                o1 = st.text_input("Option 1")
                o2 = st.text_input("Option 2")
                o3 = st.text_input("Option 3")
                o4 = st.text_input("Option 4")
                correct = st.selectbox("Correct answer", [o1, o2, o3, o4])
                difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])

                if st.form_submit_button("➕ Add Question"):
                    options = [o1, o2, o3, o4]
                    if not qt.strip() or not qq.strip() or any(not x.strip() for x in options):
                        st.error("Complete the subject, topic, question and all four options.")
                    elif correct not in options:
                        st.error("Select a valid correct answer.")
                    else:
                        insert_custom_question(
                            qs, qt.strip(), qq.strip(), options, correct, difficulty
                        )
                        add_topic(st.session_state.user_id, qs, qt.strip())
                        st.success(
                            "Question added. Its unique ID will prevent it being repeated "
                            "for this student/topic."
                        )

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption(
    "MindMate • Study Focus → Quiz → Analysis → Coding Skill → Tomorrow's Plan"
)
