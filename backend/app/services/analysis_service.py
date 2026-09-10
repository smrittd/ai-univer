from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AnalysisRecommendation, Assessment, AssessmentItem, Attempt, AttemptAnswer, Course, KnowledgeAnalysis, Topic, TopicAnalysisResult
from app.services.ai_interpretation_service import AIInterpretationService
from app.services.knowledge_engine import AnswerEvidence, KnowledgeAnalysisEngine, TopicInput, TopicResult


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = KnowledgeAnalysisEngine()

    def create_analysis(self, student_id: str, course_id: str) -> KnowledgeAnalysis:
        course = self.db.scalar(
            select(Course).where(Course.id == course_id).options(selectinload(Course.topics).selectinload(Topic.prerequisites))
        )
        if not course:
            raise LookupError("Course was not found")
        answers_by_topic = self._answers_by_topic(student_id, course_id)
        dependent_counts = {topic.id: len(topic.dependent_links) for topic in course.topics}

        # Pass one measures direct performance. Pass two incorporates scores of declared prerequisites.
        first_pass = self.engine.analyze(
            [TopicInput(topic.id, topic.title, answers_by_topic[topic.id], [], dependent_counts[topic.id]) for topic in course.topics]
        )
        direct_scores = {result.topic_id: result.mastery_score for result in first_pass}
        final_inputs = []
        for topic in course.topics:
            prerequisites = [
                (link.prerequisite_topic_id, link.prerequisite.title, direct_scores[link.prerequisite_topic_id])
                for link in topic.prerequisites
            ]
            final_inputs.append(TopicInput(topic.id, topic.title, answers_by_topic[topic.id], prerequisites, dependent_counts[topic.id]))
        results = self.engine.analyze(final_inputs)
        overall_mastery = round(sum(result.mastery_score for result in results) / len(results), 2) if results else 0.0
        ai_summary = AIInterpretationService().interpret(course.title, overall_mastery, results)

        analysis = KnowledgeAnalysis(
            student_id=student_id,
            course_id=course_id,
            overall_mastery=overall_mastery,
            engine_version=self.engine.version,
            ai_summary=ai_summary,
        )
        self.db.add(analysis)
        self.db.flush()
        for result in results:
            self.db.add(TopicAnalysisResult(
                analysis_id=analysis.id,
                topic_id=result.topic_id,
                mastery_score=result.mastery_score,
                confidence=result.confidence,
                state=str(result.state),
                evidence_json=result.evidence,
            ))
        for result in sorted(results, key=lambda value: value.priority, reverse=True)[:5]:
            if result.mastery_score < 85:
                self.db.add(AnalysisRecommendation(
                    analysis_id=analysis.id,
                    topic_id=result.topic_id,
                    priority=result.priority,
                    content=self._recommendation(result),
                ))
        self.db.commit()
        return analysis

    def get_analysis(self, analysis_id: str, student_id: str) -> KnowledgeAnalysis | None:
        return self.db.scalar(
            select(KnowledgeAnalysis)
            .where(KnowledgeAnalysis.id == analysis_id, KnowledgeAnalysis.student_id == student_id)
            .options(
                selectinload(KnowledgeAnalysis.topic_results).selectinload(TopicAnalysisResult.topic),
                selectinload(KnowledgeAnalysis.recommendations).selectinload(AnalysisRecommendation.topic),
            )
        )

    def latest(self, course_id: str, student_id: str) -> KnowledgeAnalysis | None:
        analysis_id = self.db.scalar(
            select(KnowledgeAnalysis.id)
            .where(KnowledgeAnalysis.course_id == course_id, KnowledgeAnalysis.student_id == student_id)
            .order_by(KnowledgeAnalysis.analyzed_at.desc())
        )
        return self.get_analysis(analysis_id, student_id) if analysis_id else None

    def _answers_by_topic(self, student_id: str, course_id: str) -> dict[str, list[AnswerEvidence]]:
        rows = self.db.execute(
            select(AttemptAnswer, Topic.id)
            .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
            .join(AssessmentItem, AssessmentItem.id == AttemptAnswer.assessment_item_id)
            .join(Assessment, Assessment.id == AssessmentItem.assessment_id)
            .join(Topic, Topic.id == AssessmentItem.topic_id)
            .where(Attempt.student_id == student_id, Assessment.course_id == course_id)
        ).all()
        answer_map: dict[str, list[AnswerEvidence]] = defaultdict(list)
        for answer, topic_id in rows:
            item = answer.assessment_item
            answer_map[topic_id].append(AnswerEvidence(
                correct=answer.is_correct,
                weight=item.weight,
                difficulty=item.difficulty,
                submitted_at=answer.attempt.submitted_at or datetime.now(UTC),
            ))
        return answer_map

    @staticmethod
    def _recommendation(result: TopicResult) -> str:
        if result.evidence["weak_prerequisites"]:
            prerequisite = result.evidence["weak_prerequisites"][0]["topic"]
            return f"Review {prerequisite} before practising {result.title}."
        return f"Study {result.title} next; target at least 70% on a fresh practice set."
