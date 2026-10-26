import streamlit as st
from google import genai
from datetime import date, datetime
import json
import os
import database

# ================= Database & Page Config =================
database.init_db()

st.set_page_config(page_title="AI Study Planner - Agentic Edition", page_icon="🎓", layout="wide")

if "pwa_loaded" not in st.session_state:
    st.session_state.pwa_loaded = True

    st.markdown("""
    <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/static/sw.js');
    }
    </script>
    """, unsafe_allow_html=True)

st.title("AI Study Planner with Exam Prediction - Agentic Edition")
st.caption("Tutor Agent | Memory Agent | Evaluator Agent | Adaptive Engine - Powered by Google Gemini & SQLite Backend")

MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")

# ================= Helpers =================
def load_env_key():
    try:
        if "GEMINI_API_KEY" in os.environ:
            return os.environ["GEMINI_API_KEY"]
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""

def clean_key(raw):
    if not raw:
        return ""
    return str(raw).strip().strip('"').strip("'").strip()

def extract_json_block(text):
    """Safely extracts JSON array or object text from model response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start_bracket = text.find("[")
    end_bracket = text.rfind("]")
    if start_bracket != -1 and end_bracket != -1 and end_bracket > start_bracket:
        text = text[start_bracket:end_bracket + 1]
    return text

def friendly_error(e):
    msg = str(e)
    if "401" in msg or "UNAUTHENTICATED" in msg or "API_KEY_INVALID" in msg or "API key not valid" in msg:
        return ("Your API key was rejected. Create a fresh key at "
                "https://aistudio.google.com/apikey and paste it in the sidebar.")
    if "429" in msg or "quota" in msg.lower() or "RESOURCE_EXHAUSTED" in msg:
        return "Free quota exceeded. Wait a minute and try again."
    if "404" in msg or "NOT_FOUND" in msg:
        return "Model unavailable. Pick a different model in the sidebar."
    if "Deadline" in msg or "timeout" in msg.lower():
        return "Network timeout. Check your internet."
    return f"Unexpected error: {e}"

@st.cache_data(ttl=300)
def fetch_available_models(api_key):
    try:
        c = genai.Client(api_key=api_key)
        ids = [m.name.replace("models/", "") for m in c.models.list()]
        models = sorted([m for m in ids if "gemini" in m.lower()])
        return models if models else ["gemini-2.5-flash", "gemini-1.5-flash"]
    except Exception:
        return ["gemini-2.5-flash", "gemini-1.5-flash"]

# ================= Tutor Agent =================
def tutor_reply(client, model, subject, topic, messages):
    history = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    prompt = f"""You are TutorAgent, a patient, friendly and expert AI tutor.
Subject: {subject}
Topic the student is learning: {topic}

Conversation so far:
{history}

Rules:
1. Explain concepts simply, step by step, with real-world examples.
2. Keep answers focused and under 250 words.
3. End every reply with one short check-in question to test understanding.
Now respond as TutorAgent."""
    return client.models.generate_content(model=model, contents=prompt).text

# ================= Evaluator Agent =================
def generate_quiz(client, model, subject, topic, n):
    prompt = f"""You are the Evaluator Agent. Create {n} multiple-choice questions on the topic "{topic}" (subject: {subject}).
Respond with ONLY a raw JSON array (no markdown fences, no explanation):
[{{"question": "question text", "options": ["A", "B", "C", "D"], "correct": 0, "tag": "subtopic"}}]
Rules: "correct" is the index (0-3) of the correct option. "tag" is the specific subtopic tested."""
    text = client.models.generate_content(model=model, contents=prompt).text.strip()
    clean_json = extract_json_block(text)
    return json.loads(clean_json)

def evaluate_quiz(client, model, subject, topic, quiz, answers):
    """Hybrid evaluation: deterministic scoring + AI feedback and weak-area detection."""
    lines = []
    correct_count = 0
    for i, q in enumerate(quiz):
        options = q.get("options", [])
        correct_val = q.get("correct", 0)

        # Determine correct answer text
        if isinstance(correct_val, int) and 0 <= correct_val < len(options):
            correct_text = options[correct_val]
        elif isinstance(correct_val, str) and correct_val.isdigit() and 0 <= int(correct_val) < len(options):
            correct_text = options[int(correct_val)]
        elif isinstance(correct_val, str) and correct_val in options:
            correct_text = correct_val
        else:
            correct_text = options[0] if options else str(correct_val)

        student_choice = answers[i] if i < len(answers) and answers[i] is not None else ""
        ok = (student_choice == correct_text)
        if ok:
            correct_count += 1
            mark = "Correct"
        else:
            mark = f"Wrong (correct answer: {correct_text})"

        lines.append(f"Q{i+1} [{q.get('tag', 'general')}]: student picked {student_choice} -> {mark}")

    pct = round(100 * correct_count / len(quiz)) if quiz else 0
    review = "\n".join(lines)
    prompt = f"""You are the Evaluator Agent. A student scored {pct}% on "{topic}" ({subject}).
Per-question review:
{review}

Respond in EXACTLY this format:
FEEDBACK: 2-3 sentences of constructive feedback.
WEAK: a JSON array of the subtopics the student should revise, e.g. ["Pointers", "Recursion"] (empty array if none)."""
    text = client.models.generate_content(model=model, contents=prompt).text.strip()
    feedback, weak = "Good effort!", []
    for line in text.splitlines():
        if line.startswith("FEEDBACK:"):
            feedback = line.replace("FEEDBACK:", "").strip()
        if line.startswith("WEAK:"):
            raw = line.replace("WEAK:", "").strip()
            try:
                clean_weak = extract_json_block(raw)
                weak = json.loads(clean_weak) if clean_weak else []
            except Exception:
                weak = []
    return pct, feedback, weak

# ================= Adaptive Engine =================
def adapt_plan(client, model, mem, subject, topics, exam_date, hours, level, days_left):
    """Adaptive Engine: rewrites the plan giving extra weight to weak areas from memory."""
    weak = ", ".join(mem.get("weak_topics", [])) or "no weak areas recorded yet"
    evs = mem.get("evaluations", [])
    history_lines = "\n".join(
        f"- {e['date']} | {e['topic']} | score {e['score_pct']}% | weak: {', '.join(e.get('weak_topics', [])) or 'none'}"
        for e in evs[-10:]
    ) or "- no evaluations yet"
    prompt = f"""You are the Adaptive Engine of an AI study planner.
Student profile:
- Subject: {subject}
- Full syllabus: {topics}
- Exam date: {exam_date} ({days_left} days left)
- Study hours per day: {hours}
- Preparation level: {level}

Memory Agent data:
- Known weak areas: {weak}
- Evaluation history:
{history_lines}

Task: create a REVISED day-by-day study plan that ADAPTS to the student's measured performance:
1. Give weak areas from memory significantly more time and repetition.
2. Reduce time on topics the student already scores well in.
3. Keep the same daily format:
### Day N - <theme>
- Study: <topics>
- Practice: <tasks>
- Self-test: <questions/task>
- Time split: Xh study / Yh practice
4. Start with a short "Why this plan changed" summary (2-3 lines).
5. End with one motivational tip.
Be specific and practical."""
    return client.models.generate_content(model=model, contents=prompt).text

# ================= Sidebar: Settings & Backend =================
st.sidebar.header("Settings")
env_key = clean_key(load_env_key())
default_val = "" if (not env_key or "PASTE_YOUR_API_KEY_HERE" in env_key or "your-full-key-here" in env_key) else env_key
raw_key = st.sidebar.text_input("Gemini API Key", value=default_val, type="password",
                                help="Get a free key at https://aistudio.google.com/apikey")
api_key = clean_key(raw_key)

if api_key:
    st.sidebar.caption(f"Loaded key: {api_key[:4]}...{api_key[-4:]} ({len(api_key)} chars)")
    if st.sidebar.button("Test API Key", use_container_width=True):
        with st.sidebar.spinner("Testing..."):
            try:
                t = genai.Client(api_key=api_key)
                st.sidebar.success(f"Key works! {len(list(t.models.list()))} models available.")
            except Exception as e:
                st.sidebar.error(friendly_error(e))
    available = fetch_available_models(api_key)
    default_idx = next((i for i, m in enumerate(available) if "flash" in m), 0)
    model_name = st.sidebar.selectbox("Model", available, index=default_idx)
else:
    model_name = None

st.sidebar.markdown("---")
st.sidebar.subheader("👤 Student Account & Backend")
st.sidebar.caption("🟢 Backend: SQLite (`study_planner.db`)")

all_students = database.list_all_usernames()
if "current_username" not in st.session_state:
    st.session_state.current_username = all_students[0] if all_students else "default_student"

curr_idx = all_students.index(st.session_state.current_username) if st.session_state.current_username in all_students else 0
selected_student = st.sidebar.selectbox("Active Student Profile", all_students, index=curr_idx)
if selected_student != st.session_state.current_username:
    st.session_state.current_username = selected_student
    st.rerun()

current_user = database.get_or_create_user(st.session_state.current_username)
database.migrate_legacy_memory(current_user.id, MEMORY_FILE)

with st.sidebar.expander("➕ Create New Student"):
    new_student_name = st.text_input("New Student Name", placeholder="e.g. Maria")
    if st.button("Add Student", use_container_width=True):
        if new_student_name.strip():
            database.get_or_create_user(new_student_name.strip())
            st.session_state.current_username = new_student_name.strip()
            st.sidebar.success(f"Created '{new_student_name.strip()}'!")
            st.rerun()

# ================= Memory Agent Status =================
st.sidebar.markdown("---")
st.sidebar.subheader("🧠 Memory Agent")
user_evals = database.get_user_evaluations(current_user.id)
weak_topics = database.get_user_weak_topics(current_user.id)
a_score = database.get_user_average_score(current_user.id)
saved_plans = database.get_saved_plans(current_user.id)

st.sidebar.caption(f"Quizzes taken: {len(user_evals)}")
st.sidebar.caption(f"Average score: {a_score if a_score is not None else 'N/A'}%")
st.sidebar.caption("Weak areas: " + (", ".join(weak_topics) if weak_topics else "none yet"))
st.sidebar.caption(f"Saved plans: {len(saved_plans)}")

if user_evals:
    with st.sidebar.expander("📋 Quiz History"):
        for ev in reversed(user_evals[-5:]):
            st.caption(f"**{ev['date']}** | {ev['topic']} | Score: **{ev['score_pct']}%**")
            if ev.get("weak_topics"):
                st.caption(f"  └ Needs review: {', '.join(ev['weak_topics'])}")

if st.sidebar.button("Clear Student Memory", use_container_width=True):
    database.clear_user_memory(current_user.id)
    st.session_state.clear()
    st.sidebar.success("Database memory cleared.")
    st.rerun()

if not api_key:
    st.warning("Please enter your Gemini API key in the sidebar to continue.")
    st.stop()

client = genai.Client(api_key=api_key)

# Build compatibility memory dict for agents
mem = {
    "profile": database.get_profile_data(current_user.id),
    "evaluations": user_evals,
    "weak_topics": weak_topics,
    "plans_generated": len(saved_plans),
}

# Pre-populate form with saved profile
saved_prof = mem["profile"]
default_subj = saved_prof.get("subject", "")
default_topics = saved_prof.get("topics", "")
default_hours = saved_prof.get("hours", 3)
try:
    default_exam_date = datetime.strptime(saved_prof.get("exam_date", str(date.today())), "%Y-%m-%d").date()
    if default_exam_date < date.today():
        default_exam_date = date.today()
except Exception:
    default_exam_date = date.today()

level_options = ["Just started", "Halfway done", "Almost done", "Only revision left"]
saved_level = saved_prof.get("level", "Just started")
default_level_idx = level_options.index(saved_level) if saved_level in level_options else 0

style_options = ["Balanced (mix of everything)", "Theory first", "Practice problems", "Visual / diagrams"]
saved_style = saved_prof.get("style", "Balanced (mix of everything)")
default_style_idx = style_options.index(saved_style) if saved_style in style_options else 0

diff_options = ["Easy", "Moderate", "Hard", "Very Hard"]
saved_diff = saved_prof.get("difficulty", "Moderate")
default_diff_idx = diff_options.index(saved_diff) if saved_diff in diff_options else 1

# ================= Main Input Form =================
with st.form("study_form"):
    col1, col2 = st.columns(2)
    with col1:
        subject = st.text_input("Subject", value=default_subj, placeholder="e.g. Data Structures")
        exam_date = st.date_input("Exam Date", value=default_exam_date)
        hours_per_day = st.slider("Study hours available per day", 1, 12, value=default_hours)
    with col2:
        level = st.selectbox("Current preparation level", level_options, index=default_level_idx)
        style = st.selectbox("Learning style", style_options, index=default_style_idx)
        difficulty = st.selectbox("Exam difficulty", diff_options, index=default_diff_idx)
    topics = st.text_area("Syllabus / Topics",
                          value=default_topics,
                          placeholder="e.g. Arrays, Linked Lists, Trees, Graphs...",
                          height=100)
    submitted = st.form_submit_button("Save Profile to Database", use_container_width=True)

if submitted and subject and topics:
    database.save_profile_data(
        user_id=current_user.id,
        subject=subject,
        topics=topics,
        exam_date=str(exam_date),
        hours=hours_per_day,
        level=level,
        style=style,
        difficulty=difficulty
    )
    st.success(f"Profile saved to database for student '{current_user.username}'!")
    mem["profile"] = database.get_profile_data(current_user.id)

days_left = (exam_date - date.today()).days

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Study Plan", "Exam Prediction", "Tutor Agent", "Quiz + Evaluator", "Adaptive Engine"])

# ================= Tab 1: Study Plan =================
with tab1:
    if st.button("Generate My Study Plan", use_container_width=True, key="plan_btn"):
        if days_left < 1:
            st.error("Exam date must be in the future!")
        elif not (subject and topics):
            st.error("Fill in Subject and Syllabus above and click Save Profile first.")
        else:
            prompt = f"""You are an expert academic study planner.
Create a detailed DAY-BY-DAY study plan:
- Subject: {subject}
- Syllabus/Topics: {topics}
- Exam date: {exam_date} ({days_left} days left)
- Daily hours: {hours_per_day}
- Level: {level} | Style: {style} | Difficulty: {difficulty}
Format each day as:
### Day N - <theme>
- Study: <topics>
- Practice: <tasks>
- Self-test: <questions/task>
- Time split: Xh study / Yh practice
End with a 2-3 day revision + mock test block and one motivational tip."""
            with st.spinner("Building your plan..."):
                try:
                    plan = client.models.generate_content(model=model_name, contents=prompt).text
                    database.save_study_plan_record(current_user.id, subject, "standard", plan)
                    st.success("Your study plan is ready and saved to database!")
                    st.markdown(plan)
                    st.download_button("Download Plan", plan,
                                       file_name=f"study_plan_{subject.replace(' ', '_')}.md",
                                       mime="text/markdown")
                except Exception as e:
                    st.error(friendly_error(e))

    saved_std_plans = database.get_saved_plans(current_user.id, plan_type="standard")
    if saved_std_plans:
        with st.expander(f"📚 Saved Study Plans History ({len(saved_std_plans)})"):
            for idx, p in enumerate(saved_std_plans):
                st.markdown(f"**Plan #{idx+1} - {p['subject']}** *(Created: {p['created_at']})*")
                preview = p['content'][:300] + "..." if len(p['content']) > 300 else p['content']
                st.markdown(preview)
                st.download_button(f"Download Full Plan #{idx+1}", p['content'],
                                   file_name=f"plan_{idx+1}_{p['subject']}.md",
                                   key=f"dl_std_{p['id']}")
                st.markdown("---")

# ================= Tab 2: Exam Prediction =================
with tab2:
    if not (subject and topics):
        st.info("Fill in Subject and Syllabus above and click Save Profile first.")
    else:
        past_papers = st.text_area("Optional: paste past paper questions",
                                   placeholder="Paste previous year questions here...", height=80)
        if st.button("Predict My Exam", use_container_width=True, key="pred_btn"):
            current_weaks = database.get_user_weak_topics(current_user.id)
            prompt = f"""You are an exam prediction expert.
Subject: {subject} | Syllabus: {topics} | Level: {level} | Difficulty: {difficulty} | Days left: {days_left}
{f"Past papers: {past_papers}" if past_papers.strip() else ""}
Known weak areas from memory: {', '.join(current_weaks) or 'none'}
Respond in EXACTLY this format:
## Most Likely Exam Topics
Table: | Rank | Topic | Probability (%) | Why likely |
## 5 Predicted Questions
## Predicted Score Range
- If preparation continues: X-Y%
- If weak areas are fixed: A-B%
## Weak-Area Alert
## Question Pattern Guess"""
            with st.spinner("Predicting your exam..."):
                try:
                    prediction = client.models.generate_content(model=model_name, contents=prompt).text
                    database.save_study_plan_record(current_user.id, subject, "prediction", prediction)
                    st.success("Prediction complete and stored!")
                    st.markdown(prediction)
                    st.download_button("Download Prediction", prediction,
                                       file_name=f"prediction_{subject.replace(' ', '_')}.md",
                                       mime="text/markdown")
                except Exception as e:
                    st.error(friendly_error(e))

# ================= Tab 3: Tutor Agent =================
with tab3:
    subj_t = subject or mem["profile"].get("subject", "")
    topic_t = st.text_input("Topic you want to learn", placeholder="e.g. Recursion in Trees",
                            key="tutor_topic")
    if "tutor_msgs" not in st.session_state:
        st.session_state.tutor_msgs = []
    for m in st.session_state.tutor_msgs:
        with st.chat_message(m["role"]):
            st.write(m["content"])
    user_q = st.chat_input("Ask your tutor anything about this topic...")
    if user_q:
        if not topic_t:
            st.warning("Please type the topic first.")
        else:
            st.session_state.tutor_msgs.append({"role": "user", "content": user_q})
            with st.spinner("Tutor Agent is thinking..."):
                try:
                    reply = tutor_reply(client, model_name, subj_t, topic_t, st.session_state.tutor_msgs)
                    st.session_state.tutor_msgs.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.error(friendly_error(e))
            st.rerun()
    if st.button("Reset Tutor Chat"):
        st.session_state.tutor_msgs = []
        st.rerun()

# ================= Tab 4: Quiz + Evaluator Agent =================
with tab4:
    subj_q = subject or mem["profile"].get("subject", "")
    topic_q = st.text_input("Topic for quiz", placeholder="e.g. Arrays", key="quiz_topic")
    n_q = st.slider("Number of questions", 3, 10, 5)
    if st.button("Generate Quiz"):
        if not topic_q:
            st.warning("Enter a topic first.")
        else:
            with st.spinner("Evaluator Agent is creating questions..."):
                try:
                    st.session_state.quiz = generate_quiz(client, model_name, subj_q, topic_q, n_q)
                    st.session_state.pop("quiz_result", None)
                except Exception as e:
                    st.error(friendly_error(e))
    if "quiz" in st.session_state:
        quiz = st.session_state.quiz
        st.markdown(f"**Quiz on: {topic_q}**")
        answers = []
        for i, q in enumerate(quiz):
            st.write(f"**Q{i+1}.** {q['question']}")
            answers.append(st.radio("Choose an answer:", q["options"], key=f"quiz_q{i}", index=None))
        if st.button("Submit Answers", key="submit_quiz"):
            if any(a is None for a in answers):
                st.warning("Answer all questions before submitting.")
            else:
                with st.spinner("Evaluator Agent is grading..."):
                    try:
                        pct, feedback, weak = evaluate_quiz(client, model_name, subj_q, topic_q, quiz, answers)
                        # Save evaluation into database
                        database.record_evaluation(current_user.id, subj_q, topic_q, pct, weak, feedback)
                        st.session_state.quiz_result = {"pct": pct, "feedback": feedback, "weak": weak}
                    except Exception as e:
                        st.error(friendly_error(e))
    if "quiz_result" in st.session_state:
        r = st.session_state.quiz_result
        st.success(f"Score: {r['pct']}% (Saved to Database)")
        st.write("**Feedback:** " + r["feedback"])
        st.write("**Weak areas detected:** " + (", ".join(r["weak"]) if r["weak"] else "none, great job!"))
        st.info("The Adaptive Engine can now use this result to fix your plan. Check the last tab.")
        if st.button("Take New Quiz"):
            st.session_state.pop("quiz", None)
            st.session_state.pop("quiz_result", None)
            st.rerun()

# ================= Tab 5: Adaptive Engine =================
with tab5:
    st.subheader("Adaptive Engine - Plan That Reacts to Your Performance")
    prof = database.get_profile_data(current_user.id)
    use_saved = st.checkbox("Use saved profile", value=bool(prof.get("subject") or prof.get("topics")))
    if use_saved and prof:
        a_subj = prof.get("subject") or subject
        a_topics = prof.get("topics") or topics
        try:
            a_date = datetime.strptime(prof.get("exam_date", str(date.today())), "%Y-%m-%d").date()
        except Exception:
            a_date = exam_date
        a_hours = prof.get("hours", hours_per_day)
        a_level = prof.get("level", level)
    else:
        a_subj = subject
        a_topics = topics
        a_date = exam_date
        a_hours = hours_per_day
        a_level = level
    a_days = (a_date - date.today()).days
    current_weaks = database.get_user_weak_topics(current_user.id)
    st.caption(f"Days left: {a_days} | Weak areas in database: "
               + (", ".join(current_weaks) if current_weaks else "none yet"))
    if st.button("Adapt My Study Plan", use_container_width=True):
        if not (a_subj and a_topics):
            st.error("Fill in Subject and Syllabus first (or save a profile).")
        elif a_days < 1:
            st.error("Exam date must be in the future!")
        else:
            with st.spinner("Adaptive Engine is rewriting your plan..."):
                try:
                    new_plan = adapt_plan(client, model_name, mem, a_subj, a_topics,
                                          a_date, a_hours, a_level, a_days)
                    database.save_study_plan_record(current_user.id, a_subj, "adaptive", new_plan)
                    st.success("Adaptive plan generated and saved to database! Weak areas now get priority.")
                    st.markdown(new_plan)
                    st.download_button("Download Adaptive Plan", new_plan,
                                       file_name=f"adaptive_plan_{a_subj.replace(' ', '_')}.md",
                                       mime="text/markdown")
                except Exception as e:
                    st.error(friendly_error(e))

    saved_adapt_plans = database.get_saved_plans(current_user.id, plan_type="adaptive")
    if saved_adapt_plans:
        with st.expander(f"🔄 Saved Adaptive Plans History ({len(saved_adapt_plans)})"):
            for idx, p in enumerate(saved_adapt_plans):
                st.markdown(f"**Adaptive Plan #{idx+1} - {p['subject']}** *(Created: {p['created_at']})*")
                preview = p['content'][:300] + "..." if len(p['content']) > 300 else p['content']
                st.markdown(preview)
                st.download_button(f"Download Full Adaptive Plan #{idx+1}", p['content'],
                                   file_name=f"adaptive_plan_{idx+1}_{p['subject']}.md",
                                   key=f"dl_adapt_{p['id']}")
                st.markdown("---")

st.markdown("---")
st.caption("Agentic AI Study Planner | Tutor + Memory + Evaluator + Adaptive Engine | Streamlit + SQLite + FastAPI Backend")
