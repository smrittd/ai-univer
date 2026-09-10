from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Assessment, AssessmentItem, Attempt, AttemptAnswer, Course, Enrollment, Topic, TopicPrerequisite, User


TOPICS = [
    ("limits", "Limits"),
    ("continuity", "Continuity"),
    ("function-composition", "Function Composition"),
    ("derivatives", "Derivatives"),
    ("product-rule", "Product Rule"),
    ("quotient-rule", "Quotient Rule"),
    ("chain-rule", "Chain Rule"),
    ("trigonometric-derivatives", "Trigonometric Derivatives"),
    ("integrals", "Integrals"),
    ("substitution", "Substitution"),
    ("integration-by-parts", "Integration by Parts"),
    ("fundamental-theorem", "Fundamental Theorem of Calculus"),
    ("optimization", "Optimization"),
    ("related-rates", "Related Rates"),
]

PREREQUISITES = [
    ("continuity", "limits"), ("derivatives", "continuity"),
    ("product-rule", "derivatives"), ("quotient-rule", "derivatives"),
    ("chain-rule", "derivatives"), ("chain-rule", "function-composition"),
    ("trigonometric-derivatives", "chain-rule"), ("integrals", "derivatives"),
    ("substitution", "integrals"), ("substitution", "function-composition"),
    ("integration-by-parts", "integrals"), ("fundamental-theorem", "integrals"),
    ("optimization", "derivatives"), ("related-rates", "chain-rule"),
]


class MockDataService:
    def __init__(self, db: Session):
        self.db = db

    def seed(self) -> tuple[Course, User, bool]:
        existing = self.db.scalar(select(Course).where(Course.code == "CALC-101"))
        if existing:
            student = self.db.scalar(select(User).where(User.email == "demo@example.com"))
            return existing, student, False

        course = Course(code="CALC-101", title="Calculus", description="Mock Calculus course for AI University MVP.")
        self.db.add(course)
        self.db.flush()
        topics: dict[str, Topic] = {}
        for index, (slug, title) in enumerate(TOPICS, start=1):
            topic = Topic(course_id=course.id, slug=slug, title=title, description=f"Calculus: {title}", order_index=index)
            self.db.add(topic)
            topics[slug] = topic
        self.db.flush()
        for child, parent in PREREQUISITES:
            self.db.add(TopicPrerequisite(topic_id=topics[child].id, prerequisite_topic_id=topics[parent].id, required_mastery=60))

        student = User(email="demo@example.com", full_name="Demo Student", password_hash=hash_password("demo-password"))
        self.db.add(student)
        self.db.flush()
        self.db.add(Enrollment(student_id=student.id, course_id=course.id))
        assessment = Assessment(course_id=course.id, title="Calculus diagnostic", assessment_type="diagnostic")
        self.db.add(assessment)
        self.db.flush()

        # 18 per topic gives the engine enough confidence to distinguish real gaps from sparse evidence.
        item_by_slug: dict[str, AssessmentItem] = {}
        for slug, topic in topics.items():
            item = AssessmentItem(
                assessment_id=assessment.id,
                topic_id=topic.id,
                prompt=f"Diagnostic problem for {topic.title}",
                difficulty=2,
                weight=1,
            )
            self.db.add(item)
            item_by_slug[slug] = item
        self.db.flush()

        # Deliberately representative profile: good foundations, composition/chain-rule gap, critical trig derivatives.
        correct_counts = {
            "limits": 17, "continuity": 16, "function-composition": 8, "derivatives": 15,
            "product-rule": 14, "quotient-rule": 13, "chain-rule": 9, "trigonometric-derivatives": 7,
            "integrals": 13, "substitution": 12, "integration-by-parts": 10,
            "fundamental-theorem": 14, "optimization": 11, "related-rates": 8,
        }
        now = datetime.now(UTC)
        for slug, correct_count in correct_counts.items():
            for index in range(18):
                attempt = Attempt(student_id=student.id, assessment_id=assessment.id, submitted_at=now - timedelta(days=(index % 6) + 1))
                self.db.add(attempt)
                self.db.flush()
                self.db.add(AttemptAnswer(
                    attempt_id=attempt.id,
                    assessment_item_id=item_by_slug[slug].id,
                    is_correct=index < correct_count,
                    score=1 if index < correct_count else 0,
                    answer_payload={"source": "mock-diagnostic"},
                ))
        self.db.commit()
        return course, student, True
