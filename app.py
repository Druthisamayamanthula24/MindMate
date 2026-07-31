import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, date, timedelta
import random

# =========================================================
# MINDMATE - Smart Semester Study Planner & Analyzer
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
}
.subtitle {
    font-size: 18px;
    opacity: 0.75;
    margin-bottom: 25px;
}
.card {
    padding: 18px;
    border-radius: 14px;
    border: 1px solid rgba(128,128,128,.25);
    margin-bottom: 12px;
}
.small-muted {
    opacity: .7;
    font-size: 14px;
}
.big-number {
    font-size: 30px;
    font-weight: 700;
}
.priority-high { font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# --------------------- SESSION STATE ----------------------
def init_state():
    defaults = {
        "subjects": pd.DataFrame(columns=[
            "subject", "units", "difficulty", "confidence",
            "exam_date", "completed_units"
        ]),
        "exams": pd.DataFrame(columns=[
            "exam_name", "subject", "exam_date"
        ]),
        "sessions": pd.DataFrame(columns=[
            "date", "subject", "topic", "duration_min",
            "technique", "mood", "distractions",
            "productivity", "quiz_score"
        ]),
        "quiz_results": pd.DataFrame(columns=[
            "date", "subject", "topic", "score", "questions"
        ]),
        "timetable": pd.DataFrame(columns=[
            "day", "start", "end", "subject"
        ]),
        "current_subject": "",
        "current_topic": "",
        "study_running": False,
        "study_end": None,
        "study_start": None,
        "study_duration": 45,
        "break_running": False,
        "break_end": None,
        "quiz_topic": "",
        "quiz_subject": "",
        "quiz_questions": [],
        "quiz_answers": {},
        "quiz_submitted": False,
        "last_quiz_score": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# ---------------------- HELPERS --------------------------
DIFFICULTY = {"Easy": 1, "Medium": 2, "Hard": 3, "Very Hard": 4}

TOPIC_BANK = {
    "Python": [
        ("Which keyword defines a function in Python?", ["func", "def", "function", "define"], 1),
        ("Which data type stores key-value pairs?", ["list", "tuple", "set", "dictionary"], 3),
        ("Which symbol starts a comment in Python?", ["//", "#", "/*", "--"], 1),
        ("Which method adds an item to a list?", ["add()", "insertEnd()", "append()", "push()"], 2),
        ("What does len() return?", ["Memory size", "Number of elements", "Last index", "Data type"], 1),
        ("Which keyword is used for exception handling?", ["try", "check", "catch", "error"], 0),
        ("Which collection is immutable?", ["list", "set", "dictionary", "tuple"], 3),
        ("What is the output type of input() by default?", ["int", "float", "str", "bool"], 2),
    ],
    "C++": [
        ("Which keyword is used to create a class?", ["object", "class", "structs", "define"], 1),
        ("Which operator accesses members through an object?", [".", "->", "::", "#"], 0),
        ("Which symbol begins a single-line comment?", ["#", "//", "/*", "--"], 1),
        ("Which function is the entry point of a C++ program?", ["start()", "run()", "main()", "execute()"], 2),
        ("Which concept allows the same function name with different parameters?", ["Inheritance", "Overloading", "Encapsulation", "Abstraction"], 1),
    ],
    "Data Structures": [
        ("Which structure follows LIFO?", ["Queue", "Stack", "Tree", "Graph"], 1),
        ("Which structure follows FIFO?", ["Stack", "Queue", "Heap", "Tree"], 1),
        ("Binary search requires the data to be?", ["Random", "Sorted", "Duplicated", "Hashed"], 1),
        ("Which traversal visits Root, Left, Right?", ["Inorder", "Postorder", "Preorder", "Level only"], 2),
        ("Which data structure is commonly used for BFS?", ["Stack", "Queue", "Array only", "Set"], 1),
        ("What is the average time complexity of binary search?", ["O(n)", "O(log n)", "O(n²)", "O(1) always"], 1),
    ],
    "DBMS": [
        ("Which normal form removes partial dependency?", ["1NF", "2NF", "3NF", "BCNF"], 1),
        ("Which SQL command retrieves data?", ["GET", "SELECT", "FETCHALL", "OPEN"], 1),
        ("A primary key must be?", ["Duplicate", "Nullable", "Unique", "Optional"], 2),
        ("Which command adds rows to a table?", ["INSERT", "ADD", "PUT", "APPEND"], 0),
        ("Which property means a transaction is all-or-nothing?", ["Consistency", "Atomicity", "Isolation", "Durability"], 1),
    ],
    "Mathematics": [
        ("What is the derivative of x²?", ["x", "2x", "x²", "2"], 1),
        ("What is the value of sin(90°)?", ["0", "1", "-1", "Undefined"], 1),
        ("What is the slope of a horizontal line?", ["1", "0", "Undefined", "-1"], 1),
        ("What is the determinant of [[a,b],[c,d]]?", ["ab-cd", "ad-bc", "ac-bd", "a+b+c+d"], 1),
        ("What is the integral of 1 dx?", ["1", "x", "x²", "0"], 1),
    ],
    "AI/ML": [
        ("Which is supervised learning?", ["Clustering", "Classification", "PCA", "Association rules"], 1),
        ("Which algorithm is used for classification and regression?", ["Random Forest", "Apriori only", "K-Means only", "PCA"], 0),
        ("What is overfitting?", ["Model too simple", "Model memorizes training data too closely", "No training", "Missing data"], 1),
        ("Which metric is common for regression?", ["Accuracy", "MAE", "Precision", "Recall"], 1),
        ("K-Means is mainly used for?", ["Clustering", "Classification labels", "Sorting", "Encryption"], 0),
    ]
}

TECHNIQUES = ["Pomodoro", "Active Recall", "Practice Problems", "Mind Mapping", "Feynman Technique"]

def calculate_priority(row):
    today = pd.Timestamp.today().normalize()
    exam = pd.to_datetime(row["exam_date"])
    days_left = max((exam - today).days, 1)
    urgency = min(30 / days_left, 30)
    difficulty = DIFFICULTY.get(row["difficulty"], 2)
    confidence_gap = 6 - int(row["confidence"])
    remaining_units = max(int(row["units"]) - int(row["completed_units"]), 0)
    syllabus_factor = remaining_units / max(int(row["units"]), 1) * 5
    return round(urgency * 2 + difficulty * 2 + confidence_gap * 1.5 + syllabus_factor, 2)

def priority_label(score):
    if score >= 35:
        return "🔥 Very High"
    if score >= 25:
        return "🔴 High"
    if score >= 15:
        return "🟠 Medium"
    return "🟢 Low"

def get_recommendation():
    subjects = st.session_state.subjects.copy()
    if subjects.empty:
        return None
    subjects["priority"] = subjects.apply(calculate_priority, axis=1)
    return subjects.sort_values("priority", ascending=False).iloc[0]

def get_topic_for_subject(subject):
    if not subject:
        return "General Revision"
    aliases = {
        "Data Structures": "Data Structures",
        "Artificial Intelligence": "AI/ML",
        "Machine Learning": "AI/ML",
        "C++": "C++",
        "Python": "Python",
        "DBMS": "DBMS",
        "Mathematics": "Mathematics",
    }
    return f"{subject} Revision" if subject not in aliases else random.choice({
        "Python": ["Functions", "Lists & Dictionaries", "Exception Handling", "OOP"],
        "C++": ["Classes & Objects", "Constructors", "Inheritance", "Polymorphism"],
        "Data Structures": ["Stacks & Queues", "Trees", "Searching", "Sorting"],
        "DBMS": ["Normalization", "SQL", "Transactions", "Keys"],
        "Mathematics": ["Calculus", "Matrices", "Differentiation", "Integration"],
        "AI/ML": ["Supervised Learning", "Regression", "Classification", "Clustering"]
    }[aliases[subject]])

def available_questions(subject, topic):
    key = subject if subject in TOPIC_BANK else None
    if key:
        pool = TOPIC_BANK[key].copy()
        random.shuffle(pool)
        return pool[:5]
    return []

# ----------------------- SIDEBAR -------------------------
st.sidebar.title("🧠 MindMate")
st.sidebar.caption("Plan smarter • Study better • Score higher")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "🎓 Semester Setup",
        "📚 Subjects & Syllabus",
        "📅 Exam Timetable",
        "🗓️ Smart Planner",
        "⏱️ Study Session",
        "🧩 Break Puzzle",
        "📝 Topic Quiz",
        "📊 Analytics",
        "🤖 AI Insights"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "MindMate combines semester planning, exam urgency, "
    "study sessions, quizzes and analytics to create an adaptive plan."
)

# ======================== DASHBOARD ======================
if page == "🏠 Dashboard":
    st.markdown('<div class="main-title">🧠 MindMate</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Your Smart Semester Study Planner & Analyzer</div>', unsafe_allow_html=True)

    subjects = st.session_state.subjects
    sessions = st.session_state.sessions
    quizzes = st.session_state.quiz_results

    if subjects.empty:
        st.warning("👋 Welcome! Start with **Semester Setup** to enter your subjects and exam dates.")
        c1, c2, c3 = st.columns(3)
        c1.metric("📚 Subjects", 0)
        c2.metric("⏱️ Study Hours", "0.0h")
        c3.metric("📝 Quiz Average", "0%")
        st.markdown("### 🚀 Recommended first steps")
        st.write("1. Add your subjects → 2. Add exam dates → 3. Generate your plan → 4. Start a study session.")
    else:
        total_hours = sessions["duration_min"].sum() / 60 if not sessions.empty else 0
        quiz_avg = quizzes["score"].mean() if not quizzes.empty else 0
        completed_units = int(subjects["completed_units"].sum())
        total_units = int(subjects["units"].sum())

        rec = get_recommendation()
        next_exam = pd.to_datetime(subjects["exam_date"]).min()
        days_to_exam = max((next_exam.date() - date.today()).days, 0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📚 Subjects", len(subjects))
        c2.metric("⏱️ Study Hours", f"{total_hours:.1f}h")
        c3.metric("📝 Quiz Average", f"{quiz_avg:.0f}%" if quiz_avg else "—")
        c4.metric("📖 Syllabus", f"{completed_units}/{total_units}")

        st.markdown("---")
        left, right = st.columns([1.4, 1])

        with left:
            st.subheader("🔥 Today's Priority")
            st.success(
                f"**{rec['subject']}** — {priority_label(rec['priority'])}\n\n"
                f"Exam: {pd.to_datetime(rec['exam_date']).strftime('%d %b %Y')}  •  "
                f"{days_to_exam} day(s) remaining  •  "
                f"Confidence: {rec['confidence']}/5"
            )
            st.button("🚀 Open Smart Planner", key="dash_plan", on_click=lambda: None)

        with right:
            st.subheader("🎯 Semester Progress")
            progress = completed_units / total_units if total_units else 0
            st.progress(min(max(progress, 0), 1))
            st.write(f"**{progress*100:.0f}%** of units marked complete")

        st.subheader("📅 Upcoming Exams")
        exam_view = subjects[["subject", "exam_date", "difficulty", "confidence"]].copy()
        exam_view["Days Left"] = (
            pd.to_datetime(exam_view["exam_date"]).dt.normalize()
            - pd.Timestamp.today().normalize()
        ).dt.days.clip(lower=0)
        exam_view = exam_view.sort_values("exam_date")
        st.dataframe(exam_view, use_container_width=True, hide_index=True)

# ==================== SEMESTER SETUP =====================
elif page == "🎓 Semester Setup":
    st.title("🎓 Semester Setup")
    st.write("Enter the academic information MindMate needs to build your personalized plan.")

    with st.form("semester_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            semester = st.selectbox("Semester", ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"])
        with c2:
            academic_year = st.text_input("Academic Year", "2026-27")
        with c3:
            daily_hours = st.number_input("Available study hours/day", 0.5, 12.0, 2.0, 0.5)

        goal = st.text_input("Main goal", "Prepare consistently for Mid and Semester examinations")
        save = st.form_submit_button("💾 Save Semester Details")

        if save:
            st.session_state.semester_info = {
                "semester": semester,
                "academic_year": academic_year,
                "daily_hours": daily_hours,
                "goal": goal
            }
            st.success("✅ Semester details saved!")

    info = st.session_state.get("semester_info")
    if info:
        st.markdown("### Current Plan Settings")
        c1, c2, c3 = st.columns(3)
        c1.metric("Semester", info["semester"])
        c2.metric("Daily Study Target", f"{info['daily_hours']} h")
        c3.metric("Academic Year", info["academic_year"])
        st.info(f"🎯 Goal: {info['goal']}")

# ================= SUBJECTS & SYLLABUS ===================
elif page == "📚 Subjects & Syllabus":
    st.title("📚 Subjects & Syllabus")

    with st.form("subject_form"):
        c1, c2 = st.columns(2)
        with c1:
            subject = st.text_input("Subject Name", placeholder="e.g. Data Structures")
            units = st.number_input("Number of Units", 1, 12, 5)
            completed_units = st.number_input("Completed Units", 0, 12, 0)
        with c2:
            difficulty = st.selectbox("Difficulty", list(DIFFICULTY.keys()))
            confidence = st.slider("Current Confidence", 1, 5, 3)
            exam_date = st.date_input("Main Exam Date", date.today() + timedelta(days=30))

        add = st.form_submit_button("➕ Add / Save Subject")

        if add:
            if not subject.strip():
                st.error("Please enter a subject name.")
            else:
                new = {
                    "subject": subject.strip(),
                    "units": int(units),
                    "difficulty": difficulty,
                    "confidence": int(confidence),
                    "exam_date": pd.Timestamp(exam_date),
                    "completed_units": min(int(completed_units), int(units))
                }
                existing = st.session_state.subjects
                existing = existing[existing["subject"].str.lower() != subject.strip().lower()]
                st.session_state.subjects = pd.concat([existing, pd.DataFrame([new])], ignore_index=True)
                st.success(f"✅ {subject} saved.")

    if not st.session_state.subjects.empty:
        st.subheader("📋 Your Subjects")
        view = st.session_state.subjects.copy()
        view["Priority"] = view.apply(calculate_priority, axis=1)
        view["Priority Level"] = view["Priority"].apply(priority_label)
        st.dataframe(view, use_container_width=True, hide_index=True)

        st.caption("You can update a subject by entering the same subject name again.")

# ===================== EXAM TIMETABLE ====================
elif page == "📅 Exam Timetable":
    st.title("📅 Examination Timetable")
    subjects = list(st.session_state.subjects["subject"]) if not st.session_state.subjects.empty else []

    if not subjects:
        st.warning("Add subjects first in **Subjects & Syllabus**.")
    else:
        with st.form("exam_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                exam_name = st.selectbox("Exam", ["Mid-1", "Mid-2", "Semester Examination", "Lab Examination", "Assignment"])
            with c2:
                exam_subject = st.selectbox("Subject", subjects)
            with c3:
                exam_date = st.date_input("Date", date.today() + timedelta(days=7))
            add = st.form_submit_button("➕ Add Exam")
            if add:
                row = pd.DataFrame([{
                    "exam_name": exam_name,
                    "subject": exam_subject,
                    "exam_date": pd.Timestamp(exam_date)
                }])
                st.session_state.exams = pd.concat([st.session_state.exams, row], ignore_index=True)
                st.success("✅ Examination added.")

        if not st.session_state.exams.empty:
            st.subheader("📝 Examination Schedule")
            exams = st.session_state.exams.copy()
            exams["Days Left"] = (
                pd.to_datetime(exams["exam_date"]).dt.normalize()
                - pd.Timestamp.today().normalize()
            ).dt.days.clip(lower=0)
            st.dataframe(exams.sort_values("exam_date"), use_container_width=True, hide_index=True)

# ====================== SMART PLANNER ====================
elif page == "🗓️ Smart Planner":
    st.title("🗓️ Smart Study Planner")
    subjects = st.session_state.subjects.copy()

    if subjects.empty:
        st.warning("Add subjects and exam dates first.")
    else:
        subjects["priority"] = subjects.apply(calculate_priority, axis=1)
        subjects["Priority"] = subjects["priority"].apply(priority_label)
        subjects["Days Left"] = (
            pd.to_datetime(subjects["exam_date"]).dt.normalize()
            - pd.Timestamp.today().normalize()
        ).dt.days.clip(lower=0)
        subjects = subjects.sort_values("priority", ascending=False)

        st.subheader("🔥 Priority Ranking")
        st.dataframe(
            subjects[["subject", "Days Left", "difficulty", "confidence", "completed_units", "units", "priority", "Priority"]],
            use_container_width=True, hide_index=True
        )

        rec = subjects.iloc[0]
        topic = get_topic_for_subject(rec["subject"])
        st.subheader("🎯 Today's Recommended Session")
        c1, c2, c3 = st.columns(3)
        c1.metric("Subject", rec["subject"])
        c2.metric("Recommended Time", "45 min")
        c3.metric("Priority", priority_label(rec["priority"]))

        st.info(
            f"**Topic:** {topic}\n\n"
            f"Exam in approximately **{int(rec['Days Left'])} day(s)**. "
            f"Difficulty is **{rec['difficulty']}** and confidence is **{rec['confidence']}/5**."
        )

        if st.button("🚀 Start Today's Study", type="primary"):
            st.session_state.current_subject = rec["subject"]
            st.session_state.current_topic = topic
            st.session_state.study_duration = 45
            st.session_state.study_start = datetime.now()
            st.session_state.study_end = datetime.now() + timedelta(minutes=45)
            st.session_state.study_running = True
            st.success("Study session started! Open **Study Session** to see the timer.")

# ===================== STUDY SESSION =====================
elif page == "⏱️ Study Session":
    st.title("⏱️ Study Session")

    if not st.session_state.current_subject:
        st.info("Choose today's task from **Smart Planner** first.")
    else:
        st.subheader(f"📚 {st.session_state.current_subject}")
        st.write(f"🎯 Topic: **{st.session_state.current_topic}**")

        if not st.session_state.study_running:
            st.warning("No active study timer.")
            if st.button("▶️ Start 45-Minute Session"):
                st.session_state.study_start = datetime.now()
                st.session_state.study_end = datetime.now() + timedelta(minutes=45)
                st.session_state.study_duration = 45
                st.session_state.study_running = True
                st.rerun()
        else:
            remaining = max(
                0,
                int((st.session_state.study_end - datetime.now()).total_seconds())
            )
            minutes, seconds = divmod(remaining, 60)
            st.markdown(
                f"<div style='text-align:center;font-size:72px;font-weight:800'>{minutes:02d}:{seconds:02d}</div>",
                unsafe_allow_html=True
            )
            st.progress(1 - remaining / (st.session_state.study_duration * 60))

            if remaining > 0:
                st.caption("Stay focused. MindMate is tracking this session.")
                st.write("⏳ Refreshing timer...")
                import time
                time.sleep(1)
                st.rerun()
            else:
                st.session_state.study_running = False
                st.toast("🎉 Study session complete! Time for your break.")
                st.success("🎉 Study session complete!")
                st.session_state.break_end = datetime.now() + timedelta(minutes=5)
                st.session_state.break_running = True

                with st.form("session_feedback"):
                    mood = st.slider("How was your mood?", 1, 5, 4)
                    distractions = st.slider("Distractions", 0, 5, 1)
                    technique = st.selectbox("Technique used", TECHNIQUES)
                    productivity = st.slider("Productivity", 1, 5, 4)
                    save = st.form_submit_button("💾 Save Session & Take Break")
                    if save:
                        row = pd.DataFrame([{
                            "date": pd.Timestamp.today().normalize(),
                            "subject": st.session_state.current_subject,
                            "topic": st.session_state.current_topic,
                            "duration_min": st.session_state.study_duration,
                            "technique": technique,
                            "mood": mood,
                            "distractions": distractions,
                            "productivity": productivity,
                            "quiz_score": np.nan
                        }])
                        st.session_state.sessions = pd.concat([st.session_state.sessions, row], ignore_index=True)
                        st.success("Session saved. Take your break!")

# ====================== BREAK PUZZLE =====================
elif page == "🧩 Break Puzzle":
    st.title("🧩 Break Time")
    st.write("A short puzzle to refresh your mind before the quiz.")

    q = st.session_state.get("break_question", None)
    if q is None:
        a, b = random.randint(3, 12), random.randint(2, 9)
        q = {"a": a, "b": b, "answer": a + b * 2}
        st.session_state.break_question = q

    st.info(f"🧩 Solve: **{q['a']} + {q['b']} × 2 = ?**")
    answer = st.number_input("Your answer", min_value=0, step=1)
    if st.button("✅ Check"):
        if int(answer) == q["answer"]:
            st.success("🎉 Correct! Break completed. Now take your topic quiz.")
            st.session_state.break_question = None
        else:
            st.error("Not quite. Try again!")

# ======================== QUIZ ==========================
elif page == "📝 Topic Quiz":
    st.title("📝 Topic-Based Quiz")
    st.write("The quiz checks understanding of the topic you just studied.")

    subjects = list(st.session_state.subjects["subject"]) if not st.session_state.subjects.empty else []
    default_subject = st.session_state.current_subject if st.session_state.current_subject in subjects else (subjects[0] if subjects else "")

    if not subjects:
        st.warning("Add subjects first.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            quiz_subject = st.selectbox("Subject", subjects, index=subjects.index(default_subject))
        with c2:
            quiz_topic = st.text_input("Topic", st.session_state.current_topic or "General Revision")

        if st.button("🎲 Generate 5-Question Quiz"):
            questions = available_questions(quiz_subject, quiz_topic)
            if not questions:
                st.warning("A built-in question bank is not available for this subject yet. Use one of the supported subjects: Python, C++, Data Structures, DBMS, Mathematics or AI/ML.")
            else:
                st.session_state.quiz_subject = quiz_subject
                st.session_state.quiz_topic = quiz_topic
                st.session_state.quiz_questions = questions
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state.last_quiz_score = None

        if st.session_state.quiz_questions and not st.session_state.quiz_submitted:
            st.markdown("---")
            for i, (question, options, correct) in enumerate(st.session_state.quiz_questions):
                st.session_state.quiz_answers[i] = st.radio(
                    f"Q{i+1}. {question}",
                    options,
                    index=None,
                    key=f"quiz_{i}"
                )

            if st.button("📊 Submit Quiz", type="primary"):
                answered = 0
                correct_count = 0
                for i, (_, options, correct) in enumerate(st.session_state.quiz_questions):
                    selected = st.session_state.quiz_answers.get(i)
                    if selected is not None:
                        answered += 1
                        if options.index(selected) == correct:
                            correct_count += 1

                score = round(correct_count / len(st.session_state.quiz_questions) * 100)
                st.session_state.last_quiz_score = score
                st.session_state.quiz_submitted = True

                row = pd.DataFrame([{
                    "date": pd.Timestamp.today().normalize(),
                    "subject": quiz_subject,
                    "topic": quiz_topic,
                    "score": score,
                    "questions": len(st.session_state.quiz_questions)
                }])
                st.session_state.quiz_results = pd.concat([st.session_state.quiz_results, row], ignore_index=True)

                if not st.session_state.sessions.empty:
                    idx = st.session_state.sessions.index[-1]
                    if st.session_state.sessions.loc[idx, "subject"] == quiz_subject:
                        st.session_state.sessions.loc[idx, "quiz_score"] = score

        if st.session_state.quiz_submitted:
            score = st.session_state.last_quiz_score
            st.success(f"🎉 Quiz completed! Score: **{score}%**")
            if score >= 80:
                st.info("🟢 Topic mastery looks strong. MindMate can move you toward the next topic.")
            elif score >= 60:
                st.warning("🟠 Good start. A short revision is recommended.")
            else:
                st.error("🔴 Weak area detected. MindMate recommends revising this topic before moving on.")

# ======================== ANALYTICS ======================
elif page == "📊 Analytics":
    st.title("📊 Study Analytics")

    sessions = st.session_state.sessions.copy()
    quizzes = st.session_state.quiz_results.copy()

    if sessions.empty:
        st.info("Complete a study session to start seeing analytics.")
    else:
        sessions["date"] = pd.to_datetime(sessions["date"])
        total_hours = sessions["duration_min"].sum() / 60
        avg_productivity = sessions["productivity"].mean()
        avg_distraction = sessions["distractions"].mean()

        c1, c2, c3 = st.columns(3)
        c1.metric("⏱️ Total Study", f"{total_hours:.1f} h")
        c2.metric("⭐ Avg Productivity", f"{avg_productivity:.1f}/5")
        c3.metric("📵 Avg Distractions", f"{avg_distraction:.1f}")

        daily = sessions.groupby("date", as_index=False)["duration_min"].sum()
        fig = px.line(daily, x="date", y="duration_min", markers=True, title="Daily Study Time")
        st.plotly_chart(fig, use_container_width=True)

        subject_hours = sessions.groupby("subject", as_index=False)["duration_min"].sum()
        fig = px.pie(subject_hours, values="duration_min", names="subject", title="Study Time by Subject")
        st.plotly_chart(fig, use_container_width=True)

        if not quizzes.empty:
            quiz_subject = quizzes.groupby("subject", as_index=False)["score"].mean()
            fig = px.bar(quiz_subject, x="subject", y="score", title="Average Quiz Score by Subject", range_y=[0, 100])
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Session History")
        st.dataframe(sessions.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

# ======================= AI INSIGHTS =====================
elif page == "🤖 AI Insights":
    st.title("🤖 AI Insights & Recommendations")

    subjects = st.session_state.subjects.copy()
    quizzes = st.session_state.quiz_results.copy()
    sessions = st.session_state.sessions.copy()

    if subjects.empty:
        st.info("Add semester subjects first.")
    else:
        subjects["priority"] = subjects.apply(calculate_priority, axis=1)
        top = subjects.sort_values("priority", ascending=False).iloc[0]

        st.subheader("🔥 Highest Priority")
        st.success(
            f"Focus on **{top['subject']}**. "
            f"Priority: {priority_label(top['priority'])}. "
            f"Confidence: {top['confidence']}/5."
        )

        st.subheader("🧠 Personalized Insights")

        if not quizzes.empty:
            avg = quizzes.groupby("subject")["score"].mean()
            weakest = avg.idxmin()
            weakest_score = avg.min()
            st.write(
                f"• **{weakest}** is currently your weakest measured subject "
                f"with an average quiz score of **{weakest_score:.0f}%**."
            )
        else:
            st.write("• Complete topic quizzes so MindMate can identify weak areas.")

        if not sessions.empty:
            best = sessions.groupby("subject")["productivity"].mean().idxmax()
            best_score = sessions.groupby("subject")["productivity"].mean().max()
            st.write(
                f"• Your highest average productivity has been in **{best}** "
                f"({best_score:.1f}/5)."
            )
            if sessions["distractions"].mean() > 2:
                st.write("• Your average distraction level is high. Try phone-free study blocks.")
            else:
                st.write("• Your distraction level is under control. Keep the same study environment.")
        else:
            st.write("• Complete a few study sessions to unlock behaviour-based insights.")

        days = max((pd.to_datetime(top["exam_date"]).date() - date.today()).days, 0)
        if days <= 7:
            st.warning(
                f"⚠️ **{top['subject']}** exam is in {days} day(s). "
                "Prioritize revision, practice questions and a short quiz."
            )
        elif days <= 14:
            st.info(
                f"📅 **{top['subject']}** exam is in {days} days. "
                "Keep consistent daily sessions."
            )
        else:
            st.success(
                f"✅ You have {days} days before the **{top['subject']}** exam. "
                "Use this time for steady syllabus completion."
            )

        st.subheader("🎯 Suggested Next Action")
        st.write(
            f"Study **{top['subject']}** for 45 minutes, complete a topic quiz, "
            "and use the quiz result to adjust your next session."
        )

# ====================== END APP ==========================
st.sidebar.markdown("---")
st.sidebar.caption("MindMate • Streamlit • Pandas • Plotly • Adaptive Study Planning")
