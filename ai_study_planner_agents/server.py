import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from google import genai
import database

# Initialize DB
database.init_db()

app = FastAPI(
    title="AI Study Planner Backend API",
    description="Agentic Study Planner backend powered by Google Gemini and SQLite/SQLAlchemy",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= Schemas =================
class UserCreate(BaseModel):
    username: str

class ProfileUpdate(BaseModel):
    subject: str = ""
    topics: str = ""
    exam_date: str = str(date.today())
    hours: int = 3
    level: str = "Just started"
    style: str = "Balanced (mix of everything)"
    difficulty: str = "Moderate"

class EvaluationCreate(BaseModel):
    subject: str
    topic: str
    score_pct: float
    weak_topics: List[str] = Field(default_factory=list)
    feedback: str = ""

class PlanCreate(BaseModel):
    subject: str
    plan_type: str = "standard"
    content: str

class TutorRequest(BaseModel):
    api_key: str
    model: str = "gemini-2.5-flash"
    subject: str
    topic: str
    messages: List[dict]  # [{"role": "user", "content": "..."}]

class QuizGenRequest(BaseModel):
    api_key: str
    model: str = "gemini-2.5-flash"
    subject: str
    topic: str
    num_questions: int = 5

class QuizEvalRequest(BaseModel):
    api_key: str
    model: str = "gemini-2.5-flash"
    subject: str
    topic: str
    quiz: List[dict]
    answers: List[Optional[str]]

class PlanGenRequest(BaseModel):
    api_key: str
    model: str = "gemini-2.5-flash"
    subject: str
    topics: str
    exam_date: str
    hours_per_day: int
    level: str
    style: str
    difficulty: str

class AdaptPlanRequest(BaseModel):
    api_key: str
    model: str = "gemini-2.5-flash"
    user_id: int
    subject: str
    topics: str
    exam_date: str
    hours_per_day: int
    level: str

class PredictExamRequest(BaseModel):
    api_key: str
    model: str = "gemini-2.5-flash"
    user_id: int
    subject: str
    topics: str
    level: str
    difficulty: str
    exam_date: str
    past_papers: str = ""

# ================= Routes: User & Profile =================
@app.get("/")
def root():
    return {"status": "ok", "message": "AI Study Planner Agentic Backend is running"}

@app.get("/api/users")
def get_users():
    return {"users": database.list_all_usernames()}

@app.post("/api/users")
def get_or_create_user(req: UserCreate):
    user = database.get_or_create_user(req.username)
    return {"id": user.id, "username": user.username}

@app.get("/api/profile/{user_id}")
def get_profile(user_id: int):
    return database.get_profile_data(user_id)

@app.post("/api/profile/{user_id}")
def update_profile(user_id: int, req: ProfileUpdate):
    database.save_profile_data(
        user_id=user_id,
        subject=req.subject,
        topics=req.topics,
        exam_date=req.exam_date,
        hours=req.hours,
        level=req.level,
        style=req.style,
        difficulty=req.difficulty
    )
    return {"status": "success", "profile": database.get_profile_data(user_id)}

# ================= Routes: Evaluations & Memory =================
@app.get("/api/memory/{user_id}")
def get_memory(user_id: int):
    return {
        "profile": database.get_profile_data(user_id),
        "evaluations": database.get_user_evaluations(user_id),
        "weak_topics": database.get_user_weak_topics(user_id),
        "average_score": database.get_user_average_score(user_id),
    }

@app.post("/api/evaluations/{user_id}")
def add_evaluation(user_id: int, req: EvaluationCreate):
    database.record_evaluation(
        user_id=user_id,
        subject=req.subject,
        topic=req.topic,
        score_pct=req.score_pct,
        weak_topics=req.weak_topics,
        feedback=req.feedback
    )
    return {"status": "success", "weak_topics": database.get_user_weak_topics(user_id)}

@app.delete("/api/memory/{user_id}")
def clear_memory(user_id: int):
    database.clear_user_memory(user_id)
    return {"status": "success", "message": "Memory cleared"}

# ================= Routes: Saved Plans =================
@app.get("/api/plans/{user_id}")
def list_plans(user_id: int, plan_type: Optional[str] = None):
    return {"plans": database.get_saved_plans(user_id, plan_type)}

@app.post("/api/plans/{user_id}")
def create_plan_record(user_id: int, req: PlanCreate):
    database.save_study_plan_record(
        user_id=user_id,
        subject=req.subject,
        plan_type=req.plan_type,
        content=req.content
    )
    return {"status": "success"}

# ================= Routes: Agent Services =================
def get_gemini_client(api_key: str) -> genai.Client:
    key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip().strip('"').strip("'")
    if not key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required")
    return genai.Client(api_key=key)

@app.post("/api/agent/tutor")
def tutor_chat(req: TutorRequest):
    client = get_gemini_client(req.api_key)
    history = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in req.messages])
    prompt = f"""You are TutorAgent, a patient, friendly and expert AI tutor.
Subject: {req.subject}
Topic the student is learning: {req.topic}

Conversation so far:
{history}

Rules:
1. Explain concepts simply, step by step, with real-world examples.
2. Keep answers focused and under 250 words.
3. End every reply with one short check-in question to test understanding.
Now respond as TutorAgent."""
    try:
        reply = client.models.generate_content(model=req.model, contents=prompt).text
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
