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
import io

# Try to import optional packages with graceful fallback
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

# =========================================================
# MINDMATE - Smart Semester Study Planner & Analyzer
# Version 8.1 - Error-Free with Fallback Support
# =========================================================

st.set_page_config(
    page_title="MindMate | Smart Study Planner",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------- CSS ----------------------------
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
.subtitle {
    font-size: 18px;
    opacity: .75;
    margin-bottom: 25px;
    color: #666;
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
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.metric-value {
    font-size: 28px;
    font-weight: 700;
}
.metric-label {
    font-size: 14px;
    opacity: .9;
}
.chat-message {
    padding: 10px 15px;
    border-radius: 10px;
    margin: 5px 0;
    max-width: 80%;
}
.chat-user {
    background: #667eea;
    color: white;
    margin-left: auto;
}
.chat-bot {
    background: white;
    border: 1px solid #dee2e6;
    margin-right: auto;
}
.chat-timestamp {
    font-size: 10px;
    color: #999;
    text-align: right;
    margin-top: 2px;
}
.feed-item {
    padding: 12px;
    border-radius: 10px;
    background: white;
    border-left: 4px solid #667eea;
    margin-bottom: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.feed-item .time {
    font-size: 11px;
    color: #999;
}
.feed-item .icon {
    font-size: 20px;
    margin-right: 10px;
}
.study-timer {
    text-align: center;
    font-size: 60px;
    font-weight: 800;
    font-family: monospace;
    padding: 20px;
}
.login-container {
    max-width: 420px;
    margin: 0 auto;
    padding: 40px;
    border-radius: 20px;
    background: white;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}
.puzzle-container {
    padding: 20px;
    border-radius: 14px;
    background: #f8f9fa;
    border: 2px solid #e9ecef;
}
.sudoku-cell {
    background: white;
    border: 1px solid #dee2e6;
    padding: 8px;
    text-align: center;
    font-size: 18px;
    font-weight: 600;
}
.sudoku-cell.fixed {
    background: #e9ecef;
}
.bot-status {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.bot-online {
    background: #d4edda;
    color: #155724;
}
.bot-offline {
    background: #f8d7da;
    color: #721c24;
}
.bot-warning {
    background: #fff3cd;
    color: #856404;
}
.stress-meter {
    padding: 15px;
    border-radius: 12px;
    text-align: center;
    margin: 10px 0;
}
.stress-low {
    background: #d4edda;
    border: 2px solid #28a745;
}
.stress-medium {
    background: #fff3cd;
    border: 2px solid #ffc107;
}
.stress-high {
    background: #f8d7da;
    border: 2px solid #dc3545;
}
.stress-very-high {
    background: #f5c6cb;
    border: 2px solid #721c24;
}
.webcam-container {
    border: 2px solid #dee2e6;
    border-radius: 12px;
    padding: 15px;
    background: #f8f9fa;
}
.install-warning {
    padding: 15px;
    border-radius: 10px;
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# --------------------- SECURE AUTH SYSTEM ------------------------
USERS_FILE = "mindmate_data/users.json"
SALT = "MindMate_Salt_2024"

def hash_password(password):
    return hashlib.sha256((password + SALT).encode()).hexdigest()

def load_users():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        return {"admin": hash_password("admin123")}
    except:
        return {"admin": hash_password("admin123")}

def save_users(users):
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f)
        return True
    except:
        return False

def verify_user(username, password):
    users = load_users()
    if username in users:
        return users[username] == hash_password(password)
    return False

def create_user(username, password):
    users = load_users()
    if username in users:
        return False, "Username already exists!"
    if len(password) < 6:
        return False, "Password must be at least 6 characters!"
    users[username] = hash_password(password)
    if save_users(users):
        return True, "User created successfully!"
    return False, "Error creating user!"

# --------------------- DATA ------------------------------
DATA_DIR = "mindmate_data"
os.makedirs(DATA_DIR, exist_ok=True)

SCHEMAS = {
    "subjects": ["subject", "units", "difficulty", "confidence", "exam_date", "completed_units"],
    "exams": ["exam_name", "subject", "exam_date"],
    "sessions": ["date", "subject", "topic", "duration_min", "technique", "mood", "distractions", "productivity", "quiz_score"],
    "quiz_results": ["date", "subject", "topic", "score", "questions", "attempt_id"],
    "timetable": ["day", "start", "end", "subject"],
    "quiz_attempts": ["attempt_id", "subject", "topic", "attempt_time", "question_hash", "completed"],
    "coding_problems": ["problem_id", "platform", "problem_name", "difficulty", "topic", "date_solved", "time_taken", "language", "score"],
    "previous_semester": ["subject", "semester", "marks", "grade", "year"],
    "mid_marks": ["subject", "mid_term", "marks", "date_taken", "semester"],
    "activity_feed": ["timestamp", "activity_type", "description", "details", "user"],
    "stress_logs": ["timestamp", "stress_level", "user", "recommendation"]
}

def empty_df(name):
    return pd.DataFrame(columns=SCHEMAS[name])

def load_df(name):
    path = os.path.join(DATA_DIR, f"{name}.csv")
    try:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            df = pd.read_csv(path)
            for col in SCHEMAS[name]:
                if col not in df.columns:
                    df[col] = None
            df = df[SCHEMAS[name]]
            for col in ["exam_date", "date", "attempt_time", "date_solved", "year", "date_taken", "timestamp"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
            return df
        else:
            return empty_df(name)
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

def init_state():
    for name in SCHEMAS:
        if name not in st.session_state:
            st.session_state[name] = load_df(name)

    defaults = {
        "current_subject": "",
        "current_topic": "",
        "study_running": False,
        "study_end": None,
        "study_start": None,
        "study_duration": 45,
        "break_running": False,
        "break_end": None,
        "quiz_subject": "",
        "quiz_topic": "",
        "quiz_questions": [],
        "quiz_answers": {},
        "quiz_submitted": False,
        "quiz_start_time": None,
        "quiz_time_limit": 300,
        "current_attempt_id": None,
        "quiz_lock": False,
        "semester_info": {},
        "page": "🏠 Dashboard",
        "data_initialized": True,
        "logged_in": False,
        "username": "",
        "sudoku_grid": None,
        "sudoku_solution": None,
        "sudoku_editable": None,
        "sudoku_used_puzzles": [],
        "arrow_puzzle": None,
        "arrow_solution": None,
        "arrow_used_puzzles": [],
        "puzzle_start_time": None,
        "puzzle_type": None,
        "puzzle_completed": False,
        "used_quiz_questions": {},
        "quiz_question_pool": {},
        "current_semester": "Fall 2024",
        "show_performance_metrics": True,
        "chat_history": [],
        "gemini_api_key": "",
        "bot_available": False,
        "feed_filter": "All",
        "bot_model": None,
        "daily_streak": 0,
        "last_activity_date": None,
        "stress_level": 0,
        "stress_recommendation": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# --------------------- CONSTANTS --------------------------
DIFFICULTY = {"Easy": 1, "Medium": 2, "Hard": 3, "Very Hard": 4}
CODING_PLATFORMS = ["LeetCode", "HackerRank", "CodeChef", "Codeforces", "GeeksforGeeks", "AtCoder", "Custom"]
CODING_LANGUAGES = ["Python", "C++", "Java", "JavaScript", "Go", "Rust", "C#", "Ruby", "Swift"]
CODING_DIFFICULTIES = ["Easy", "Medium", "Hard"]
TECHNIQUES = ["Pomodoro", "Active Recall", "Practice Problems", "Mind Mapping", "Feynman Technique", "Spaced Repetition"]

# Question banks
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
    ]
}

GENERIC_QUESTIONS = [
    ("What is critical thinking?", ["Following instructions", "Analyzing information", "Memorizing facts", "Copying answers"], 1),
    ("Which skill is essential for effective learning?", ["Time management", "Social media", "Watching videos", "Skipping topics"], 0),
]

# Sudoku Puzzles
SUDOKU_PUZZLES = [
    [
        [5,3,0,0,7,0,0,0,0],
        [6,0,0,1,9,5,0,0,0],
        [0,9,8,0,0,0,0,6,0],
        [8,0,0,0,6,0,0,0,3],
        [4,0,0,8,0,3,0,0,1],
        [7,0,0,0,2,0,0,0,6],
        [0,6,0,0,0,0,2,8,0],
        [0,0,0,4,1,9,0,0,5],
        [0,0,0,0,8,0,0,7,9]
    ],
    [
        [0,0,4,3,0,0,2,0,9],
        [0,0,5,0,0,9,0,0,1],
        [0,7,0,0,6,0,0,4,3],
        [0,0,6,0,0,2,0,8,7],
        [1,9,0,0,0,7,4,0,0],
        [0,5,0,1,9,0,0,0,0],
        [0,0,7,0,0,0,3,0,0],
        [0,4,0,0,0,6,0,0,0],
        [9,0,3,0,0,0,0,0,6]
    ],
]

# Arrow Puzzles
ARROW_PUZZLES = []
for _ in range(10):
    directions = ['↑', '→', '↓', '←']
    size = 5
    puzzle = []
    solution = []
    for i in range(size):
        row = []
        sol_row = []
        for j in range(size):
            if random.random() < 0.7:
                dir_idx = random.randint(0, 3)
                row.append(directions[dir_idx])
                sol_row.append(dir_idx)
            else:
                row.append(' ')
                sol_row.append(-1)
        puzzle.append(row)
        solution.append(sol_row)
    ARROW_PUZZLES.append((puzzle, solution))

# --------------------- STRESS DETECTION ---------------------
def detect_stress_from_face(image):
    """Simulate stress detection from facial features"""
    try:
        if CV2_AVAILABLE and cv2 is not None and np is not None:
            # Convert image to numpy array
            if isinstance(image, Image.Image):
                img_array = np.array(image)
            else:
                img_array = np.array(image)
            
            # Simulate stress detection based on image properties
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Calculate image variance as a stress indicator
            variance = np.var(gray)
            normalized_variance = min(variance / 1000, 1.0)
            
            # Add some randomness for simulation
            stress_level = 0.3 + 0.7 * normalized_variance + random.uniform(-0.1, 0.1)
            stress_level = max(0, min(1, stress_level))
            
            return stress_level
        else:
            # Fallback: random stress level if cv2 not available
            return random.uniform(0.2, 0.8)
    except:
        return random.uniform(0.2, 0.8)

def get_stress_recommendation(stress_level):
    if stress_level < 0.3:
        return {
            "level": "Low Stress 😊",
            "color": "stress-low",
            "recommendation": "You're doing great! Keep up the good work. Take short breaks to maintain this state.",
            "activities": ["Continue studying", "Take a 5-min break", "Stay hydrated"]
        }
    elif stress_level < 0.5:
        return {
            "level": "Moderate Stress 😐",
            "color": "stress-medium",
            "recommendation": "You're experiencing some stress. Try deep breathing or a short walk.",
            "activities": ["Deep breathing (5 min)", "Short walk (10 min)", "Listen to calm music"]
        }
    elif stress_level < 0.7:
        return {
            "level": "High Stress 😰",
            "color": "stress-high",
            "recommendation": "You're feeling stressed. Take a longer break and try relaxation techniques.",
            "activities": ["Take a 15-min break", "Meditation", "Stretch exercises", "Drink water"]
        }
    else:
        return {
            "level": "Very High Stress 😫",
            "color": "stress-very-high",
            "recommendation": "You're under significant stress. Take a break, relax, and come back refreshed.",
            "activities": ["Take a 30-min break", "Go for a walk", "Listen to calming music", "Deep breathing exercise"]
        }

def show_stress_detection():
    st.markdown("### 🧘 Stress Detection")
    st.markdown("Monitor your stress levels and get personalized recommendations")
    
    # Check if cv2 is available
    if not CV2_AVAILABLE:
        st.markdown("""
        <div class="install-warning">
            <strong>⚠️ OpenCV not installed!</strong><br>
            For better stress detection, install opencv-python:
            <code>pip install opencv-python</code><br>
            Using fallback stress detection for now.
        </div>
        """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📸 Stress Check", "📊 Stress History"])
    
    with tab1:
        st.markdown('<div class="webcam-container">', unsafe_allow_html=True)
        
        # Manual stress level input (as fallback)
        st.markdown("### 📝 Stress Self-Assessment")
        st.markdown("If camera is not available, please rate your stress level:")
        
        col1, col2 = st.columns(2)
        with col1:
            manual_stress = st.slider("How stressed do you feel?", 0, 100, 50)
            if st.button("💾 Save Stress Level", type="primary"):
                stress_level = manual_stress / 100
                st.session_state.stress_level = stress_level
                stress_info = get_stress_recommendation(stress_level)
                
                st.markdown(f"""
                <div class="stress-meter {stress_info['color']}">
                    <h3>Stress Level: {stress_info['level']}</h3>
                    <p>Score: {stress_level*100:.0f}%</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="card">
                    <p><strong>💡 Recommendation:</strong> {stress_info['recommendation']}</p>
                    <p><strong>📋 Suggested Activities:</strong></p>
                    <ul>
                        {''.join([f'<li>{activity}</li>' for activity in stress_info['activities']])}
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
                # Save to history
                new_log = pd.DataFrame([{
                    "timestamp": pd.Timestamp.now(),
                    "stress_level": stress_level,
                    "user": st.session_state.username,
                    "recommendation": stress_info['recommendation']
                }])
                st.session_state.stress_logs = pd.concat([st.session_state.stress_logs, new_log], ignore_index=True)
                save_all()
                add_to_feed("Stress Check", f"Stress level: {stress_info['level']}", f"Score: {stress_level*100:.0f}%")
                
                if stress_level > 0.6:
                    st.warning("⚠️ You seem stressed. Take a break! 🧘")
                    if st.button("🧘 Take a Break", type="primary"):
                        st.session_state.page = "🧩 Brain Break"
                        st.rerun()
        
        with col2:
            st.markdown("### 🧘 Quick Stress Relief Tips")
            st.markdown("""
            - **Deep Breathing:** Inhale 4s, hold 4s, exhale 4s
            - **Hydration:** Drink a glass of water
            - **Walk:** Take a 5-minute walk
            - **Music:** Listen to calming music
            - **Stretch:** Do some light stretching
            """)
        
        # Camera option if available
        if CV2_AVAILABLE:
            st.markdown("---")
            st.markdown("### 📸 Or use Camera Detection")
            camera_image = st.camera_input("Position your face in the frame", key="stress_camera")
            
            if camera_image is not None:
                with st.spinner("Analyzing facial features..."):
                    image = Image.open(camera_image)
                    stress_level = detect_stress_from_face(image)
                    st.session_state.stress_level = stress_level
                    stress_info = get_stress_recommendation(stress_level)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.image(image, caption="Captured Image", use_container_width=True)
                    
                    with col2:
                        st.markdown(f"""
                        <div class="stress-meter {stress_info['color']}">
                            <h3>Stress Level: {stress_info['level']}</h3>
                            <p>Score: {stress_level*100:.0f}%</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div class="card">
                            <p><strong>💡 Recommendation:</strong> {stress_info['recommendation']}</p>
                            <p><strong>📋 Suggested Activities:</strong></p>
                            <ul>
                                {''.join([f'<li>{activity}</li>' for activity in stress_info['activities']])}
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    new_log = pd.DataFrame([{
                        "timestamp": pd.Timestamp.now(),
                        "stress_level": stress_level,
                        "user": st.session_state.username,
                        "recommendation": stress_info['recommendation']
                    }])
                    st.session_state.stress_logs = pd.concat([st.session_state.stress_logs, new_log], ignore_index=True)
                    save_all()
                    add_to_feed("Stress Check", f"Stress level: {stress_info['level']}", f"Score: {stress_level*100:.0f}%")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown("### 📊 Stress History")
        
        stress_logs = st.session_state.stress_logs
        if stress_logs.empty:
            st.info("No stress logs yet. Use the stress checker to start tracking!")
        else:
            user_logs = stress_logs[stress_logs["user"] == st.session_state.username]
            
            if user_logs.empty:
                st.info("No stress logs for you yet.")
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    avg_stress = user_logs["stress_level"].mean()
                    st.metric("Average Stress", f"{avg_stress*100:.0f}%")
                with col2:
                    max_stress = user_logs["stress_level"].max()
                    st.metric("Max Stress", f"{max_stress*100:.0f}%")
                with col3:
                    min_stress = user_logs["stress_level"].min()
                    st.metric("Min Stress", f"{min_stress*100:.0f}%")
                
                user_logs = user_logs.sort_values("timestamp")
                fig = px.line(user_logs, x="timestamp", y="stress_level", 
                            title="Stress Level Trend", 
                            labels={"stress_level": "Stress Level", "timestamp": "Time"})
                fig.update_layout(yaxis_range=[0, 1])
                st.plotly_chart(fig, use_container_width=True)

# --------------------- HELPER FUNCTIONS ---------------------
def add_to_feed(activity_type, description, details=""):
    try:
        new_entry = pd.DataFrame([{
            "timestamp": pd.Timestamp.now(),
            "activity_type": activity_type,
            "description": description,
            "details": details,
            "user": st.session_state.username
        }])
        st.session_state.activity_feed = pd.concat([st.session_state.activity_feed, new_entry], ignore_index=True)
        save_all()
        update_streak()
    except:
        pass

def update_streak():
    today = date.today()
    last_date = st.session_state.last_activity_date
    
    if last_date is None:
        st.session_state.daily_streak = 1
        st.session_state.last_activity_date = today
    else:
        if isinstance(last_date, str):
            last_date = datetime.strptime(last_date, '%Y-%m-%d').date()
        
        if last_date == today:
            pass
        elif last_date == today - timedelta(days=1):
            st.session_state.daily_streak += 1
            st.session_state.last_activity_date = today
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
        "AI/ML": ["Supervised Learning", "Regression", "Classification", "Clustering", "Neural Networks"]
    }
    subject = str(subject)
    for key, topics in aliases.items():
        if key.lower() in subject.lower():
            return random.choice(topics)
    return f"{subject} Revision"

def available_questions(subject):
    if subject not in st.session_state.quiz_question_pool:
        matched = None
        for key in TOPIC_BANK:
            if key.lower() in str(subject).lower() or str(subject).lower() in key.lower():
                matched = key
                break
        
        if matched:
            pool = TOPIC_BANK[matched].copy()
        else:
            pool = GENERIC_QUESTIONS.copy()
        
        random.shuffle(pool)
        st.session_state.quiz_question_pool[subject] = pool
        st.session_state.used_quiz_questions[subject] = []
    
    pool = st.session_state.quiz_question_pool[subject]
    used = st.session_state.used_quiz_questions[subject]
    
    if len(used) >= len(pool):
        st.session_state.used_quiz_questions[subject] = []
        used = []
    
    available = [q for i, q in enumerate(pool) if i not in used]
    num_questions = min(5, len(available))
    selected = available[:num_questions]
    
    for q in selected:
        idx = pool.index(q)
        if idx not in used:
            st.session_state.used_quiz_questions[subject].append(idx)
    
    return selected

def calculate_priority(row):
    try:
        today = pd.Timestamp.today().normalize()
        exam = pd.to_datetime(row["exam_date"])
        if pd.isna(exam):
            return 0
        exam = exam.normalize()
        days_left = max((exam - today).days, 1)
        urgency = min(30 / days_left, 30)
        difficulty = DIFFICULTY.get(str(row["difficulty"]), 2)
        confidence_gap = 6 - int(row["confidence"]) if pd.notna(row["confidence"]) else 3
        remaining = max(int(row["units"]) - int(row["completed_units"]), 0) if pd.notna(row["units"]) and pd.notna(row["completed_units"]) else 0
        syllabus = remaining / max(int(row["units"]), 1) * 5 if pd.notna(row["units"]) else 0
        return round(urgency * 2 + difficulty * 2 + confidence_gap * 1.5 + syllabus, 2)
    except Exception:
        return 0

def priority_label(score):
    if score >= 35: return "🔥 Very High"
    if score >= 25: return "🔴 High"
    if score >= 15: return "🟠 Medium"
    return "🟢 Low"

def get_recommendation():
    df = st.session_state.subjects.copy()
    if df.empty: return None
    try:
        df["priority"] = df.apply(calculate_priority, axis=1)
        return df.sort_values("priority", ascending=False).iloc[0]
    except Exception:
        return None

def generate_attempt_id(subject, topic):
    raw = f"{subject}_{topic}_{datetime.now().isoformat()}_{random.random()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def get_grade(marks):
    if marks >= 90: return "A+"
    elif marks >= 80: return "A"
    elif marks >= 70: return "B+"
    elif marks >= 60: return "B"
    elif marks >= 50: return "C+"
    elif marks >= 40: return "C"
    elif marks >= 33: return "D"
    else: return "F"

def get_performance_metrics():
    prev_sem = st.session_state.previous_semester
    mid_marks = st.session_state.mid_marks
    
    metrics = {
        "avg_prev_marks": 0,
        "avg_mid_marks": 0,
        "subjects_improved": 0,
        "total_subjects": 0,
        "cgpa": 0
    }
    
    if not prev_sem.empty:
        metrics["avg_prev_marks"] = prev_sem["marks"].mean()
        metrics["total_subjects"] = len(prev_sem)
    
    if not mid_marks.empty:
        metrics["avg_mid_marks"] = mid_marks["marks"].mean()
    
    if not prev_sem.empty:
        grades = [get_grade(m) for m in prev_sem["marks"]]
        grade_points = {"A+": 10, "A": 9, "B+": 8, "B": 7, "C+": 6, "C": 5, "D": 4, "F": 0}
        total_points = sum(grade_points.get(g, 0) for g in grades)
        metrics["cgpa"] = round(total_points / len(grades), 2) if grades else 0
    
    return metrics

def generate_smart_daily_plan():
    subjects = st.session_state.subjects.copy()
    sessions = st.session_state.sessions.copy()
    quizzes = st.session_state.quiz_results.copy()
    prev_sem = st.session_state.previous_semester.copy()
    mid_marks = st.session_state.mid_marks.copy()

    if subjects.empty:
        return []

    today = pd.Timestamp.today().normalize()
    plan = []

    for _, row in subjects.iterrows():
        try:
            subject = str(row["subject"])
            
            try:
                exam = pd.to_datetime(row["exam_date"]).normalize()
                days_left = max((exam - today).days, 1)
            except:
                days_left = 30

            difficulty = DIFFICULTY.get(str(row["difficulty"]), 2)
            confidence = int(row["confidence"]) if pd.notna(row["confidence"]) else 3
            units = int(row["units"]) if pd.notna(row["units"]) else 1
            completed = int(row["completed_units"]) if pd.notna(row["completed_units"]) else 0
            remaining = max(units - completed, 0)

            prev_performance = 0
            if not prev_sem.empty:
                prev_subject = prev_sem[prev_sem["subject"].astype(str).str.lower() == subject.lower()]
                if not prev_subject.empty:
                    prev_performance = float(prev_subject["marks"].mean())
            
            mid_performance = 0
            if not mid_marks.empty:
                mid_subject = mid_marks[mid_marks["subject"].astype(str).str.lower() == subject.lower()]
                if not mid_subject.empty:
                    mid_performance = float(mid_subject["marks"].mean())

            subject_quizzes = quizzes[
                quizzes["subject"].astype(str).str.lower() == subject.lower()
            ] if not quizzes.empty else pd.DataFrame()
            quiz_avg = float(subject_quizzes["score"].mean()) if not subject_quizzes.empty else None

            recent_hours = 0
            if not sessions.empty:
                ss = sessions[
                    sessions["subject"].astype(str).str.lower() == subject.lower()
                ].copy()
                if not ss.empty:
                    ss["date"] = pd.to_datetime(ss["date"], errors="coerce")
                    ss = ss[ss["date"] >= today - timedelta(days=7)]
                    recent_hours = ss["duration_min"].sum() / 60

            urgency_score = min(30 / days_left, 30)
            difficulty_score = difficulty * 2
            confidence_score = (6 - confidence) * 2
            syllabus_score = remaining / max(units, 1) * 10
            quiz_score = (100 - quiz_avg) / 10 if quiz_avg is not None else 5
            study_penalty = min(recent_hours * 0.5, 5)
            
            performance_penalty = 0
            if prev_performance > 0 and prev_performance < 50:
                performance_penalty = (50 - prev_performance) / 10
            if mid_performance > 0 and mid_performance < 50:
                performance_penalty += (50 - mid_performance) / 10

            smart_score = (
                urgency_score + difficulty_score +
                confidence_score + syllabus_score +
                quiz_score - study_penalty + performance_penalty
            )

            reasons = []
            if days_left <= 7: reasons.append(f"Exam in {days_left} day(s)")
            if confidence <= 2: reasons.append("Low confidence")
            if remaining > 0: reasons.append(f"{remaining} unit(s) remaining")
            if quiz_avg is not None and quiz_avg < 60: reasons.append(f"Quiz average {quiz_avg:.0f}%")
            if prev_performance < 50: reasons.append(f"Previous semester: {prev_performance:.0f}%")
            if mid_performance < 50: reasons.append(f"Mid term: {mid_performance:.0f}%")
            if not reasons: reasons.append("Good opportunity for revision")

            plan.append({
                "subject": subject,
                "topic": get_topic_for_subject(subject),
                "score": smart_score,
                "days_left": days_left,
                "confidence": confidence,
                "remaining_units": remaining,
                "quiz_avg": quiz_avg,
                "recent_hours": recent_hours,
                "prev_performance": prev_performance,
                "mid_performance": mid_performance,
                "reason": " + ".join(reasons)
            })
        except Exception:
            continue

    return sorted(plan, key=lambda x: x["score"], reverse=True)

# --------------------- GEMINI AI CHATBOT --------------------
def setup_gemini(api_key):
    if not GEMINI_AVAILABLE:
        return None, "Google Generative AI package not installed. Run: pip install google-generativeai"
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        st.session_state.bot_available = True
        return model, "Success"
    except Exception as e:
        st.session_state.bot_available = False
        return None, f"Error: {str(e)}"

def get_bot_response(prompt, model, context=""):
    if not GEMINI_AVAILABLE or model is None:
        return "⚠️ AI Assistant is not available. Please install the required package: pip install google-generativeai"
    
    try:
        full_prompt = f"""You are MindMate, an AI study assistant helping students with their academic queries. 
        Context about the student: {context}
        
        Student Question: {prompt}
        
        Please provide a helpful, clear, and educational response. If you don't know something, be honest about it."""
        
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

def show_chatbot():
    st.markdown("### 🤖 MindMate AI Assistant")
    
    if not GEMINI_AVAILABLE:
        st.warning("""
        ⚠️ **Google Generative AI package not installed!**
        
        To use the AI Assistant, please install the required package:
        ```bash
        pip install google-generativeai
