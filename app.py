import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import random
import os
import hashlib
import json
import time

# Optional packages
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    CV2_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False


# ============================================================
# STUDYWISE - Smart Semester Study Planner & Analyzer
# Final Version
# ============================================================

st.set_page_config(
    page_title="StudyWise | Smart Study Planner",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------- CSS -------------------------------
st.markdown("""
<style>
.main-title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.subtitle {font-size:18px; opacity:.75; margin-bottom:25px;}
.card {
    padding:18px; border-radius:14px;
    border:1px solid rgba(128,128,128,.25);
    margin-bottom:12px; background:white;
    box-shadow:0 2px 4px rgba(0,0,0,.05);
}
.metric-card {
    padding:15px; border-radius:12px; color:white;
    text-align:center;
    background:linear-gradient(135deg,#667eea,#764ba2);
}
.timer-box {
    padding:25px; border-radius:18px;
    text-align:center;
    background:linear-gradient(135deg,#667eea,#764ba2);
    color:white; margin:15px 0;
}
.timer-number {font-size:64px; font-weight:800; font-family:monospace;}
.stress-meter {padding:15px; border-radius:12px; text-align:center; margin:10px 0;}
.stress-low {background:#d4edda; border:2px solid #28a745;}
.stress-medium {background:#fff3cd; border:2px solid #ffc107;}
.stress-high {background:#f8d7da; border:2px solid #dc3545;}
.stress-very-high {background:#f5c6cb; border:2px solid #721c24;}
.chat-user {background:#667eea;color:white;padding:10px;border-radius:10px;margin:5px 0;}
.chat-bot {background:#f8f9fa;padding:10px;border-radius:10px;margin:5px 0;border:1px solid #ddd;}
.install-warning {padding:15px;border-radius:10px;background:#fff3cd;border-left:4px solid #ffc107;}
</style>
""", unsafe_allow_html=True)


# ------------------------- DATA -------------------------------
DATA_DIR = "studywise_data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
os.makedirs(DATA_DIR, exist_ok=True)

SALT = "StudyWise_Local_Salt_2026"

SCHEMAS = {
    "subjects": ["subject", "units", "difficulty", "confidence", "exam_date", "completed_units"],
    "sessions": ["date", "subject", "topic", "duration_min", "technique", "mood",
                 "distractions", "productivity", "quiz_score", "user"],
    "quiz_results": ["date", "subject", "topic", "score", "questions", "attempt_id", "user"],
    "previous_semester": ["subject", "semester", "marks", "grade", "year", "user"],
    "mid_marks": ["subject", "mid_term", "marks", "date_taken", "semester", "user"],
    "activity_feed": ["timestamp", "activity_type", "description", "details", "user"],
    "stress_logs": ["timestamp", "stress_level", "user", "recommendation"],
}


def empty_df(name):
    return pd.DataFrame(columns=SCHEMAS[name])


def hash_password(password):
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
    users = load_users()
    if not username:
        return False, "Username cannot be empty."
    if username in users:
        return False, "Username already exists."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    users[username] = hash_password(password)
    if save_users(users):
        return True, "Account created successfully."
    return False, "Could not create account."


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

        date_cols = ["date", "exam_date", "date_taken", "timestamp"]
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
                path = os.path.join(DATA_DIR, f"{name}.csv")
                st.session_state[name].to_csv(path, index=False)
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False


# --------------------- Session State --------------------------
def init_state():
    for name in SCHEMAS:
        if name not in st.session_state:
            st.session_state[name] = load_df(name)

    defaults = {
        "logged_in": False,
        "username": "",
        "page": "🏠 Dashboard",
        "study_running": False,
        "study_end": None,
        "study_start": None,
        "study_duration": 45,
        "current_subject": "",
        "current_topic": "",
        "quiz_questions": [],
        "quiz_answers": {},
        "quiz_submitted": False,
        "quiz_subject": "",
        "quiz_topic": "",
        "current_attempt_id": None,
        "stress_level": 0,
        "stress_recommendation": "",
        "daily_streak": 0,
        "last_activity_date": None,
        "chat_history": [],
        "bot_model": None,
        "bot_available": False,
        "gemini_api_key": "",
        "quiz_question_pool": {},
        "used_quiz_questions": {},
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


# ------------------------- Constants --------------------------
DIFFICULTY = {"Easy": 1, "Medium": 2, "Hard": 3, "Very Hard": 4}

TECHNIQUES = [
    "Pomodoro",
    "Active Recall",
    "Practice Problems",
    "Mind Mapping",
    "Feynman Technique",
    "Spaced Repetition",
]

TOPIC_ALIASES = {
    "Python": ["Functions", "Lists & Dictionaries", "Exception Handling", "OOP", "File Handling"],
    "C++": ["Classes & Objects", "Constructors", "Inheritance", "Polymorphism", "Templates"],
    "Data Structures": ["Stacks & Queues", "Trees", "Searching", "Sorting", "Graphs"],
    "DBMS": ["Normalization", "SQL", "Transactions", "Keys", "Constraints"],
    "Mathematics": ["Calculus", "Matrices", "Differentiation", "Integration", "Probability"],
    "AI/ML": ["Supervised Learning", "Regression", "Classification", "Clustering", "Neural Networks"],
}

QUESTION_BANK = {
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


# ------------------------- Helpers ----------------------------
def update_streak():
    today = date.today()
    last = st.session_state.last_activity_date

    if isinstance(last, str):
        try:
            last = datetime.strptime(last, "%Y-%m-%d").date()
        except Exception:
            last = None

    if last is None:
        st.session_state.daily_streak = 1
        st.session_state.last_activity_date = today
    elif last == today:
        return
    elif last == today - timedelta(days=1):
        st.session_state.daily_streak += 1
        st.session_state.last_activity_date = today
    else:
        st.session_state.daily_streak = 1
        st.session_state.last_activity_date = today


def add_to_feed(activity_type, description, details=""):
    try:
        entry = pd.DataFrame([{
            "timestamp": pd.Timestamp.now(),
            "activity_type": activity_type,
            "description": description,
            "details": details,
            "user": st.session_state.username,
        }])
        st.session_state.activity_feed = pd.concat(
            [st.session_state.activity_feed, entry], ignore_index=True
        )
        update_streak()
        save_all()
    except Exception:
        pass


def get_topic_for_subject(subject):
    subject = str(subject)
    for key, topics in TOPIC_ALIASES.items():
        if key.lower() in subject.lower():
            return random.choice(topics)
    return f"{subject} Revision"


def get_grade(marks):
    try:
        marks = float(marks)
    except Exception:
        return "F"

    if marks >= 90: return "A+"
    if marks >= 80: return "A"
    if marks >= 70: return "B+"
    if marks >= 60: return "B"
    if marks >= 50: return "C+"
    if marks >= 40: return "C"
    if marks >= 33: return "D"
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
        remaining = max(units - completed, 0)

        urgency = min(30 / days_left, 30)
        confidence_gap = 6 - confidence
        syllabus = remaining / units * 5

        return round(
            urgency * 2 + difficulty * 2 +
            confidence_gap * 1.5 + syllabus, 2
        )
    except Exception:
        return 0


def priority_label(score):
    if score >= 35:
        return "🔥 Very High"
    if score >= 25:
        return "🔴 High"
    if score >= 15:
        return "🟠 Medium"
    return "🟢 Low"


def generate_attempt_id(subject, topic):
    raw = f"{subject}_{topic}_{datetime.now().isoformat()}_{random.random()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def get_performance_metrics():
    prev = st.session_state.previous_semester
    mid = st.session_state.mid_marks

    avg_prev = float(prev["marks"].mean()) if not prev.empty else 0
    avg_mid = float(mid["marks"].mean()) if not mid.empty else 0

    cgpa = 0
    if not prev.empty:
        points = {"A+": 10, "A": 9, "B+": 8, "B": 7, "C+": 6, "C": 5, "D": 4, "F": 0}
        grades = [get_grade(x) for x in prev["marks"]]
        cgpa = round(sum(points.get(g, 0) for g in grades) / len(grades), 2)

    return {
        "avg_prev_marks": avg_prev,
        "avg_mid_marks": avg_mid,
        "total_subjects": len(prev),
        "cgpa": cgpa,
    }


def get_recommendation():
    df = st.session_state.subjects.copy()
    if df.empty:
        return None

    df["priority"] = df.apply(calculate_priority, axis=1)
    return df.sort_values("priority", ascending=False).iloc[0]


# ---------------------- Timer ---------------------------------
def start_timer(minutes):
    minutes = max(1, int(minutes))
    now = time.time()

    st.session_state.study_duration = minutes
    st.session_state.study_start = now
    st.session_state.study_end = now + minutes * 60
    st.session_state.study_running = True


def stop_timer():
    st.session_state.study_running = False
    st.session_state.study_end = None
    st.session_state.study_start = None


def timer_html(end_timestamp):
    return f"""
    <div class="timer-box">
        <div style="font-size:20px;">📚 Study Session</div>
        <div id="study-timer" class="timer-number">00:00</div>
        <div id="timer-status">Stay focused 💪</div>
    </div>

    <script>
    const endTime = {end_timestamp} * 1000;

    function updateTimer() {{
        const now = Date.now();
        let remaining = Math.max(0, Math.floor((endTime - now) / 1000));

        const mins = Math.floor(remaining / 60);
        const secs = remaining % 60;

        document.getElementById("study-timer").textContent =
            String(mins).padStart(2, "0") + ":" +
            String(secs).padStart(2, "0");

        if (remaining <= 0) {{
            document.getElementById("study-timer").textContent = "00:00";
            document.getElementById("timer-status").textContent =
                "🎉 Session complete! Take a break.";
        }}
    }}

    updateTimer();
    setInterval(updateTimer, 1000);
    </script>
    """


# ---------------------- Quiz ---------------------------------
def get_questions(subject):
    matched = None

    for key in QUESTION_BANK:
        if key.lower() in subject.lower() or subject.lower() in key.lower():
            matched = key
            break

    pool = QUESTION_BANK.get(matched, GENERIC_QUESTIONS).copy()
    random.shuffle(pool)
    return pool[:min(5, len(pool))]


# ---------------------- Stress --------------------------------
def stress_info(level):
    if level < 0.30:
        return (
            "Low Stress 😊",
            "stress-low",
            "You're doing well. Continue studying and take short breaks.",
            ["Continue studying", "Take a 5-minute break", "Stay hydrated"],
        )
    if level < 0.50:
        return (
            "Moderate Stress 😐",
            "stress-medium",
            "Try deep breathing or a short walk before continuing.",
            ["Deep breathing", "10-minute walk", "Calm music"],
        )
    if level < 0.70:
        return (
            "High Stress 😰",
            "stress-high",
            "Take a longer break and use a relaxation technique.",
            ["15-minute break", "Stretching", "Meditation", "Drink water"],
        )
    return (
        "Very High Stress 😫",
        "stress-very-high",
        "Pause studying and give yourself time to relax.",
        ["30-minute break", "Walk", "Deep breathing", "Calming music"],
    )


def detect_stress_from_face(image):
    # This is only a demo heuristic, not a medical/psychological diagnosis.
    if CV2_AVAILABLE and np is not None:
        try:
            img = np.array(image)
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img
            variance = float(np.var(gray))
            score = 0.3 + 0.7 * min(variance / 1000, 1.0)
            return max(0.0, min(1.0, score))
        except Exception:
            pass
    return random.uniform(0.2, 0.8)


# ---------------------- Gemini --------------------------------
def setup_gemini(api_key):
    if not GEMINI_AVAILABLE:
        return None, "Install google-generativeai first."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model, "Connected"
    except Exception as e:
        return None, str(e)


def get_bot_response(prompt, model):
    if model is None:
        return "AI Assistant is not connected. Add your Gemini API key in the sidebar."

    try:
        context = (
            f"Student username: {st.session_state.username}. "
            f"Current subjects: {', '.join(st.session_state.subjects['subject'].astype(str).tolist()) if not st.session_state.subjects.empty else 'None'}."
        )

        full_prompt = f"""
You are StudyWise, an educational AI study assistant.
{context}

Student question:
{prompt}

Give a clear, concise, student-friendly answer.
Explain concepts step by step when needed.
"""
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Sorry, I could not generate a response: {e}"


# ============================================================
# LOGIN
# ============================================================
def show_login():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-title">StudyWise 🧠</h1>', unsafe_allow_html=True)
    st.markdown("### Smart Semester Study Planner")

    tab_login, tab_signup = st.tabs(["🔐 Login", "📝 Create Account"])

    with tab_login:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", type="primary", use_container_width=True):
            if verify_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.page = "🏠 Dashboard"
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab_signup:
        new_user = st.text_input("New username", key="signup_username")
        new_pass = st.text_input("New password", type="password", key="signup_password")
        confirm = st.text_input("Confirm password", type="password", key="signup_confirm")

        if st.button("Create Account", use_container_width=True):
            if new_pass != confirm:
                st.error("Passwords do not match.")
            else:
                ok, msg = create_user(new_user, new_pass)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.caption("Default local account: admin / admin123")
    st.markdown("</div>", unsafe_allow_html=True)


if not st.session_state.logged_in:
    show_login()
    st.stop()


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown("## 🧠 StudyWise")
st.sidebar.caption(f"Logged in as **{st.session_state.username}**")

pages = [
    "🏠 Dashboard",
    "📚 Subjects",
    "⏱️ Study Timer",
    "📝 Quiz",
    "📊 Performance",
    "🧘 Stress Check",
    "🤖 AI Assistant",
    "📈 Analytics",
]

st.session_state.page = st.sidebar.radio(
    "Navigation",
    pages,
    index=pages.index(st.session_state.page) if st.session_state.page in pages else 0,
)

st.sidebar.markdown("---")

# User-configurable timer
st.sidebar.markdown("### ⏱️ Quick Timer")
quick_minutes = st.sidebar.number_input(
    "Set study time (minutes)",
    min_value=1,
    max_value=240,
    value=int(st.session_state.study_duration),
    step=1,
)

st.session_state.study_duration = int(quick_minutes)

if st.sidebar.button("▶ Start Timer", use_container_width=True):
    start_timer(quick_minutes)
    st.session_state.page = "⏱️ Study Timer"
    st.rerun()

if st.sidebar.button("⏹ Stop Timer", use_container_width=True):
    stop_timer()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.metric("🔥 Daily Streak", f"{st.session_state.daily_streak} day(s)")

if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()


# ============================================================
# DASHBOARD
# ============================================================
if st.session_state.page == "🏠 Dashboard":
    st.markdown('<h1 class="main-title">StudyWise 🧠</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Your smart semester study planner, timer, quiz and performance tracker.</div>',
        unsafe_allow_html=True,
    )

    subjects = st.session_state.subjects
    sessions = st.session_state.sessions
    quizzes = st.session_state.quiz_results

    today = pd.Timestamp.today().normalize()
    today_sessions = sessions[
        pd.to_datetime(sessions["date"], errors="coerce").dt.normalize() == today
    ] if not sessions.empty else pd.DataFrame()

    study_minutes = float(today_sessions["duration_min"].sum()) if not today_sessions.empty else 0
    quiz_avg = float(quizzes["score"].mean()) if not quizzes.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📚 Subjects", len(subjects))
    c2.metric("⏱️ Today's Study", f"{study_minutes:.0f} min")
    c3.metric("📝 Quiz Average", f"{quiz_avg:.0f}%")
    c4.metric("🔥 Streak", f"{st.session_state.daily_streak} day(s)")

    st.markdown("### 🎯 Today's Smart Recommendation")

    recommendation = get_recommendation()
    if recommendation is None:
        st.info("Add your subjects to get a personalized recommendation.")
    else:
        score = float(recommendation["priority"])
        st.success(
            f"**Study:** {recommendation['subject']}  |  "
            f"Priority: {priority_label(score)}"
        )
        st.write(
            f"Exam: {pd.to_datetime(recommendation['exam_date']).date()}  •  "
            f"Confidence: {recommendation['confidence']}/5  •  "
            f"Remaining units: {recommendation['units'] - recommendation['completed_units']}"
        )

    if st.session_state.study_running and st.session_state.study_end:
        st.markdown("### 🔴 Active Study Session")
        st.components.v1.html(
            timer_html(st.session_state.study_end),
            height=190,
        )

    st.markdown("### ⚡ Quick Actions")
    q1, q2, q3 = st.columns(3)

    with q1:
        if st.button("📚 Add Subject", use_container_width=True):
            st.session_state.page = "📚 Subjects"
            st.rerun()

    with q2:
        if st.button("⏱️ Open Timer", use_container_width=True):
            st.session_state.page = "⏱️ Study Timer"
            st.rerun()

    with q3:
        if st.button("📝 Take Quiz", use_container_width=True):
            st.session_state.page = "📝 Quiz"
            st.rerun()


# ============================================================
# SUBJECTS
# ============================================================
elif st.session_state.page == "📚 Subjects":
    st.title("📚 Subjects")

    with st.form("subject_form"):
        c1, c2 = st.columns(2)

        with c1:
            subject = st.text_input("Subject name")
            units = st.number_input("Total units", min_value=1, max_value=100, value=5)
            completed = st.number_input("Completed units", min_value=0, max_value=100, value=0)

        with c2:
            difficulty = st.selectbox("Difficulty", list(DIFFICULTY.keys()), index=1)
            confidence = st.slider("Confidence (1 = low, 5 = high)", 1, 5, 3)
            exam_date = st.date_input("Exam date", value=date.today() + timedelta(days=14))

        submitted = st.form_submit_button("➕ Add Subject", type="primary")

    if submitted:
        if not subject.strip():
            st.error("Enter a subject name.")
        elif completed > units:
            st.error("Completed units cannot be greater than total units.")
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
                [st.session_state.subjects, new_row], ignore_index=True
            )
            save_all()
            add_to_feed("Subject Added", subject.strip(), f"{units} units")
            st.success("Subject added successfully.")

    if st.session_state.subjects.empty:
        st.info("No subjects added yet.")
    else:
        df = st.session_state.subjects.copy()
        df["priority_score"] = df.apply(calculate_priority, axis=1)
        df["priority"] = df["priority_score"].apply(priority_label)

        st.dataframe(
            df[[
                "subject", "units", "completed_units", "difficulty",
                "confidence", "exam_date", "priority"
            ]],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### 🗑️ Remove Subject")
        selected = st.selectbox("Select subject to remove", df["subject"].astype(str).tolist())

        if st.button("Delete Selected Subject"):
            st.session_state.subjects = st.session_state.subjects[
                st.session_state.subjects["subject"].astype(str) != selected
            ].reset_index(drop=True)
            save_all()
            st.success(f"{selected} removed.")
            st.rerun()


# ============================================================
# STUDY TIMER
# ============================================================
elif st.session_state.page == "⏱️ Study Timer":
    st.title("⏱️ Study Timer")
    st.write("Set your own study duration — the timer is no longer fixed to a default value.")

    c1, c2, c3 = st.columns(3)

    with c1:
        minutes = st.number_input(
            "Study duration (minutes)",
            min_value=1,
            max_value=240,
            value=int(st.session_state.study_duration),
            step=1,
        )
        st.session_state.study_duration = int(minutes)

    with c2:
        selected_subject = st.text_input(
            "Subject",
            value=st.session_state.current_subject,
        )

    with c3:
        selected_topic = st.text_input(
            "Topic",
            value=st.session_state.current_topic,
        )

    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("▶ Start Study", type="primary", use_container_width=True):
            st.session_state.current_subject = selected_subject
            st.session_state.current_topic = selected_topic
            start_timer(minutes)
            add_to_feed(
                "Study Started",
                selected_subject or "General Study",
                f"{minutes} minutes",
            )
            st.rerun()

    with b2:
        if st.button("⏹ Stop", use_container_width=True):
            if st.session_state.study_running and st.session_state.study_start:
                elapsed = max(0, time.time() - st.session_state.study_start)
                duration = min(elapsed / 60, float(st.session_state.study_duration))

                if duration >= 1:
                    new_session = pd.DataFrame([{
                        "date": pd.Timestamp.now(),
                        "subject": selected_subject or "General Study",
                        "topic": selected_topic or "General",
                        "duration_min": round(duration, 1),
                        "technique": "Custom Timer",
                        "mood": "Good",
                        "distractions": 0,
                        "productivity": 5,
                        "quiz_score": 0,
                        "user": st.session_state.username,
                    }])
                    st.session_state.sessions = pd.concat(
                        [st.session_state.sessions, new_session],
                        ignore_index=True,
                    )
                    save_all()

            stop_timer()
            st.rerun()

    with b3:
        if st.button("🔄 Reset", use_container_width=True):
            stop_timer()
            st.session_state.study_duration = 45
            st.rerun()

    if st.session_state.study_running and st.session_state.study_end:
        st.components.v1.html(
            timer_html(st.session_state.study_end),
            height=210,
        )
        st.info("Keep this page open while studying. The countdown runs in your browser.")
    else:
        total_seconds = int(st.session_state.study_duration) * 60
        st.markdown(
            f"""
            <div class="timer-box">
                <div style="font-size:20px;">Ready to Study 📚</div>
                <div class="timer-number">{total_seconds // 60:02d}:00</div>
                <div>Set the duration above and press Start Study.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 💡 Study Techniques")
    st.write(" • Pomodoro  • Active Recall  • Practice Problems  • Feynman Technique  • Spaced Repetition")


# ============================================================
# QUIZ
# ============================================================
elif st.session_state.page == "📝 Quiz":
    st.title("📝 Study Quiz")

    subjects = (
        st.session_state.subjects["subject"].astype(str).tolist()
        if not st.session_state.subjects.empty
        else ["Python", "C++", "Data Structures", "DBMS", "Mathematics", "AI/ML"]
    )

    subject = st.selectbox("Choose subject", subjects)
    topic = st.text_input("Topic", value=get_topic_for_subject(subject))

    if st.button("🎯 Generate Quiz", type="primary"):
        st.session_state.quiz_questions = get_questions(subject)
        st.session_state.quiz_answers = {}
        st.session_state.quiz_submitted = False
        st.session_state.quiz_subject = subject
        st.session_state.quiz_topic = topic
        st.session_state.current_attempt_id = generate_attempt_id(subject, topic)
        st.rerun()

    if st.session_state.quiz_questions:
        st.markdown("---")
        st.subheader(f"Quiz: {st.session_state.quiz_subject}")

        with st.form("quiz_form"):
            answers = {}

            for i, (question, options, _) in enumerate(st.session_state.quiz_questions):
                answers[i] = st.radio(
                    f"{i + 1}. {question}",
                    options,
                    key=f"quiz_{st.session_state.current_attempt_id}_{i}",
                )

            submitted = st.form_submit_button("Submit Quiz", type="primary")

        if submitted:
            correct = 0

            for i, (_, options, correct_index) in enumerate(st.session_state.quiz_questions):
                if answers.get(i) == options[correct_index]:
                    correct += 1

            total = len(st.session_state.quiz_questions)
            score = round(correct / total * 100, 1)

            result = pd.DataFrame([{
                "date": pd.Timestamp.now(),
                "subject": st.session_state.quiz_subject,
                "topic": st.session_state.quiz_topic,
                "score": score,
                "questions": total,
                "attempt_id": st.session_state.current_attempt_id,
                "user": st.session_state.username,
            }])

            st.session_state.quiz_results = pd.concat(
                [st.session_state.quiz_results, result],
                ignore_index=True,
            )
            save_all()
            add_to_feed("Quiz Completed", st.session_state.quiz_subject, f"Score: {score}%")

            st.session_state.quiz_submitted = True
            st.session_state.last_quiz_score = score

        if st.session_state.quiz_submitted:
            score = st.session_state.get("last_quiz_score", 0)
            if score >= 80:
                st.success(f"🎉 Excellent! You scored {score}%.")
            elif score >= 60:
                st.info(f"👍 Good job! You scored {score}%.")
            else:
                st.warning(f"📖 Keep practicing. You scored {score}%.")


# ============================================================
# PERFORMANCE
# ============================================================
elif st.session_state.page == "📊 Performance":
    st.title("📊 Performance Tracker")

    tab1, tab2 = st.tabs(["Previous Semester", "Mid Marks"])

    with tab1:
        with st.form("previous_sem_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                subject = st.text_input("Subject", key="prev_subject")
            with c2:
                marks = st.number_input("Marks", min_value=0.0, max_value=100.0, value=0.0, key="prev_marks")
            with c3:
                semester = st.text_input("Semester", value="Previous", key="prev_sem")

            if st.form_submit_button("Add Marks"):
                if subject.strip():
                    row = pd.DataFrame([{
                        "subject": subject.strip(),
                        "semester": semester,
                        "marks": marks,
                        "grade": get_grade(marks),
                        "year": date.today().year,
                        "user": st.session_state.username,
                    }])
                    st.session_state.previous_semester = pd.concat(
                        [st.session_state.previous_semester, row],
                        ignore_index=True,
                    )
                    save_all()
                    st.success("Marks added.")

        if not st.session_state.previous_semester.empty:
            st.dataframe(st.session_state.previous_semester, use_container_width=True, hide_index=True)

    with tab2:
        with st.form("mid_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                subject = st.text_input("Subject", key="mid_subject")
            with c2:
                marks = st.number_input("Marks", min_value=0.0, max_value=100.0, value=0.0, key="mid_marks_input")
            with c3:
                semester = st.text_input("Semester", value="Current", key="mid_sem")

            if st.form_submit_button("Add Mid Mark"):
                if subject.strip():
                    row = pd.DataFrame([{
                        "subject": subject.strip(),
                        "mid_term": "Mid",
                        "marks": marks,
                        "date_taken": pd.Timestamp.now(),
                        "semester": semester,
                        "user": st.session_state.username,
                    }])
                    st.session_state.mid_marks = pd.concat(
                        [st.session_state.mid_marks, row],
                        ignore_index=True,
                    )
                    save_all()
                    st.success("Mid mark added.")

        if not st.session_state.mid_marks.empty:
            st.dataframe(st.session_state.mid_marks, use_container_width=True, hide_index=True)

    metrics = get_performance_metrics()

    st.markdown("### 📌 Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Previous Avg", f"{metrics['avg_prev_marks']:.1f}%")
    c2.metric("Mid Avg", f"{metrics['avg_mid_marks']:.1f}%")
    c3.metric("Subjects", metrics["total_subjects"])
    c4.metric("Estimated CGPA", metrics["cgpa"])


# ============================================================
# STRESS CHECK
# ============================================================
elif st.session_state.page == "🧘 Stress Check":
    st.title("🧘 Stress Check")
    st.caption("This is a self-check tool for study planning, not a medical diagnosis.")

    tab1, tab2 = st.tabs(["Self Assessment", "Stress History"])

    with tab1:
        level = st.slider("How stressed do you feel right now?", 0, 100, 40)
        st.progress(level / 100)

        if st.button("💾 Save Stress Level", type="primary"):
            score = level / 100
            label, css, recommendation, activities = stress_info(score)

            st.session_state.stress_level = score
            st.session_state.stress_recommendation = recommendation

            row = pd.DataFrame([{
                "timestamp": pd.Timestamp.now(),
                "stress_level": score,
                "user": st.session_state.username,
                "recommendation": recommendation,
            }])

            st.session_state.stress_logs = pd.concat(
                [st.session_state.stress_logs, row],
                ignore_index=True,
            )
            save_all()
            add_to_feed("Stress Check", label, f"Score: {level}%")

            st.markdown(
                f"""
                <div class="stress-meter {css}">
                    <h3>{label}</h3>
                    <p>Score: {level}%</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.info(recommendation)
            st.write("**Suggested:** " + " • ".join(activities))

        if CV2_AVAILABLE:
            st.markdown("---")
            st.subheader("📸 Optional Camera Demo")
            camera = st.camera_input("Capture an image")

            if camera:
                from PIL import Image
                image = Image.open(camera)
                score = detect_stress_from_face(image)
                label, css, recommendation, _ = stress_info(score)

                c1, c2 = st.columns(2)
                with c1:
                    st.image(image, caption="Captured image", use_container_width=True)
                with c2:
                    st.markdown(
                        f"""
                        <div class="stress-meter {css}">
                            <h3>{label}</h3>
                            <p>Demo score: {score * 100:.0f}%</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.caption("Camera result is only a demo heuristic and should not be treated as a real stress diagnosis.")

    with tab2:
        logs = st.session_state.stress_logs
        logs = logs[logs["user"].astype(str) == str(st.session_state.username)] if not logs.empty else logs

        if logs.empty:
            st.info("No stress records yet.")
        else:
            st.dataframe(logs.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)
            fig = px.line(
                logs.sort_values("timestamp"),
                x="timestamp",
                y="stress_level",
                title="Stress Level Trend",
            )
            fig.update_layout(yaxis_range=[0, 1])
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# AI ASSISTANT
# ============================================================
elif st.session_state.page == "🤖 AI Assistant":
    st.title("🤖 StudyWise AI Assistant")

    st.info("Add a Gemini API key in the sidebar to enable AI answers.")

    api_key = st.sidebar.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state.gemini_api_key,
    )

    if api_key:
        st.session_state.gemini_api_key = api_key

        if st.sidebar.button("🔌 Connect AI"):
            model, message = setup_gemini(api_key)
            st.session_state.bot_model = model
            st.session_state.bot_available = model is not None

            if model is not None:
                st.sidebar.success(message)
            else:
                st.sidebar.error(message)

    if not GEMINI_AVAILABLE:
        st.warning("Optional package missing. Install with: pip install google-generativeai")
    else:
        for role, message in st.session_state.chat_history:
            css = "chat-user" if role == "user" else "chat-bot"
            st.markdown(
                f'<div class="{css}">{message}</div>',
                unsafe_allow_html=True,
            )

        prompt = st.chat_input("Ask StudyWise a study question...")

        if prompt:
            st.session_state.chat_history.append(("user", prompt))

            answer = get_bot_response(
                prompt,
                st.session_state.bot_model,
            )

            st.session_state.chat_history.append(("assistant", answer))
            st.rerun()


# ============================================================
# ANALYTICS
# ============================================================
elif st.session_state.page == "📈 Analytics":
    st.title("📈 Study Analytics")

    sessions = st.session_state.sessions.copy()
    quizzes = st.session_state.quiz_results.copy()

    if sessions.empty and quizzes.empty:
        st.info("Start studying or taking quizzes to see analytics.")
    else:
        if not sessions.empty:
            sessions["date"] = pd.to_datetime(sessions["date"], errors="coerce")
            daily = sessions.groupby(sessions["date"].dt.date)["duration_min"].sum().reset_index()
            daily.columns = ["date", "minutes"]

            st.subheader("⏱️ Study Time")
            fig = px.bar(daily, x="date", y="minutes", title="Daily Study Minutes")
            st.plotly_chart(fig, use_container_width=True)

            subject_time = sessions.groupby("subject")["duration_min"].sum().reset_index()
            fig2 = px.pie(
                subject_time,
                names="subject",
                values="duration_min",
                title="Study Time by Subject",
            )
            st.plotly_chart(fig2, use_container_width=True)

        if not quizzes.empty:
            quizzes["date"] = pd.to_datetime(quizzes["date"], errors="coerce")

            st.subheader("📝 Quiz Performance")
            fig3 = px.line(
                quizzes.sort_values("date"),
                x="date",
                y="score",
                color="subject",
                markers=True,
                title="Quiz Score Trend",
            )
            fig3.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig3, use_container_width=True)

            st.metric("Overall Quiz Average", f"{quizzes['score'].mean():.1f}%")


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption("StudyWise 🧠 | Smart study planning made simple")
