import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import random
import os
import hashlib

# =========================================================
# MINDMATE - Smart Semester Study Planner & Analyzer
# Version 4.0 - Smart Daily Study Plan
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
.main-title {font-size:42px;font-weight:800;margin-bottom:0;}
.subtitle {font-size:18px;opacity:.75;margin-bottom:25px;}
.card {padding:18px;border-radius:14px;border:1px solid rgba(128,128,128,.25);margin-bottom:12px;}
.metric-card {padding:15px;border-radius:12px;color:white;text-align:center;background:linear-gradient(135deg,#667eea,#764ba2);}
.metric-value {font-size:28px;font-weight:700;}
.metric-label {font-size:14px;opacity:.9;}
.priority-high {font-weight:700;}
.study-timer {text-align:center;font-size:60px;font-weight:800;font-family:monospace;padding:20px;}
</style>
""", unsafe_allow_html=True)

# --------------------- DATA ------------------------------
DATA_DIR = "mindmate_data"
os.makedirs(DATA_DIR, exist_ok=True)

SCHEMAS = {
    "subjects": ["subject","units","difficulty","confidence","exam_date","completed_units"],
    "exams": ["exam_name","subject","exam_date"],
    "sessions": ["date","subject","topic","duration_min","technique","mood","distractions","productivity","quiz_score"],
    "quiz_results": ["date","subject","topic","score","questions","attempt_id"],
    "timetable": ["day","start","end","subject"],
    "quiz_attempts": ["attempt_id","subject","topic","attempt_time","question_hash","completed"],
    "coding_problems": ["problem_id","platform","problem_name","difficulty","topic","date_solved","time_taken","language","score"]
}

def empty_df(name):
    return pd.DataFrame(columns=SCHEMAS[name])

def load_df(name):
    path = os.path.join(DATA_DIR, f"{name}.csv")
    try:
        df = pd.read_csv(path)
        for col in SCHEMAS[name]:
            if col not in df.columns:
                df[col] = None
        df = df[SCHEMAS[name]]
        for col in ["exam_date","date","attempt_time","date_solved"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df
    except Exception:
        return empty_df(name)

def save_all():
    for name in SCHEMAS:
        st.session_state[name].to_csv(
            os.path.join(DATA_DIR, f"{name}.csv"), index=False
        )

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
        "semester_info": {}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# --------------------- CONSTANTS --------------------------
DIFFICULTY = {"Easy":1, "Medium":2, "Hard":3, "Very Hard":4}
CODING_PLATFORMS = ["LeetCode","HackerRank","CodeChef","Codeforces","GeeksforGeeks","AtCoder","Custom"]
CODING_LANGUAGES = ["Python","C++","Java","JavaScript","Go","Rust","C#","Ruby","Swift"]
CODING_DIFFICULTIES = ["Easy","Medium","Hard"]
TECHNIQUES = ["Pomodoro","Active Recall","Practice Problems","Mind Mapping","Feynman Technique","Spaced Repetition"]

TOPIC_BANK = {
    "Python": [
        ("Which keyword defines a function in Python?",["func","def","function","define"],1),
        ("Which data type stores key-value pairs?",["list","tuple","set","dictionary"],3),
        ("Which symbol starts a comment in Python?",["//","#","/*","--"],1),
        ("Which method adds an item to a list?",["add()","insertEnd()","append()","push()"],2),
        ("What does len() return?",["Memory size","Number of elements","Last index","Data type"],1),
        ("Which keyword is used for exception handling?",["try","check","catch","error"],0),
        ("Which collection is immutable?",["list","set","dictionary","tuple"],3),
        ("What is the output type of input() by default?",["int","float","str","bool"],2),
        ("Which loop is used for definite iteration?",["while","for","do-while","until"],1),
        ("What is the result of 3 ** 2?",["6","9","8","5"],1)
    ],
    "C++": [
        ("Which keyword is used to create a class?",["object","class","structs","define"],1),
        ("Which operator accesses members through an object?",[".","->","::","#"],0),
        ("Which symbol begins a single-line comment?",["#","//","/*","--"],1),
        ("Which function is the entry point of a C++ program?",["start()","run()","main()","execute()"],2),
        ("Which concept allows the same function name with different parameters?",["Inheritance","Overloading","Encapsulation","Abstraction"],1),
        ("What is the size of int commonly on a 64-bit system?",["2","4","8","16"],1),
        ("Which keyword is used for dynamic memory allocation?",["new","malloc","alloc","create"],0),
        ("What is the default access specifier in a class?",["public","private","protected","internal"],1)
    ],
    "Data Structures": [
        ("Which structure follows LIFO?",["Queue","Stack","Tree","Graph"],1),
        ("Which structure follows FIFO?",["Stack","Queue","Heap","Tree"],1),
        ("Binary search requires the data to be?",["Random","Sorted","Duplicated","Hashed"],1),
        ("Which traversal visits Root, Left, Right?",["Inorder","Postorder","Preorder","Level only"],2),
        ("Which data structure is commonly used for BFS?",["Stack","Queue","Array only","Set"],1),
        ("Average time complexity of binary search?",["O(n)","O(log n)","O(n²)","O(1) always"],1),
        ("Which structure is used for implementing recursion?",["Queue","Stack","Heap","Array"],1),
        ("What is the minimum height order of a binary tree with n nodes?",["log n","n","n/2","sqrt(n)"],0)
    ],
    "DBMS": [
        ("Which normal form removes partial dependency?",["1NF","2NF","3NF","BCNF"],1),
        ("Which SQL command retrieves data?",["GET","SELECT","FETCHALL","OPEN"],1),
        ("A primary key must be?",["Duplicate","Nullable","Unique","Optional"],2),
        ("Which command adds rows to a table?",["INSERT","ADD","PUT","APPEND"],0),
        ("Which property means a transaction is all-or-nothing?",["Consistency","Atomicity","Isolation","Durability"],1),
        ("Default order of ORDER BY?",["Descending","Ascending","Random","None"],1),
        ("Which join returns all rows from left table?",["INNER JOIN","LEFT JOIN","RIGHT JOIN","FULL JOIN"],1),
        ("What is the maximum length of VARCHAR in MySQL?",["255","65535","16777215","No limit"],1)
    ],
    "Mathematics": [
        ("Derivative of x²?",["x","2x","x²","2"],1),
        ("Value of sin(90°)?",["0","1","-1","Undefined"],1),
        ("Slope of a horizontal line?",["1","0","Undefined","-1"],1),
        ("Determinant of [[a,b],[c,d]]?",["ab-cd","ad-bc","ac-bd","a+b+c+d"],1),
        ("Integral of 1 dx?",["1","x","x²","0"],1),
        ("Derivative of ln(x)?",["1/x","x","x²","e^x"],0),
        ("sin²(x) + cos²(x) equals?",["0","1","2","sin(x)"],1),
        ("Area of a circle?",["πr","2πr","πr²","πd"],2)
    ],
    "AI/ML": [
        ("Which is supervised learning?",["Clustering","Classification","PCA","Association rules"],1),
        ("Which algorithm can be used for classification and regression?",["Random Forest","Apriori only","K-Means only","PCA"],0),
        ("What is overfitting?",["Model too simple","Model memorizes training data too closely","No training","Missing data"],1),
        ("Which metric is common for regression?",["Accuracy","MAE","Precision","Recall"],1),
        ("K-Means is mainly used for?",["Clustering","Classification labels","Sorting","Encryption"],0),
        ("Activation function commonly used for binary classification output?",["ReLU","Sigmoid","Tanh","Linear"],1),
        ("Which technique reduces dimensionality?",["PCA","CNN","RNN","LSTM"],0),
        ("A neural network is inspired by?",["Computer","Brain","Database","Algorithm"],1)
    ]
}

GENERIC_QUESTIONS = [
    ("What is critical thinking?",["Following instructions","Analyzing information","Memorizing facts","Copying answers"],1),
    ("Which skill is essential for effective learning?",["Time management","Social media","Watching videos","Skipping topics"],0),
    ("What is the scientific method based on?",["Observation and experiment","Tradition","Authority","Intuition"],0),
    ("Which learning style uses visual aids?",["Auditory","Visual","Kinesthetic","Logical"],1),
    ("What is the Pareto principle?",["80/20 rule","50/50 rule","90/10 rule","All topics equally"],0),
    ("Which approach is useful for complex problems?",["Divide and conquer","Ignore the problem","Guessing","Skipping"],0),
    ("What helps long-term retention?",["Spaced repetition","Cramming only","Skipping revision","Random study"],0),
    ("What is active recall?",["Retrieving information from memory","Reading only","Copying notes","Watching videos"],0)
]

# --------------------- HELPERS ----------------------------
def get_topic_for_subject(subject):
    aliases = {
        "Python":["Functions","Lists & Dictionaries","Exception Handling","OOP","File Handling"],
        "C++":["Classes & Objects","Constructors","Inheritance","Polymorphism","Templates"],
        "Data Structures":["Stacks & Queues","Trees","Searching","Sorting","Graphs"],
        "DBMS":["Normalization","SQL","Transactions","Keys","Constraints"],
        "Mathematics":["Calculus","Matrices","Differentiation","Integration","Probability"],
        "AI/ML":["Supervised Learning","Regression","Classification","Clustering","Neural Networks"]
    }
    subject = str(subject)
    for key, topics in aliases.items():
        if key.lower() in subject.lower():
            return random.choice(topics)
    return f"{subject} Revision"

def available_questions(subject):
    matched = None
    for key in TOPIC_BANK:
        if key.lower() in str(subject).lower() or str(subject).lower() in key.lower():
            matched = key
            break
    pool = TOPIC_BANK[matched].copy() if matched else GENERIC_QUESTIONS.copy()
    random.shuffle(pool)
    return pool[:5]

def calculate_priority(row):
    try:
        today = pd.Timestamp.today().normalize()
        exam = pd.to_datetime(row["exam_date"])
        days_left = max((exam-today).days, 1)
        urgency = min(30/days_left, 30)
        difficulty = DIFFICULTY.get(str(row["difficulty"]), 2)
        confidence_gap = 6-int(row["confidence"])
        remaining = max(int(row["units"])-int(row["completed_units"]), 0)
        syllabus = remaining/max(int(row["units"]),1)*5
        return round(urgency*2 + difficulty*2 + confidence_gap*1.5 + syllabus, 2)
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
    df["priority"] = df.apply(calculate_priority, axis=1)
    return df.sort_values("priority", ascending=False).iloc[0]

def generate_attempt_id(subject, topic):
    raw = f"{subject}_{topic}_{datetime.now().isoformat()}_{random.random()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def generate_smart_daily_plan():
    subjects = st.session_state.subjects.copy()
    sessions = st.session_state.sessions.copy()
    quizzes = st.session_state.quiz_results.copy()

    if subjects.empty:
        return []

    today = pd.Timestamp.today().normalize()
    plan = []

    for _, row in subjects.iterrows():
        subject = str(row["subject"])

        try:
            exam = pd.to_datetime(row["exam_date"]).normalize()
            days_left = max((exam-today).days, 1)
        except:
            days_left = 30

        difficulty = DIFFICULTY.get(str(row["difficulty"]), 2)
        confidence = int(row["confidence"]) if pd.notna(row["confidence"]) else 3
        units = int(row["units"]) if pd.notna(row["units"]) else 1
        completed = int(row["completed_units"]) if pd.notna(row["completed_units"]) else 0
        remaining = max(units-completed, 0)

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
                ss = ss[ss["date"] >= today-timedelta(days=7)]
                recent_hours = ss["duration_min"].sum()/60

        urgency_score = min(30/days_left, 30)
        difficulty_score = difficulty*2
        confidence_score = (6-confidence)*2
        syllabus_score = remaining/max(units,1)*10
        quiz_score = (100-quiz_avg)/10 if quiz_avg is not None else 5
        study_penalty = min(recent_hours*0.5, 5)

        smart_score = (
            urgency_score + difficulty_score +
            confidence_score + syllabus_score +
            quiz_score - study_penalty
        )

        reasons = []
        if days_left <= 7: reasons.append(f"Exam in {days_left} day(s)")
        if confidence <= 2: reasons.append("Low confidence")
        if remaining > 0: reasons.append(f"{remaining} unit(s) remaining")
        if quiz_avg is not None and quiz_avg < 60:
            reasons.append(f"Quiz average {quiz_avg:.0f}%")
        if not reasons: reasons.append("Good opportunity for revision")

        plan.append({
            "subject":subject,
            "topic":get_topic_for_subject(subject),
            "score":smart_score,
            "days_left":days_left,
            "confidence":confidence,
            "remaining_units":remaining,
            "quiz_avg":quiz_avg,
            "recent_hours":recent_hours,
            "reason":" + ".join(reasons)
        })

    return sorted(plan, key=lambda x:x["score"], reverse=True)

# --------------------- SIDEBAR ----------------------------
with st.sidebar:
    st.markdown("## 🧠 MindMate")
    st.caption("Smart Semester Study Planner")

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "🧠 Smart Daily Plan",
            "📚 Semester Setup",
            "⏱️ Study Session",
            "📝 Quiz",
            "💻 Coding Tracker",
            "📅 Timetable",
            "📊 Analytics"
        ]
    )

    st.markdown("---")
    st.caption("MindMate v4.0")
    if st.button("💾 Save Data", use_container_width=True):
        save_all()
        st.success("Saved!")

# ======================== DASHBOARD =======================
if page == "🏠 Dashboard":
    st.markdown('<div class="main-title">🧠 MindMate</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Your Smart Semester Study Planner & Analyzer</div>', unsafe_allow_html=True)

    subjects = st.session_state.subjects
    sessions = st.session_state.sessions
    quizzes = st.session_state.quiz_results
    coding = st.session_state.coding_problems
    exams = st.session_state.exams

    if subjects.empty:
        st.warning("👋 Welcome! Start with Semester Setup.")
        c1,c2,c3 = st.columns(3)
        c1.metric("📚 Subjects",0)
        c2.metric("⏱️ Study Hours","0.0h")
        c3.metric("📝 Quiz Average","0%")
        st.info("Add subjects → add exams → use Smart Daily Plan → start studying.")
    else:
        total_hours = sessions["duration_min"].sum()/60 if not sessions.empty else 0
        quiz_avg = quizzes["score"].mean() if not quizzes.empty else 0
        completed = int(subjects["completed_units"].sum())
        total = int(subjects["units"].sum())
        coding_count = len(coding)
        progress = completed/total if total else 0

        # streak using unique dates
        streak = 0
        if not sessions.empty:
            dates = sorted(set(pd.to_datetime(sessions["date"], errors="coerce").dt.date.dropna()), reverse=True)
            expected = date.today()
            for d in dates:
                if d == expected:
                    streak += 1
                    expected -= timedelta(days=1)
                elif d < expected:
                    break

        cols = st.columns(6)
        metrics = [
            (len(subjects),"📚 Subjects"),
            (f"{total_hours:.1f}h","⏱️ Study Hours"),
            (f"{quiz_avg:.0f}%","📝 Quiz Avg"),
            (f"{completed}/{total}","📖 Progress"),
            (f"{streak}🔥","Day Streak"),
            (coding_count,"💻 Problems")
        ]
        for col,(value,label) in zip(cols,metrics):
            with col:
                st.markdown(f"<div class='metric-card'><div class='metric-value'>{value}</div><div class='metric-label'>{label}</div></div>",unsafe_allow_html=True)

        st.markdown("---")
        rec = get_recommendation()

        left,right = st.columns([1.4,1])
        with left:
            st.subheader("🎯 Today's Priority")
            if rec is not None:
                score = calculate_priority(rec)
                st.markdown(f"""
                <div class="card">
                <h2>{rec['subject']}</h2>
                <p><b>Priority:</b> {priority_label(score)}</p>
                <p><b>Exam:</b> {pd.to_datetime(rec['exam_date']).strftime('%d %b %Y')}</p>
                <p><b>Confidence:</b> {'⭐'*int(rec['confidence'])}{'☆'*(5-int(rec['confidence']))}</p>
                <p><b>Units:</b> {rec['completed_units']}/{rec['units']}</p>
                </div>
                """,unsafe_allow_html=True)

                if st.button("🧠 Open Smart Daily Plan",type="primary",use_container_width=True):
                    st.session_state._goto_smart = True
                    st.rerun()

            st.subheader("⏱️ Recent Study")
            if sessions.empty:
                st.info("No study sessions yet.")
            else:
                for _,s in sessions.sort_values("date",ascending=False).head(5).iterrows():
                    st.write(f"📚 **{s['subject']}** — {s['topic']} • {s['duration_min']} min")

        with right:
            st.subheader("📊 Syllabus Progress")
            st.metric("Completion",f"{progress*100:.0f}%")
            st.progress(progress)
            st.metric("🎯 Avg Productivity",f"{sessions['productivity'].mean():.1f}/5" if not sessions.empty else "—")
            st.metric("📝 Quizzes",len(quizzes))
            st.metric("💻 Coding Problems",len(coding))

        st.markdown("---")
        st.subheader("📈 Performance Overview")
        a,b = st.columns(2)

        with a:
            if not sessions.empty:
                d = sessions.copy()
                d["date"] = pd.to_datetime(d["date"]).dt.date
                daily = d.groupby("date",as_index=False)["duration_min"].sum()
                fig = px.bar(daily.tail(14),x="date",y="duration_min",title="📚 Study Time",labels={"duration_min":"Minutes"})
                st.plotly_chart(fig,use_container_width=True)
            else:
                st.info("Study to generate charts.")

        with b:
            if not quizzes.empty:
                q = quizzes.groupby("subject",as_index=False)["score"].mean()
                fig = px.bar(q,x="subject",y="score",range_y=[0,100],title="📝 Quiz Performance")
                st.plotly_chart(fig,use_container_width=True)
            else:
                st.info("Take quizzes to see performance.")

# ================= SMART DAILY PLAN =======================
elif page == "🧠 Smart Daily Plan":
    st.markdown('<div class="main-title">🧠 Smart Daily Study Plan</div>',unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>MindMate creates today's plan from your exams, confidence, syllabus, quizzes and study history.</div>", unsafe_allow_html=True)
    plan = generate_smart_daily_plan()

    if not plan:
        st.warning("Add subjects first in Semester Setup.")
    else:
        top = plan[0]
        st.markdown(f"""
        <div style="padding:25px;border-radius:16px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;">
        <h2>🎯 Top Priority: {top['subject']}</h2>
        <p><b>Recommended topic:</b> {top['topic']}</p>
        <p><b>Why:</b> {top['reason']}</p>
        <p><b>Exam:</b> {top['days_left']} day(s) remaining</p>
        </div>
        """,unsafe_allow_html=True)

        st.markdown("### 📚 Today's Plan")
        durations = [45,45,30]
        for i,item in enumerate(plan[:3]):
            st.markdown(f"""
            <div class="card">
            <h3>{['1️⃣','2️⃣','3️⃣'][i]} {item['subject']}</h3>
            <p>📖 <b>Topic:</b> {item['topic']}</p>
            <p>⏱️ <b>Duration:</b> {durations[i]} minutes</p>
            <p>🎯 <b>Reason:</b> {item['reason']}</p>
            <p>📊 <b>Smart Priority:</b> {item['score']:.1f}</p>
            </div>
            """,unsafe_allow_html=True)

            if st.button(f"🚀 Start {item['subject']} Session",key=f"smart_{i}",use_container_width=True):
                st.session_state.current_subject = item["subject"]
                st.session_state.current_topic = item["topic"]
                st.session_state.study_duration = durations[i]
                st.session_state.study_start = datetime.now()
                st.session_state.study_end = datetime.now()+timedelta(minutes=durations[i])
                st.session_state.study_running = True
                st.success("Study session started!")
                st.rerun()

        st.info("☕ After two focused sessions, take a 15-minute break. Then continue with the next priority.")

        st.markdown("### 💻 Coding Goal")
        st.success("Solve 1 Easy + 1 Medium coding problem for today's placement practice.")

        table = pd.DataFrame([{
            "Subject":x["subject"],
            "Priority":round(x["score"],1),
            "Exam Days":x["days_left"],
            "Confidence":f"{x['confidence']}/5",
            "Remaining Units":x["remaining_units"],
            "Quiz Average":f"{x['quiz_avg']:.0f}%" if x["quiz_avg"] is not None else "No quiz"
        } for x in plan])
        st.dataframe(table,use_container_width=True,hide_index=True)

        if top["quiz_avg"] is None:
            st.info(f"📝 Take a quiz after studying {top['subject']} to let MindMate learn your weak areas.")
        elif top["quiz_avg"] < 50:
            st.error(f"⚠️ {top['subject']} quiz performance is low ({top['quiz_avg']:.0f}%). Focus on concepts and Active Recall.")
        elif top["quiz_avg"] < 70:
            st.warning(f"🟠 {top['subject']} is at {top['quiz_avg']:.0f}%. Use Active Recall and Practice Problems.")
        else:
            st.success(f"🟢 {top['subject']} is at {top['quiz_avg']:.0f}%. Focus on revision and harder questions.")

# ================= SEMESTER SETUP =========================
elif page == "📚 Semester Setup":
    st.markdown('<div class="main-title">📚 Semester Setup</div>',unsafe_allow_html=True)

    with st.form("subject_form",clear_on_submit=True):
        c1,c2 = st.columns(2)
        with c1:
            subject = st.text_input("Subject Name")
            units = st.number_input("Total Units",1,20,5)
            difficulty = st.selectbox("Difficulty",list(DIFFICULTY.keys()))
        with c2:
            confidence = st.slider("Confidence",1,5,3)
            exam_date = st.date_input("Exam Date",date.today()+timedelta(days=30))
            completed = st.number_input("Completed Units",0,20,0)

        submitted = st.form_submit_button("➕ Add Subject",type="primary")
        if submitted:
            if not subject.strip():
                st.error("Enter a subject name.")
            else:
                new = pd.DataFrame([{
                    "subject":subject.strip(),
                    "units":units,
                    "difficulty":difficulty,
                    "confidence":confidence,
                    "exam_date":pd.Timestamp(exam_date),
                    "completed_units":min(completed,units)
                }])
                st.session_state.subjects = pd.concat([st.session_state.subjects,new],ignore_index=True)
                save_all()
                st.success(f"{subject} added!")

    st.markdown("### 📚 Your Subjects")
    if st.session_state.subjects.empty:
        st.info("No subjects added.")
    else:
        st.dataframe(st.session_state.subjects,use_container_width=True,hide_index=True)

        st.markdown("### ✏️ Update Completed Units / Confidence")
        names = st.session_state.subjects["subject"].tolist()
        selected = st.selectbox("Select Subject",names)
        idx = st.session_state.subjects.index[st.session_state.subjects["subject"]==selected][0]
        row = st.session_state.subjects.loc[idx]

        c1,c2,c3 = st.columns(3)
        new_completed = c1.number_input("Completed Units",0,int(row["units"]),int(row["completed_units"]),key="upd_completed")
        new_conf = c2.slider("Confidence",1,5,int(row["confidence"]),key="upd_conf")
        new_diff = c3.selectbox("Difficulty",list(DIFFICULTY.keys()),index=list(DIFFICULTY.keys()).index(row["difficulty"]),key="upd_diff")

        if st.button("💾 Update Subject"):
            st.session_state.subjects.loc[idx,"completed_units"] = new_completed
            st.session_state.subjects.loc[idx,"confidence"] = new_conf
            st.session_state.subjects.loc[idx,"difficulty"] = new_diff
            save_all()
            st.success("Updated!")
            st.rerun()

        if st.button("🗑️ Delete Selected Subject"):
            st.session_state.subjects = st.session_state.subjects.drop(idx).reset_index(drop=True)
            save_all()
            st.success("Deleted.")
            st.rerun()

    st.markdown("---")
    st.subheader("📅 Add Exam")
    with st.form("exam_form",clear_on_submit=True):
        if st.session_state.subjects.empty:
            st.info("Add a subject first.")
        else:
            exam_name = st.text_input("Exam Name")
            exam_subject = st.selectbox("Subject",st.session_state.subjects["subject"].tolist())
            exam_day = st.date_input("Exam Date",date.today()+timedelta(days=14),key="exam_day")
            if st.form_submit_button("➕ Add Exam"):
                new = pd.DataFrame([{"exam_name":exam_name or "Semester Exam","subject":exam_subject,"exam_date":pd.Timestamp(exam_day)}])
                st.session_state.exams = pd.concat([st.session_state.exams,new],ignore_index=True)
                save_all()
                st.success("Exam added!")

# ================= STUDY SESSION ==========================
elif page == "⏱️ Study Session":
    st.markdown('<div class="main-title">⏱️ Study Session</div>',unsafe_allow_html=True)

    if st.session_state.study_running:
        remaining = max(0,(st.session_state.study_end-datetime.now()).total_seconds())
        if remaining <= 0:
            st.session_state.study_running = False
            st.success("🎉 Session completed!")
            st.rerun()

        mins = int(remaining//60)
        secs = int(remaining%60)
        st.markdown(f"<div class='study-timer'>{mins:02d}:{secs:02d}</div>",unsafe_allow_html=True)
        st.info(f"📚 {st.session_state.current_subject} — {st.session_state.current_topic}")

        if st.button("⏹️ Finish Session"):
            duration = st.session_state.study_duration
            with st.form("session_complete"):
                technique = st.selectbox("Technique",TECHNIQUES)
                mood = st.selectbox("Mood",["😄 Great","🙂 Good","😐 Okay","😓 Tired","😴 Very tired"])
                distractions = st.slider("Distractions",0,5,1)
                productivity = st.slider("Productivity",1,5,4)
                submit = st.form_submit_button("Save Session")
                if submit:
                    new = pd.DataFrame([{
                        "date":pd.Timestamp.now(),
                        "subject":st.session_state.current_subject,
                        "topic":st.session_state.current_topic,
                        "duration_min":duration,
                        "technique":technique,
                        "mood":mood,
                        "distractions":distractions,
                        "productivity":productivity,
                        "quiz_score":None
                    }])
                    st.session_state.sessions = pd.concat([st.session_state.sessions,new],ignore_index=True)
                    st.session_state.study_running=False
                    save_all()
                    st.success("Session saved!")
                    st.rerun()

        st.markdown("Refresh the page to update the timer.")
    else:
        st.subheader("🚀 Start a Session")
        if st.session_state.subjects.empty:
            st.warning("Add subjects first.")
        else:
            subject = st.selectbox("Subject",st.session_state.subjects["subject"].tolist())
            topic = st.text_input("Topic",get_topic_for_subject(subject))
            duration = st.select_slider("Duration (minutes)",options=[15,25,30,45,60,90,120],value=45)
            if st.button("▶️ Start Study",type="primary"):
                st.session_state.current_subject=subject
                st.session_state.current_topic=topic
                st.session_state.study_duration=duration
                st.session_state.study_start=datetime.now()
                st.session_state.study_end=datetime.now()+timedelta(minutes=duration)
                st.session_state.study_running=True
                st.rerun()

# ================= QUIZ ===================================
elif page == "📝 Quiz":
    st.markdown('<div class="main-title">📝 MindMate Quiz</div>',unsafe_allow_html=True)

    if st.session_state.subjects.empty:
        st.warning("Add subjects first.")
    else:
        subjects_list=st.session_state.subjects["subject"].tolist()

        if not st.session_state.quiz_questions:
            subject=st.selectbox("Subject",subjects_list)
            topic=st.text_input("Topic",get_topic_for_subject(subject))
            if st.button("🎯 Start 5 Question Quiz",type="primary"):
                st.session_state.quiz_subject=subject
                st.session_state.quiz_topic=topic
                st.session_state.quiz_questions=available_questions(subject)
                st.session_state.quiz_answers={}
                st.session_state.quiz_submitted=False
                st.session_state.current_attempt_id=generate_attempt_id(subject,topic)
                st.rerun()
        else:
            st.info(f"Quiz: {st.session_state.quiz_subject} — {st.session_state.quiz_topic}")
            for i,(question,options,correct) in enumerate(st.session_state.quiz_questions):
                answer=st.radio(question,options,key=f"q_{i}")
                st.session_state.quiz_answers[i]=options.index(answer)

            if st.button("✅ Submit Quiz",type="primary"):
                score=0
                for i,(_,_,correct) in enumerate(st.session_state.quiz_questions):
                    if st.session_state.quiz_answers.get(i)==correct:
                        score+=1
                percent=score/len(st.session_state.quiz_questions)*100

                new=pd.DataFrame([{
                    "date":pd.Timestamp.now(),
                    "subject":st.session_state.quiz_subject,
                    "topic":st.session_state.quiz_topic,
                    "score":percent,
                    "questions":len(st.session_state.quiz_questions),
                    "attempt_id":st.session_state.current_attempt_id
                }])
                st.session_state.quiz_results=pd.concat([st.session_state.quiz_results,new],ignore_index=True)

                attempt=pd.DataFrame([{
                    "attempt_id":st.session_state.current_attempt_id,
                    "subject":st.session_state.quiz_subject,
                    "topic":st.session_state.quiz_topic,
                    "attempt_time":pd.Timestamp.now(),
                    "question_hash":hashlib.md5(str(st.session_state.quiz_questions).encode()).hexdigest(),
                    "completed":True
                }])
                st.session_state.quiz_attempts=pd.concat([st.session_state.quiz_attempts,attempt],ignore_index=True)
                save_all()

                st.success(f"🎉 Score: {score}/{len(st.session_state.quiz_questions)} ({percent:.0f}%)")

                for i,(question,options,correct) in enumerate(st.session_state.quiz_questions):
                    if st.session_state.quiz_answers.get(i)==correct:
                        st.write(f"✅ Q{i+1}: Correct")
                    else:
                        st.write(f"❌ Q{i+1}: Correct answer — **{options[correct]}**")

                st.session_state.quiz_questions=[]
                st.session_state.quiz_answers={}

# ================= CODING =================================
elif page == "💻 Coding Tracker":
    st.markdown('<div class="main-title">💻 Coding Tracker</div>',unsafe_allow_html=True)

    with st.form("coding_form",clear_on_submit=True):
        c1,c2=st.columns(2)
        with c1:
            problem_id=st.text_input("Problem ID / Number")
            name=st.text_input("Problem Name")
            platform=st.selectbox("Platform",CODING_PLATFORMS)
            difficulty=st.selectbox("Difficulty",CODING_DIFFICULTIES)
        with c2:
            topic=st.text_input("Topic","Arrays")
            language=st.selectbox("Language",CODING_LANGUAGES)
            time_taken=st.number_input("Time Taken (minutes)",1,500,30)
            score=st.slider("Self Score (%)",0,100,80)

        if st.form_submit_button("➕ Add Problem",type="primary"):
            new=pd.DataFrame([{
                "problem_id":problem_id,
                "platform":platform,
                "problem_name":name or "Unnamed Problem",
                "difficulty":difficulty,
                "topic":topic,
                "date_solved":pd.Timestamp.now(),
                "time_taken":time_taken,
                "language":language,
                "score":score
            }])
            st.session_state.coding_problems=pd.concat([st.session_state.coding_problems,new],ignore_index=True)
            save_all()
            st.success("Coding problem added!")

    cp=st.session_state.coding_problems
    if cp.empty:
        st.info("No coding problems yet.")
    else:
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total",len(cp))
        c2.metric("Easy",len(cp[cp["difficulty"]=="Easy"]))
        c3.metric("Medium",len(cp[cp["difficulty"]=="Medium"]))
        c4.metric("Hard",len(cp[cp["difficulty"]=="Hard"]))

        a,b=st.columns(2)
        with a:
            p=cp["platform"].value_counts().reset_index()
            p.columns=["Platform","Problems"]
            st.plotly_chart(px.bar(p,x="Platform",y="Problems",title="Problems by Platform"),use_container_width=True)
        with b:
            d=cp["difficulty"].value_counts().reset_index()
            d.columns=["Difficulty","Problems"]
            st.plotly_chart(px.pie(d,names="Difficulty",values="Problems",title="Difficulty Distribution"),use_container_width=True)

        st.dataframe(cp.sort_values("date_solved",ascending=False),use_container_width=True,hide_index=True)

# ================= TIMETABLE ==============================
elif page == "📅 Timetable":
    st.markdown('<div class="main-title">📅 Timetable</div>',unsafe_allow_html=True)

    with st.form("time_form",clear_on_submit=True):
        day=st.selectbox("Day",["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"])
        c1,c2=st.columns(2)
        start=c1.time_input("Start Time")
        end=c2.time_input("End Time")
        subject=st.selectbox("Subject",st.session_state.subjects["subject"].tolist() if not st.session_state.subjects.empty else ["General"])
        if st.form_submit_button("➕ Add Slot"):
            new=pd.DataFrame([{"day":day,"start":str(start),"end":str(end),"subject":subject}])
            st.session_state.timetable=pd.concat([st.session_state.timetable,new],ignore_index=True)
            save_all()
            st.success("Timetable slot added!")

    if st.session_state.timetable.empty:
        st.info("No timetable slots.")
    else:
        st.dataframe(st.session_state.timetable,use_container_width=True,hide_index=True)

# ================= ANALYTICS ==============================
elif page == "📊 Analytics":
    st.markdown('<div class="main-title">📊 Analytics</div>',unsafe_allow_html=True)

    s=st.session_state.sessions
    q=st.session_state.quiz_results
    c=st.session_state.coding_problems
    sub=st.session_state.subjects

    if sub.empty:
        st.info("Add subjects and activity first.")
    else:
        if not s.empty:
            a,b=st.columns(2)
            with a:
                x=s.copy()
                x["date"]=pd.to_datetime(x["date"]).dt.date
                daily=x.groupby("date",as_index=False)["duration_min"].sum()
                st.plotly_chart(px.line(daily,x="date",y="duration_min",markers=True,title="Study Trend"),use_container_width=True)
            with b:
                bysub=s.groupby("subject",as_index=False)["duration_min"].sum()
                st.plotly_chart(px.pie(bysub,names="subject",values="duration_min",hole=.3,title="Study Time by Subject"),use_container_width=True)

        if not q.empty:
            st.subheader("📝 Quiz Analytics")
            qq=q.groupby("subject",as_index=False)["score"].mean()
            st.plotly_chart(px.bar(qq,x="subject",y="score",range_y=[0,100],text_auto=".0f",title="Average Quiz Score"),use_container_width=True)

        if not c.empty:
            st.subheader("💻 Coding Analytics")
            cc=c.groupby("language").size().reset_index(name="Problems")
            st.plotly_chart(px.bar(cc,x="language",y="Problems",title="Languages Used"),use_container_width=True)

        st.subheader("🎯 Subject Health")
        health=[]
        for _,r in sub.iterrows():
            qs=q[q["subject"].astype(str).str.lower()==str(r["subject"]).lower()] if not q.empty else pd.DataFrame()
            avg=qs["score"].mean() if not qs.empty else None
            health.append({
                "Subject":r["subject"],
                "Confidence":f"{r['confidence']}/5",
                "Syllabus":f"{int(r['completed_units'])}/{int(r['units'])}",
                "Quiz":f"{avg:.0f}%" if avg is not None else "No quiz",
                "Priority":round(calculate_priority(r),1)
            })
        st.dataframe(pd.DataFrame(health).sort_values("Priority",ascending=False),use_container_width=True,hide_index=True)
