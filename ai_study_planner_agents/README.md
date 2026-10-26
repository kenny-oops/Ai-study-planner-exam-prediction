# AI Study Planner - Agentic Edition with Database & FastAPI Backend

### Architecture
- **Database Layer (`model.py`, `database.py`)**: Persistent SQLite database (`study_planner.db`) managed with SQLAlchemy 2.0. Stores user profiles, quiz evaluation histories, detected weak subtopics, and generated study plans.
- **REST API Backend (`server.py`)**: FastAPI backend exposing endpoints for user profiles, quiz generation/evaluation, study plan management, and tutor chat.
- **Frontend App (`app.py`)**: Streamlit application with live database connectivity, student profile switching/creation, past quiz history expander, and study plan archive.

### Agents Included:
- **Tutor Agent**: Chat-based interactive teaching with check-in questions on any topic.
- **Memory Agent**: Database-backed memory tracking quizzes, weak subtopics, and student progress over time.
- **Evaluator Agent**: Generates tailored quizzes, grades answers, provides feedback, and flags weak subtopics.
- **Adaptive Engine**: Rewrites the study plan dynamically based on actual student weaknesses stored in the database.

### Installation & Running

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run the Streamlit App**:
```bash
streamlit run app.py
```

3. **(Optional) Run the FastAPI REST Backend**:
```bash
uvicorn server:app --reload --port 8000
```
API Documentation will be available at: `http://localhost:8000/docs`
