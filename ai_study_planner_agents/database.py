import os
import json
from contextlib import contextmanager
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model import Base, User, Profile, Evaluation, StudyPlan

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study_planner.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_FILE}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

def init_db():
    """Create all tables in the database if they don't already exist."""
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    """Provide a transactional database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# ================= CRUD Operations =================

def get_or_create_user(username: str = "default_student") -> User:
    """Fetch existing user or create a new user with default profile."""
    username = (username or "default_student").strip()
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username)
            db.add(user)
            db.flush()
            profile = Profile(user_id=user.id)
            db.add(profile)
            db.commit()
            db.refresh(user)
        return user

def list_all_usernames() -> list:
    """Return list of existing usernames."""
    with get_db() as db:
        users = db.query(User.username).order_by(User.username).all()
        names = [u[0] for u in users]
        return names if names else ["default_student"]

def get_profile_data(user_id: int) -> dict:
    """Retrieve student profile data as a clean dictionary."""
    with get_db() as db:
        p = db.query(Profile).filter(Profile.user_id == user_id).first()
        if not p:
            return {
                "subject": "",
                "topics": "",
                "exam_date": str(date.today()),
                "hours": 3,
                "level": "Just started",
                "style": "Balanced (mix of everything)",
                "difficulty": "Moderate",
            }
        return {
            "subject": p.subject or "",
            "topics": p.topics or "",
            "exam_date": p.exam_date or str(date.today()),
            "hours": p.hours or 3,
            "level": p.level or "Just started",
            "style": p.style or "Balanced (mix of everything)",
            "difficulty": p.difficulty or "Moderate",
        }

def save_profile_data(user_id: int, subject: str, topics: str, exam_date: str,
                      hours: int, level: str, style: str = "", difficulty: str = ""):
    """Save or update student profile in database."""
    with get_db() as db:
        p = db.query(Profile).filter(Profile.user_id == user_id).first()
        if not p:
            p = Profile(user_id=user_id)
            db.add(p)
        p.subject = subject or ""
        p.topics = topics or ""
        p.exam_date = str(exam_date)
        p.hours = int(hours)
        p.level = level or "Just started"
        if style:
            p.style = style
        if difficulty:
            p.difficulty = difficulty
        db.commit()

def record_evaluation(user_id: int, subject: str, topic: str, score_pct: float,
                      weak_topics: list, feedback: str = ""):
    """Record a quiz evaluation result in database."""
    with get_db() as db:
        ev = Evaluation(
            user_id=user_id,
            subject=subject,
            topic=topic,
            score_pct=score_pct,
            weak_topics=list(weak_topics or []),
            feedback=feedback or ""
        )
        db.add(ev)
        db.commit()

def get_user_evaluations(user_id: int, limit: int = 50) -> list:
    """Retrieve all evaluation records for a student."""
    with get_db() as db:
        evs = (db.query(Evaluation)
               .filter(Evaluation.user_id == user_id)
               .order_by(Evaluation.created_at.asc())
               .limit(limit)
               .all())
        return [
            {
                "id": e.id,
                "date": e.created_at.strftime("%Y-%m-%d") if e.created_at else str(date.today()),
                "subject": e.subject,
                "topic": e.topic,
                "score_pct": e.score_pct,
                "weak_topics": e.weak_topics or [],
                "feedback": e.feedback or "",
            }
            for e in evs
        ]

def get_user_weak_topics(user_id: int) -> list:
    """Aggregate all unique weak topics identified across evaluations."""
    evs = get_user_evaluations(user_id)
    weaks = []
    for e in evs:
        for w in e.get("weak_topics", []):
            if w and w not in weaks:
                weaks.append(w)
    return weaks

def get_user_average_score(user_id: int) -> int | None:
    """Calculate student average quiz score across all topics."""
    evs = get_user_evaluations(user_id)
    if not evs:
        return None
    return round(sum(e["score_pct"] for e in evs) / len(evs))

def save_study_plan_record(user_id: int, subject: str, plan_type: str, content: str):
    """Save generated study plan to database for future reference."""
    with get_db() as db:
        sp = StudyPlan(
            user_id=user_id,
            subject=subject or "",
            plan_type=plan_type,
            content=content
        )
        db.add(sp)
        db.commit()

def get_saved_plans(user_id: int, plan_type: str = None) -> list:
    """Retrieve saved study plans for user."""
    with get_db() as db:
        query = db.query(StudyPlan).filter(StudyPlan.user_id == user_id)
        if plan_type:
            query = query.filter(StudyPlan.plan_type == plan_type)
        plans = query.order_by(StudyPlan.created_at.desc()).all()
        return [
            {
                "id": p.id,
                "subject": p.subject,
                "plan_type": p.plan_type,
                "content": p.content,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else ""
            }
            for p in plans
        ]

def clear_user_memory(user_id: int):
    """Clear evaluations, weak areas, and saved plans for user."""
    with get_db() as db:
        db.query(Evaluation).filter(Evaluation.user_id == user_id).delete()
        db.query(StudyPlan).filter(StudyPlan.user_id == user_id).delete()
        db.commit()

def migrate_legacy_memory(user_id: int, memory_file_path: str):
    """Seamlessly import existing memory.json data into the database if empty."""
    if not os.path.exists(memory_file_path):
        return
    with get_db() as db:
        # Check if user already has data
        existing_evs = db.query(Evaluation).filter(Evaluation.user_id == user_id).count()
        if existing_evs > 0:
            return  # Already has data
        try:
            with open(memory_file_path, "r") as f:
                legacy = json.load(f)
            prof = legacy.get("profile", {})
            if prof and (prof.get("subject") or prof.get("topics")):
                save_profile_data(
                    user_id=user_id,
                    subject=prof.get("subject", ""),
                    topics=prof.get("topics", ""),
                    exam_date=prof.get("exam_date", str(date.today())),
                    hours=prof.get("hours", 3),
                    level=prof.get("level", "Just started"),
                )
            for ev in legacy.get("evaluations", []):
                record_evaluation(
                    user_id=user_id,
                    subject=ev.get("subject", ""),
                    topic=ev.get("topic", ""),
                    score_pct=ev.get("score_pct", 0),
                    weak_topics=ev.get("weak_topics", []),
                    feedback=ev.get("feedback", "")
                )
        except Exception:
            pass
