from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Course, Enrollment, Topic, User
from app.schemas.api import (
    AnalysisResponse, AnalysisTopicResponse, CourseResponse, GraphEdge, GraphNode, KnowledgeGraphResponse,
    LoginRequest, RecommendationResponse, RegisterRequest, SeedResponse, TokenResponse, TopicResponse, UserResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.mock_data_service import MockDataService

router = APIRouter(prefix="/api/v1")


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DBSession):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(email=str(payload.email), full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role.value)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DBSession):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/auth/me", response_model=UserResponse)
def me(user: CurrentUser):
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role.value)


@router.post("/mock-data/seed", response_model=SeedResponse)
def seed_mock_data(db: DBSession):
    course, student, created = MockDataService(db).seed()
    return SeedResponse(
        course_id=course.id,
        student_email=student.email,
        password="demo-password",
        message="Calculus mock data created." if created else "Calculus mock data already exists.",
    )


@router.get("/courses", response_model=list[CourseResponse])
def list_courses(user: CurrentUser, db: DBSession):
    courses = db.scalars(select(Course).join(Enrollment).where(Enrollment.student_id == user.id)).all()
    return [CourseResponse.model_validate(course) for course in courses]


@router.get("/courses/{course_id}/topics", response_model=list[TopicResponse])
def list_topics(course_id: str, user: CurrentUser, db: DBSession):
    _require_enrollment(course_id, user.id, db)
    return [TopicResponse.model_validate(topic) for topic in db.scalars(select(Topic).where(Topic.course_id == course_id).order_by(Topic.order_index)).all()]


@router.get("/courses/{course_id}/knowledge-graph", response_model=KnowledgeGraphResponse)
def knowledge_graph(course_id: str, user: CurrentUser, db: DBSession):
    _require_enrollment(course_id, user.id, db)
    topics = db.scalars(select(Topic).where(Topic.course_id == course_id).order_by(Topic.order_index)).all()
    return KnowledgeGraphResponse(
        nodes=[GraphNode(id=topic.id, title=topic.title, order_index=topic.order_index) for topic in topics],
        edges=[
            GraphEdge(from_topic_id=link.prerequisite_topic_id, to_topic_id=link.topic_id, required_mastery=link.required_mastery)
            for topic in topics for link in topic.prerequisites
        ],
    )


@router.post("/courses/{course_id}/analyses", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def analyze(course_id: str, user: CurrentUser, db: DBSession):
    _require_enrollment(course_id, user.id, db)
    return _analysis_response(AnalysisService(db).create_analysis(user.id, course_id))


@router.get("/courses/{course_id}/analyses/latest", response_model=AnalysisResponse)
def latest_analysis(course_id: str, user: CurrentUser, db: DBSession):
    _require_enrollment(course_id, user.id, db)
    analysis = AnalysisService(db).latest(course_id, user.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis has been run yet")
    return _analysis_response(analysis)


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: str, user: CurrentUser, db: DBSession):
    analysis = AnalysisService(db).get_analysis(analysis_id, user.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis was not found")
    return _analysis_response(analysis)


def _require_enrollment(course_id: str, student_id: str, db: DBSession) -> None:
    if not db.scalar(select(Enrollment.id).where(Enrollment.course_id == course_id, Enrollment.student_id == student_id)):
        raise HTTPException(status_code=404, detail="Course is not available to this student")


def _analysis_response(analysis) -> AnalysisResponse:
    topics = sorted(analysis.topic_results, key=lambda result: result.topic.order_index)
    recommendations = sorted(analysis.recommendations, key=lambda recommendation: recommendation.priority, reverse=True)
    return AnalysisResponse(
        id=analysis.id,
        course_id=analysis.course_id,
        overall_mastery=analysis.overall_mastery,
        analyzed_at=analysis.analyzed_at,
        engine_version=analysis.engine_version,
        ai_summary=analysis.ai_summary,
        topics=[AnalysisTopicResponse(
            topic_id=item.topic_id, topic_title=item.topic.title, mastery_score=item.mastery_score,
            confidence=item.confidence, state=item.state, evidence=item.evidence_json,
        ) for item in topics],
        recommendations=[RecommendationResponse(
            topic_id=item.topic_id, topic_title=item.topic.title, priority=item.priority,
            content=item.content, recommendation_type=item.recommendation_type,
        ) for item in recommendations],
    )
