from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(ORMModel):
    id: str
    email: str
    full_name: str
    role: str


class CourseResponse(ORMModel):
    id: str
    code: str
    title: str
    description: str


class TopicResponse(ORMModel):
    id: str
    slug: str
    title: str
    description: str
    order_index: int


class GraphNode(BaseModel):
    id: str
    title: str
    order_index: int


class GraphEdge(BaseModel):
    from_topic_id: str
    to_topic_id: str
    required_mastery: float


class KnowledgeGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class AnalysisTopicResponse(BaseModel):
    topic_id: str
    topic_title: str
    mastery_score: float
    confidence: float
    state: str
    evidence: dict[str, Any]


class RecommendationResponse(BaseModel):
    topic_id: str
    topic_title: str
    priority: float
    content: str
    recommendation_type: str


class AnalysisResponse(BaseModel):
    id: str
    course_id: str
    overall_mastery: float
    analyzed_at: datetime
    engine_version: str
    ai_summary: dict[str, Any] | None
    topics: list[AnalysisTopicResponse]
    recommendations: list[RecommendationResponse]


class SeedResponse(BaseModel):
    course_id: str
    student_email: str
    password: str
    message: str
