import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def uuid_pk() -> Mapped[str]:
    return mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class UserRole(str, enum.Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class AnalysisStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.STUDENT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[str] = uuid_pk()
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    topics: Mapped[list["Topic"]] = relationship(back_populates="course", cascade="all, delete-orphan", order_by="Topic.order_index")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[str] = uuid_pk()
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer)
    course: Mapped[Course] = relationship(back_populates="topics")
    prerequisites: Mapped[list["TopicPrerequisite"]] = relationship(
        foreign_keys="TopicPrerequisite.topic_id", back_populates="topic", cascade="all, delete-orphan"
    )
    dependent_links: Mapped[list["TopicPrerequisite"]] = relationship(
        foreign_keys="TopicPrerequisite.prerequisite_topic_id", back_populates="prerequisite"
    )
    __table_args__ = (UniqueConstraint("course_id", "slug", name="uq_topic_course_slug"),)


class TopicPrerequisite(Base):
    __tablename__ = "topic_prerequisites"
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    prerequisite_topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    required_mastery: Mapped[float] = mapped_column(Float, default=60)
    topic: Mapped[Topic] = relationship(foreign_keys=[topic_id], back_populates="prerequisites")
    prerequisite: Mapped[Topic] = relationship(foreign_keys=[prerequisite_topic_id], back_populates="dependent_links")


class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[str] = uuid_pk()
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    student: Mapped[User] = relationship(back_populates="enrollments")
    course: Mapped[Course] = relationship()
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_student_course"),)


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[str] = uuid_pk()
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    assessment_type: Mapped[str] = mapped_column(String(40), default="quiz")
    max_score: Mapped[float] = mapped_column(Float, default=100)
    course: Mapped[Course] = relationship(back_populates="assessments")
    items: Mapped[list["AssessmentItem"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")


class AssessmentItem(Base):
    __tablename__ = "assessment_items"
    id: Mapped[str] = uuid_pk()
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    weight: Mapped[float] = mapped_column(Float, default=1)
    assessment: Mapped[Assessment] = relationship(back_populates="items")
    topic: Mapped[Topic] = relationship()


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[str] = uuid_pk()
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    score: Mapped[float] = mapped_column(Float, default=0)
    answers: Mapped[list["AttemptAnswer"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"
    id: Mapped[str] = uuid_pk()
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), index=True)
    assessment_item_id: Mapped[str] = mapped_column(ForeignKey("assessment_items.id", ondelete="CASCADE"), index=True)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float, default=0)
    answer_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    attempt: Mapped[Attempt] = relationship(back_populates="answers")
    assessment_item: Mapped[AssessmentItem] = relationship()


class StudentActivity(Base):
    __tablename__ = "student_activities"
    id: Mapped[str] = uuid_pk()
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[str | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    activity_type: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)


class KnowledgeAnalysis(Base):
    __tablename__ = "knowledge_analyses"
    id: Mapped[str] = uuid_pk()
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    status: Mapped[AnalysisStatus] = mapped_column(Enum(AnalysisStatus), default=AnalysisStatus.COMPLETED)
    overall_mastery: Mapped[float] = mapped_column(Float)
    engine_version: Mapped[str] = mapped_column(String(30), default="1.0")
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ai_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    topic_results: Mapped[list["TopicAnalysisResult"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    recommendations: Mapped[list["AnalysisRecommendation"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class TopicAnalysisResult(Base):
    __tablename__ = "topic_analysis_results"
    id: Mapped[str] = uuid_pk()
    analysis_id: Mapped[str] = mapped_column(ForeignKey("knowledge_analyses.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    mastery_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    state: Mapped[str] = mapped_column(String(50))
    evidence_json: Mapped[dict] = mapped_column(JSON)
    analysis: Mapped[KnowledgeAnalysis] = relationship(back_populates="topic_results")
    topic: Mapped[Topic] = relationship()
    __table_args__ = (UniqueConstraint("analysis_id", "topic_id", name="uq_analysis_topic"),)


class AnalysisRecommendation(Base):
    __tablename__ = "analysis_recommendations"
    id: Mapped[str] = uuid_pk()
    analysis_id: Mapped[str] = mapped_column(ForeignKey("knowledge_analyses.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    priority: Mapped[float] = mapped_column(Float)
    recommendation_type: Mapped[str] = mapped_column(String(40), default="study")
    content: Mapped[str] = mapped_column(Text)
    analysis: Mapped[KnowledgeAnalysis] = relationship(back_populates="recommendations")
    topic: Mapped[Topic] = relationship()
