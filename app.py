import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import random
import os
import hashlib
import json
import time
from PIL import Image

# Optional packages
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


# ============================================================
# MINDMATE - Smart Semester Study Planner & Analyzer
# Version 9.0 - Clean Working Build
# ============================================================

APP_VERSION = "9.0"
DATA_DIR = "mindmate_data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SALT = "MindMate_Salt_2024"

os.makedirs(DATA_DIR, exist_ok=True)

st.set_page_config(
    page_title="MindMate | Smart Study Planner",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------- CSS -------------------------
st.markdown(
    """
    <style>
    .main-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .subtitle {
        font-size: 18px;
        opacity: .75;
        margin-bottom: 25px;
    }
    .card {
        padding: 18px;
        border-radius: 14px;
        border: 1px solid rgba(128,128,128,.25);
        margin-bottom: 12px;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-card {
        padding: 15px;
        border-radius: 12px;
        color: white;
        text-align: center;
        background: linear-gradient(135deg, #667eea, #764ba2);
    }
    .stress-meter {
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin: 10px 0;
    }
    .stress-low { background: #d4edda; border: 2px solid #28a745; }
    .stress-medium { background: #fff3cd; border: 2px solid #ffc107; }
    .stress-high { background: #f8d7da; border: 2px solid #dc3545; }
    .stress-very-high { background: #f5c6cb; border: 2px solid #721c24; }
    .bot-status {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .bot-online { background: #d4edda; color: #155724; }
    .bot-offline { background: #f8d7da; color: #721c24; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------- AUTH -------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256((password + SALT).encode()).hexdigest()


def load_users():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"admin": hash_password("admin123")}


def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
        return True
    except Exception:
        return False


def verify_user(username, password):
    users = load_users()
    return username in users and users[username] == hash_password(password)


def create_user(username, password):
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    users = load_users()
    if username in users:
        return False, "Username already exists."

    users[username] = hash_password(password)
    return (True, "Account created successfully.") if save_users(users) else (
        False,
        "Could not save the account.",
    )


# ------------------------- DATA -------------------------
SCHEMAS = {
    "subjects": ["subject", "units", "difficulty", "confidence", "exam_date", "completed_units"],
    "sessions": ["date", "subject", "topic", "duration_min", "technique", "mood", "distractions", "productivity", "quiz_score"],
    "quiz_results": ["date", "subject", "topic", "score", "questions", "attempt_id"],
    "previous_semester": ["subject", "semester", "marks", "grade", "year"],
    "mid_marks": ["subject", "mid_term", "marks", "date_taken", "semester"],
    "activity_feed": ["timestamp", "activity_type", "description", "details", "user"],
    "stress_logs": ["timestamp", "stress_level", "user", "recommendation"],
}


def empty_df(name):
    return pd.DataFrame(columns=SCHEMAS[name])


def load_df(name):
    path = os.path.join(DATA_DIR, f"{name}.csv")
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return empty_df(name)

        df = pd.read_csv(path)
        for col in SCHEMAS[name]:
            if col not in df.columns:
                df[col] = None

        df = df[SCHEMAS[name]]

        date_cols = [
            "exam_date",
            "date",
            "date_taken",
            "timestamp",
        ]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df
    except Exception:
        return empty_df(name)


def save_all():
    try:
        for name in SCHEMAS:
            if name in st.session_state:
                st.session_state[name].to_csv(
                    os.path.join(DATA_DIR, f"{name}.csv"),
                    index=False,
                )
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False


def init_state():
    for name in SCHEMAS:
        if name not in st.session_state:
            st.session_state[name] = load_df(name)

    defaults = {
        "logged_in": False,
        "username": "",
        "page": "🏠 Dashboard",
        "daily_streak": 0,
        "last_activity_date": None,
        "stress_level": 0.0,
        "chat_history": [],
        "bot_model": None,
        "bot_available": False,
        "quiz_questions": [],
        "quiz_answers": {},
        "quiz_submitted": False,
        "quiz_subject": "",
        "quiz_topic": "",
        "current_attempt_id": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()

DIFFICULTY = {"Easy": 1, "Medium": 2, "Hard": 3, "Very Hard": 4}
TECHNIQUES = [
    "Pomodoro",
    "Active Recall",
    "Practice Problems",
    "Mind Mapping",
    "Feynman Technique",
    "Spaced Repetition",
]

TOPIC_BANK = {
    "Python": [
        ("Which keyword defines a function in Python?", ["func", "def", "function", "define"], 1),
        ("Which data type stores key-value pairs?", ["list", "tuple", "set", "dictionary"], 3),
        ("Which symbol starts a comment in Python?", ["//", "#", "/*", "--"], 1),
        ("Which method adds an item to a list?", ["add()", "insertEnd()", "append()", "push()"], 2),
        ("What does len() return?", ["Memory size", "Number of elements", "Last index", "Data type"], 1),
    ],
    "C++": [
        ("Which keyword is used to create a class?", ["object", "class", "structs", "define"], 1),
        ("Which operator accesses members through an object?", [".", "->", "::", "#"], 0),
        ("Which symbol begins a single-line comment?", ["#", "//", "/*", "--"], 1),
        ("Which function is the entry point of a C++ program?", ["start()", "run()", "main()", "execute()"], 2),
    ],
    "Data Structures": [
        ("Which structure follows LIFO?", ["Queue", "Stack", "Tree", "Graph"], 1),
        ("Which structure follows FIFO?", ["Stack", "Queue", "Heap", "Tree"], 1),
        ("Binary search requires the data to be?", ["Random", "Sorted", "Duplicated", "Hashed"], 1),
        ("Which traversal visits Root, Left, Right?", ["Inorder", "Postorder", "Preorder", "Level only"], 2),
    ],
    "DBMS": [
        ("Which normal form removes partial dependency?", ["1NF", "2NF", "3NF", "BCNF"], 1),
        ("Which SQL command retrieves data?", ["GET", "SELECT", "FETCHALL", "OPEN"], 1),
        ("A primary key must be?", ["Duplicate", "Nullable", "Unique", "Optional"], 2),
        ("Which command adds rows to a table?", ["INSERT", "ADD", "PUT", "APPEND"], 0),
    ],
    "Mathematics": [
        ("Derivative of x²?", ["x", "2x", "x²", "2"], 1),
        ("Value of sin(90°)?", ["0", "1", "-1", "Undefined"], 1),
        ("Slope of a horizontal line?", ["1", "0", "Undefined", "-1"], 1),
        ("Determinant of [[a,b],[c,d]]?", ["ab-cd", "ad-bc", "ac-bd", "a+b+c+d"], 1),
    ],
    "AI/ML": [
        ("Which is supervised learning?", ["Clustering", "Classification", "PCA", "Association rules"], 1),
        ("Which algorithm can be used for classification and regression?", ["Random Forest", "Apriori only", "K-Means only", "PCA"], 0),
        ("What is overfitting?", ["Model too simple", "Model memorizes training data too closely", "No training", "Missing data"], 1),
        ("Which metric is common for regression?", ["Accuracy", "MAE", "Precision", "Recall"], 1),
    ],
}

GENERIC_QUESTIONS = [
    ("What is critical thinking?", ["Following instructions", "Analyzing information", "Memorizing facts", "Copying answers"], 1),
    ("Which skill is essential for effective learning?", ["Time management", "Social media", "Watching videos", "Skipping topics"], 0),
]


# ------------------------- HELPERS -------------------------
def add_to_feed(activity_type, description, details=""):
    entry = pd.DataFrame([{
        "timestamp": pd.Timestamp.now(),
        "activity_type": activity_type,
        "description": description,
        "details": details,
        "user": st.session_state.username,
    }])
    st.session_state.activity_feed = pd.concat(
        [st.session_state.activity_feed, entry],
        ignore_index=True,
    )
    update_streak()
    save_all()


def update_streak():
    today = date.today()
    last_date = st.session_state.last_activity_date

    if last_date is None:
        st.session_state.daily_streak = 1
    else:
        if isinstance(last_date, pd.Timestamp):
            last_date = last_date.date()
        elif isinstance(last_date, str):
            try:
                last_date = datetime.strptime(last_date, "%Y-%m-%d").date()
            except ValueError:
                last_date = None

        if last_date == today:
            return
        elif last_date == today - timedelta(days=1):
            st.session_state.daily_streak += 1
        else:
            st.session_state.daily_streak = 1

    st.session_state.last_activity_date = today


def get_topic_for_subject(subject):
    aliases = {
        "Python": ["Functions", "Lists & Dictionaries", "Exception Handling", "OOP", "File Handling"],
        "C++": ["Classes & Objects", "Constructors", "Inheritance", "Polymorphism", "Templates"],
        "Data Structures": ["Stacks & Queues", "Trees", "Searching", "Sorting", "Graphs"],
        "DBMS": ["Normalization", "SQL", "Transactions", "Keys", "Constraints"],
        "Mathematics": ["Calculus", "Matrices", "Differentiation", "Integration", "Probability"],
        "AI/ML": ["Supervised Learning", "Regression", "Classification", "Clustering", "Neural Networks"],
    }
    for key, topics in aliases.items():
        if key.lower() in str(subject).lower():
            return random.choice(topics)
    return f"{subject} Revision"


def available_questions(subject):
    subject = str(subject)
    matched = None

    for key in TOPIC_BANK:
        if key.lower() in subject.lower() or subject.lower() in key.lower():
            matched = key
            break

    pool = TOPIC_BANK.get(matched, GENERIC_QUESTIONS).copy()
    random.shuffle(pool)
    return pool[: min(5, len(pool))]


def generate_attempt_id(subject, topic):
    raw = f"{subject}_{topic}_{datetime.now().isoformat()}_{random.random()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def get_grade(marks):
    marks = float(marks)
    if marks >= 90:
        return "A+"
    if marks >= 80:
        return "A"
    if marks >= 70:
        return "B+"
    if marks >= 60:
        return "B"
    if marks >= 50:
        return "C+"
    if marks >= 40:
        return "C"
    if marks >= 33:
        return "D"
    return "F"


def calculate_priority(row):
    try:
        today = pd.Timestamp.today().normalize()
        exam = pd.to_datetime(row["exam_date"], errors="coerce")

        if pd.isna(exam):
            return 0

        days_left = max((exam.normalize() - today).days, 1)
        difficulty = DIFFICULTY.get(str(row["difficulty"]), 2)
        confidence = int(row["confidence"])
        units = max(int(row["units"]), 1)
        completed = int(row["completed_units"])

        urgency = min(30 / days_left, 30)
        confidence_gap = 6 - confidence
        remaining = max(units - completed, 0)
        syllabus = remaining / units * 5

        return round(
            urgency * 2
            + difficulty * 2
            + confidence_gap * 1.5
            + syllabus,
            2,
        )
    except Exception:
        return 0


def generate_smart_daily_plan():
    subjects = st.session_state.subjects.copy()
    sessions = st.session_state.sessions.copy()
    quizzes = st.session_state.quiz_results.copy()

    if subjects.empty:
        return []

    today = pd.Timestamp.today().normalize()
    plan = []

    for _, row in subjects.iterrows():
        try:
            subject = str(row["subject"])
            exam = pd.to_datetime(row["exam_date"], errors="coerce")
            days_left = 30 if pd.isna(exam) else max((exam.normalize() - today).days, 1)

            difficulty = DIFFICULTY.get(str(row["difficulty"]), 2)
            confidence = int(row["confidence"])
            units = max(int(row["units"]), 1)
            completed = int(row["completed_units"])
            remaining = max(units - completed, 0)

            quiz_avg = None
            if not quizzes.empty:
                q = quizzes[quizzes["subject"].astype(str).str.lower() == subject.lower()]
                if not q.empty:
                    quiz_avg = float(pd.to_numeric(q["score"], errors="coerce").mean())

            recent_hours = 0
            if not sessions.empty:
                ss = sessions[
                    sessions["subject"].astype(str).str.lower() == subject.lower()
                ].copy()
                if not ss.empty:
                    ss["date"] = pd.to_datetime(ss["date"], errors="coerce")
                    ss = ss[ss["date"] >= today - timedelta(days=7)]
                    recent_hours = (
                        pd.to_numeric(ss["duration_min"], errors="coerce").fillna(0).sum()
                        / 60
                    )

            urgency_score = min(30 / days_left, 30)
            difficulty_score = difficulty * 2
            confidence_score = (6 - confidence) * 2
            syllabus_score = remaining / units * 10
            quiz_score = (100 - quiz_avg) / 10 if quiz_avg is not None else 5
            study_penalty = min(recent_hours * 0.5, 5)

            smart_score = (
                urgency_score
                + difficulty_score
                + confidence_score
                + syllabus_score
                + quiz_score
                - study_penalty
            )

            reasons = []
            if days_left <= 7:
                reasons.append(f"Exam in {days_left} day(s)")
            if confidence <= 2:
                reasons.append("Low confidence")
            if remaining > 0:
                reasons.append(f"{remaining} unit(s) remaining")
            if quiz_avg is not None and quiz_avg < 60:
                reasons.append(f"Quiz average {quiz_avg:.0f}%")
            if not reasons:
                reasons.append("Good opportunity for revision")

            plan.append({
                "subject": subject,
                "topic": get_topic_for_subject(subject),
                "score": smart_score,
                "days_left": days_left,
                "confidence": confidence,
                "remaining_units": remaining,
                "quiz_avg": quiz_avg,
                "recent_hours": recent_hours,
                "reason": " + ".join(reasons),
            })
        except Exception:
            continue

    return sorted(plan, key=lambda x: x["score"], reverse=True)


# ------------------------- STRESS -------------------------
def detect_stress_from_face(image):
    """
    Demo-only image heuristic.
    This is NOT a clinically validated stress detector.
    """
    try:
        if not CV2_AVAILABLE:
            return None

        arr = np.array(image)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) if len(arr.shape) == 3 else arr

        variance = float(np.var(gray))
        normalized = min(variance / 1000.0, 1.0)
        stress = 0.3 + 0.7 * normalized
        return max(0.0, min(1.0, stress))
    except Exception:
        return None


def get_stress_recommendation(stress_level):
    if stress_level < 0.3:
        return {
            "level": "Low Stress 😊",
            "color": "stress-low",
            "recommendation": "You're doing great. Keep studying and take short breaks.",
            "activities": ["Continue studying", "Take a 5-minute break", "Stay hydrated"],
        }
    if stress_level < 0.5:
        return {
            "level": "Moderate Stress 😐",
            "color": "stress-medium",
            "recommendation": "Try deep breathing or a short walk before continuing.",
            "activities": ["Deep breathing", "Short walk", "Listen to calm music"],
        }
    if stress_level < 0.7:
        return {
            "level": "High Stress 😰",
            "color": "stress-high",
            "recommendation": "Take a longer break and use a relaxation technique.",
            "activities": ["15-minute break", "Stretching", "Meditation", "Drink water"],
        }
    return {
        "level": "Very High Stress 😫",
        "color": "stress-very-high",
        "recommendation": "Pause studying and give yourself time to relax and reset.",
        "activities": ["30-minute break", "Walk", "Deep breathing", "Calming music"],
    }


# ------------------------- GEMINI -------------------------
def setup_gemini(api_key):
    if not GEMINI_AVAILABLE:
        return None, "google-generativeai is not installed."

    if not api_key.strip():
        return None, "Enter a Gemini API key."

    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel("gemini-pro")
        return model, "Success"
    except Exception as e:
        return None, str(e)


def get_bot_response(prompt, model, context=""):
    if model is None:
        return "AI Assistant is not configured. Add your Gemini API key in the sidebar."

    try:
        full_prompt = f"""
You are MindMate, an AI study assistant.

Student context:
{context}

Student question:
{prompt}

Give a clear, concise, educational answer. If you are uncertain, say so.
"""
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"AI error: {e}"


# ------------------------- LOGIN -------------------------
def show_login():
    st.markdown('<div class="main-title">🧠 MindMate</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Smart Semester Study Planner & Analyzer</div>',
        unsafe_allow_html=True,
    )

    login_tab, signup_tab = st.tabs(["🔐 Login", "📝 Create Account"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", type="primary")

        if submitted:
            if verify_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.session_state.page = "🏠 Dashboard"
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.info("Default account: admin / admin123")

    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("New username")
            new_password = st.text_input("New password", type="password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account")

        if submitted:
            if new_password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, message = create_user(new_username, new_password)
                if ok:
                    st.success(message)
                else:
                    st.error(message)


# ------------------------- DASHBOARD -------------------------
def show_dashboard():
    st.markdown('<div class="main-title">🧠 MindMate</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="subtitle">Welcome, <b>{st.session_state.username}</b> • Version {APP_VERSION}</div>',
        unsafe_allow_html=True,
    )

    subjects = st.session_state.subjects
    sessions = st.session_state.sessions
    quizzes = st.session_state.quiz_results

    total_subjects = len(subjects)
    total_minutes = pd.to_numeric(sessions["duration_min"], errors="coerce").fillna(0).sum() if not sessions.empty else 0
    avg_quiz = pd.to_numeric(quizzes["score"], errors="coerce").mean() if not quizzes.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📚 Subjects", total_subjects)
    c2.metric("⏱️ Study Hours", f"{total_minutes / 60:.1f}")
    c3.metric("📝 Quiz Average", f"{avg_quiz:.0f}%" if avg_quiz else "—")
    c4.metric("🔥 Streak", f"{st.session_state.daily_streak} day(s)")

    st.markdown("### 🎯 Smart Daily Plan")
    plan = generate_smart_daily_plan()

    if not plan:
        st.info("Add subjects to generate your smart study plan.")
    else:
        for item in plan[:5]:
            with st.container(border=True):
                a, b, c = st.columns([2, 2, 1])
                a.markdown(f"**{item['subject']}**")
                a.write(f"Topic: {item['topic']}")
                b.write(item["reason"])
                c.metric("Priority", f"{item['score']:.1f}")

    if not st.session_state.activity_feed.empty:
        st.markdown("### 📰 Recent Activity")
        feed = st.session_state.activity_feed.copy()
        feed = feed[feed["user"] == st.session_state.username]
        if not feed.empty:
            feed = feed.sort_values("timestamp", ascending=False).head(8)
            for _, row in feed.iterrows():
                st.write(
                    f"**{row['activity_type']}** — {row['description']} "
                    f"({row['details']})"
                )


# ------------------------- SUBJECTS -------------------------
def show_subjects():
    st.header("📚 Subjects")

    with st.form("add_subject"):
        c1, c2, c3 = st.columns(3)
        subject = c1.text_input("Subject")
        units = c2.number_input("Total units", min_value=1, value=5)
        completed = c3.number_input("Completed units", min_value=0, max_value=units, value=0)

        c4, c5, c6 = st.columns(3)
        difficulty = c4.selectbox("Difficulty", list(DIFFICULTY))
        confidence = c5.slider("Confidence", 1, 5, 3)
        exam_date = c6.date_input("Exam date", value=date.today() + timedelta(days=14))

        submitted = st.form_submit_button("➕ Add Subject", type="primary")

    if submitted:
        if not subject.strip():
            st.error("Enter a subject name.")
        else:
            new_row = pd.DataFrame([{
                "subject": subject.strip(),
                "units": int(units),
                "difficulty": difficulty,
                "confidence": int(confidence),
                "exam_date": pd.Timestamp(exam_date),
                "completed_units": int(completed),
            }])
            st.session_state.subjects = pd.concat(
                [st.session_state.subjects, new_row],
                ignore_index=True,
            )
            save_all()
            add_to_feed("Subject Added", subject.strip(), f"{units} units")
            st.success("Subject added.")
            st.rerun()

    if not st.session_state.subjects.empty:
        df = st.session_state.subjects.copy()
        df["priority"] = df.apply(calculate_priority, axis=1)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("### ✏️ Update Progress")
        options = df["subject"].astype(str).tolist()
        selected = st.selectbox("Select subject", options)

        row_index = df.index[df["subject"].astype(str) == selected][0]
        row = st.session_state.subjects.loc[row_index]

        completed = st.number_input(
            "Completed units",
            min_value=0,
            max_value=int(row["units"]),
            value=int(row["completed_units"]),
            key=f"progress_{row_index}",
        )

        if st.button("💾 Save Progress"):
            st.session_state.subjects.loc[row_index, "completed_units"] = completed
            save_all()
            add_to_feed("Progress Updated", selected, f"{completed}/{row['units']} units")
            st.success("Progress updated.")
            st.rerun()


# ------------------------- STUDY SESSION -------------------------
def show_study():
    st.header("⏱️ Study Session")

    subjects = st.session_state.subjects["subject"].astype(str).tolist()

    if not subjects:
        st.warning("Add at least one subject first.")
        return

    subject = st.selectbox("Subject", subjects)
    topic = st.text_input("Topic", value=get_topic_for_subject(subject))
    duration = st.slider("Duration (minutes)", 5, 180, 45)
    technique = st.selectbox("Technique", TECHNIQUES)
    mood = st.select_slider("Mood", options=["😫", "😐", "🙂", "😊", "🔥"])
    distractions = st.number_input("Distractions", 0, 50, 0)
    productivity = st.slider("Productivity", 0, 100, 80)

    if st.button("▶️ Start Study Session", type="primary"):
        end_time = time.time() + duration * 60
        progress = st.progress(0)
        timer_box = st.empty()

        while True:
            remaining = max(0, int(end_time - time.time()))
            mins, secs = divmod(remaining, 60)
            timer_box.markdown(
                f"<h1 style='text-align:center'>{mins:02d}:{secs:02d}</h1>",
                unsafe_allow_html=True,
            )

            progress.progress(
                min(1.0, (duration * 60 - remaining) / (duration * 60))
            )

            if remaining <= 0:
                break
            time.sleep(1)

        st.success("🎉 Study session completed!")

        new_session = pd.DataFrame([{
            "date": pd.Timestamp.now(),
            "subject": subject,
            "topic": topic,
            "duration_min": duration,
            "technique": technique,
            "mood": mood,
            "distractions": distractions,
            "productivity": productivity,
            "quiz_score": None,
        }])

        st.session_state.sessions = pd.concat(
            [st.session_state.sessions, new_session],
            ignore_index=True,
        )
        save_all()
        add_to_feed("Study Session", subject, f"{duration} minutes")
        st.rerun()


# ------------------------- QUIZ -------------------------
def show_quiz():
    st.header("📝 Practice Quiz")

    subjects = st.session_state.subjects["subject"].astype(str).tolist()

    if not subjects:
        st.warning("Add a subject first.")
        return

    if not st.session_state.quiz_questions:
        subject = st.selectbox("Subject", subjects, key="quiz_subject_select")
        topic = st.text_input("Topic", value=get_topic_for_subject(subject), key="quiz_topic_input")

        if st.button("🚀 Start Quiz", type="primary"):
            st.session_state.quiz_subject = subject
            st.session_state.quiz_topic = topic
            st.session_state.quiz_questions = available_questions(subject)
            st.session_state.quiz_answers = {}
            st.session_state.quiz_submitted = False
            st.session_state.current_attempt_id = generate_attempt_id(subject, topic)
            st.rerun()
        return

    subject = st.session_state.quiz_subject
    topic = st.session_state.quiz_topic

    st.write(f"**Subject:** {subject}  |  **Topic:** {topic}")

    for i, (question, options, correct) in enumerate(st.session_state.quiz_questions):
        answer = st.radio(
            f"{i + 1}. {question}",
            options,
            index=None,
            key=f"quiz_{st.session_state.current_attempt_id}_{i}",
        )
        st.session_state.quiz_answers[i] = answer

    if st.button("✅ Submit Quiz", type="primary"):
        correct_count = 0

        for i, (_, options, correct) in enumerate(st.session_state.quiz_questions):
            if st.session_state.quiz_answers.get(i) == options[correct]:
                correct_count += 1

        total = len(st.session_state.quiz_questions)
        score = round(correct_count / total * 100, 1) if total else 0

        result = pd.DataFrame([{
            "date": pd.Timestamp.now(),
            "subject": subject,
            "topic": topic,
            "score": score,
            "questions": total,
            "attempt_id": st.session_state.current_attempt_id,
        }])

        st.session_state.quiz_results = pd.concat(
            [st.session_state.quiz_results, result],
            ignore_index=True,
        )

        save_all()
        add_to_feed("Quiz Completed", subject, f"Score: {score:.1f}%")

        st.success(f"🎉 Score: {score:.1f}%")
        st.info(f"You got {correct_count} out of {total} correct.")

        st.session_state.quiz_questions = []
        st.session_state.quiz_answers = {}
        st.session_state.current_attempt_id = None

        if score < 60:
            st.warning("Focus on this topic again in your next study session.")

        st.rerun()


# ------------------------- STRESS PAGE -------------------------
def show_stress_detection():
    st.header("🧘 Stress Detection")
    st.caption("Use this as a self-check. The camera feature is only a demo heuristic and is not a medical or clinical stress measurement.")

    tab1, tab2 = st.tabs(["📝 Stress Check", "📊 Stress History"])

    with tab1:
        stress = st.slider(
            "How stressed do you feel right now?",
            0,
            100,
            50,
        )

        if st.button("💾 Save Stress Level", type="primary"):
            level = stress / 100
            info = get_stress_recommendation(level)

            st.session_state.stress_level = level

            st.markdown(
                f"""
                <div class="stress-meter {info['color']}">
                    <h3>{info['level']}</h3>
                    <p>Score: {stress}%</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("### 💡 Recommendation")
            st.write(info["recommendation"])

            st.markdown("### 📋 Suggested Activities")
            for activity in info["activities"]:
                st.write(f"• {activity}")

            new_log = pd.DataFrame([{
                "timestamp": pd.Timestamp.now(),
                "stress_level": level,
                "user": st.session_state.username,
                "recommendation": info["recommendation"],
            }])

            st.session_state.stress_logs = pd.concat(
                [st.session_state.stress_logs, new_log],
                ignore_index=True,
            )

            save_all()
            add_to_feed("Stress Check", info["level"], f"Score: {stress}%")

        if CV2_AVAILABLE:
            st.markdown("---")
            st.subheader("📸 Camera Demo")
            image = st.camera_input("Capture an image")

            if image is not None:
                img = Image.open(image)
                detected = detect_stress_from_face(img)

                if detected is not None:
                    info = get_stress_recommendation(detected)
                    st.image(img, caption="Captured image", use_container_width=True)
                    st.info(
                        f"Demo estimate: {detected * 100:.0f}% — {info['level']}. "
                        "This is only an image heuristic, not a real stress diagnosis."
                    )
        else:
            st.info("Install opencv-python if you want to enable the camera demo.")

    with tab2:
        logs = st.session_state.stress_logs
        logs = logs[logs["user"] == st.session_state.username].copy()

        if logs.empty:
            st.info("No stress history yet.")
            return

        logs["stress_level"] = pd.to_numeric(logs["stress_level"], errors="coerce")

        c1, c2, c3 = st.columns(3)
        c1.metric("Average", f"{logs['stress_level'].mean() * 100:.0f}%")
        c2.metric("Maximum", f"{logs['stress_level'].max() * 100:.0f}%")
        c3.metric("Minimum", f"{logs['stress_level'].min() * 100:.0f}%")

        fig = px.line(
            logs.sort_values("timestamp"),
            x="timestamp",
            y="stress_level",
            title="Stress Level Trend",
        )
        fig.update_layout(yaxis_range=[0, 1])
        st.plotly_chart(fig, use_container_width=True)


# ------------------------- PERFORMANCE -------------------------
def show_performance():
    st.header("📊 Performance")

    prev = st.session_state.previous_semester
    mid = st.session_state.mid_marks
    quizzes = st.session_state.quiz_results

    c1, c2, c3 = st.columns(3)

    prev_avg = pd.to_numeric(prev["marks"], errors="coerce").mean() if not prev.empty else 0
    mid_avg = pd.to_numeric(mid["marks"], errors="coerce").mean() if not mid.empty else 0
    quiz_avg = pd.to_numeric(quizzes["score"], errors="coerce").mean() if not quizzes.empty else 0

    c1.metric("Previous Semester", f"{prev_avg:.1f}%" if prev_avg else "—")
    c2.metric("Mid Term", f"{mid_avg:.1f}%" if mid_avg else "—")
    c3.metric("Quiz Average", f"{quiz_avg:.1f}%" if quiz_avg else "—")

    st.subheader("➕ Add Previous Semester Mark")
    with st.form("prev_mark_form"):
        subject = st.text_input("Subject")
        marks = st.number_input("Marks", 0.0, 100.0, 70.0)
        semester = st.text_input("Semester", "Previous Semester")
        year = st.number_input("Year", 2000, 2100, date.today().year)

        if st.form_submit_button("Save Mark"):
            row = pd.DataFrame([{
                "subject": subject,
                "semester": semester,
                "marks": marks,
                "grade": get_grade(marks),
                "year": year,
            }])
            st.session_state.previous_semester = pd.concat(
                [st.session_state.previous_semester, row],
                ignore_index=True,
            )
            save_all()
            st.success("Mark saved.")
            st.rerun()

    if not prev.empty:
        st.subheader("Previous Semester Data")
        st.dataframe(prev, use_container_width=True, hide_index=True)

    if not mid.empty:
        st.subheader("Mid-Term Data")
        st.dataframe(mid, use_container_width=True, hide_index=True)


# ------------------------- AI CHATBOT -------------------------
def show_chatbot():
    st.header("🤖 MindMate AI Assistant")

    if not GEMINI_AVAILABLE:
        st.warning(
            "AI package is not installed. Run: pip install google-generativeai"
        )
        return

    if st.session_state.bot_model is None:
        st.info("Configure your Gemini API key in the sidebar.")
        return

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask MindMate a study question...")

    if prompt:
        context = (
            f"Subjects: {st.session_state.subjects['subject'].astype(str).tolist()}\n"
            f"Daily streak: {st.session_state.daily_streak}\n"
        )

        st.session_state.chat_history.append(
            {"role": "user", "content": prompt}
        )

        response = get_bot_response(
            prompt,
            st.session_state.bot_model,
            context,
        )

        st.session_state.chat_history.append(
            {"role": "assistant", "content": response}
        )

        st.rerun()


# ------------------------- SIDEBAR -------------------------
def show_sidebar():
    with st.sidebar:
        st.markdown("## 🧠 MindMate")
        st.caption(f"Version {APP_VERSION}")

        if st.session_state.logged_in:
            st.success(f"Logged in as **{st.session_state.username}**")

            pages = [
                "🏠 Dashboard",
                "📚 Subjects",
                "⏱️ Study Session",
                "📝 Practice Quiz",
                "🧘 Stress Detection",
                "📊 Performance",
                "🤖 AI Assistant",
            ]

            selected = st.radio(
                "Navigation",
                pages,
                index=pages.index(st.session_state.page)
                if st.session_state.page in pages
                else 0,
            )

            st.session_state.page = selected

            st.markdown("---")
            st.markdown("### 🤖 AI Setup")

            api_key = st.text_input(
                "Gemini API key",
                type="password",
                value="",
                help="The key is used only for this running Streamlit session.",
            )

            if api_key:
                model, message = setup_gemini(api_key)
                if model:
                    st.session_state.bot_model = model
                    st.session_state.bot_available = True
                    st.success("AI connected.")
                else:
                    st.session_state.bot_model = None
                    st.session_state.bot_available = False
                    st.error(message)

            st.markdown("---")

            if st.button("💾 Save Data"):
                if save_all():
                    st.success("Saved.")

            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.page = "🏠 Dashboard"
                st.rerun()


# ------------------------- MAIN -------------------------
if not st.session_state.logged_in:
    show_login()
else:
    show_sidebar()

    page = st.session_state.page

    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "📚 Subjects":
        show_subjects()
    elif page == "⏱️ Study Session":
        show_study()
    elif page == "📝 Practice Quiz":
        show_quiz()
    elif page == "🧘 Stress Detection":
        show_stress_detection()
    elif page == "📊 Performance":
        show_performance()
    elif page == "🤖 AI Assistant":
        show_chatbot()
