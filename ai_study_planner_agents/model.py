from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, DateTime, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, default="default_student")
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    
    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="user", cascade="all, delete-orphan")
    plans = relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    subject = Column(String, default="")
    topics = Column(Text, default="")
    exam_date = Column(String, default="")
    hours = Column(Integer, default=3)
    level = Column(String, default="Just started")
    style = Column(String, default="Balanced (mix of everything)")
    difficulty = Column(String, default="Moderate")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="profile")

class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    topic = Column(String)
    score_pct = Column(Float)
    weak_topics = Column(JSON, default=list)  # e.g. ["Recursion", "Pointers"]
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="evaluations")

class StudyPlan(Base):
    __tablename__ = "study_plans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    plan_type = Column(String, default="standard")  # "standard", "adaptive", "prediction"
    content = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="plans")
