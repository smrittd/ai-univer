"""Deterministic knowledge analysis. This module must never call an LLM."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import exp
from typing import Iterable


class KnowledgeState(StrEnum):
    NEVER_LEARNED = "NEVER_LEARNED"
    FORGOTTEN = "FORGOTTEN"
    PARTIALLY_UNDERSTOOD = "PARTIALLY_UNDERSTOOD"
    APPLICATION_PROBLEM = "APPLICATION_PROBLEM"
    MASTERED = "MASTERED"
    WEAK = "WEAK"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class AnswerEvidence:
    correct: bool
    weight: float
    difficulty: int
    submitted_at: datetime


@dataclass(frozen=True)
class TopicInput:
    topic_id: str
    title: str
    answers: list[AnswerEvidence]
    prerequisite_scores: list[tuple[str, str, float]]
    dependent_count: int


@dataclass(frozen=True)
class TopicResult:
    topic_id: str
    title: str
    mastery_score: float
    confidence: float
    state: KnowledgeState
    priority: float
    evidence: dict


class KnowledgeAnalysisEngine:
    """Versioned and transparent formula for a single course snapshot."""

    version = "1.0"

    def analyze(self, inputs: Iterable[TopicInput], now: datetime | None = None) -> list[TopicResult]:
        now = now or datetime.now(UTC)
        return [self._analyze_topic(topic, now) for topic in inputs]

    def _analyze_topic(self, topic: TopicInput, now: datetime) -> TopicResult:
        answers = topic.answers
        if not answers:
            return TopicResult(
                topic_id=topic.topic_id,
                title=topic.title,
                mastery_score=0.0,
                confidence=0.0,
                state=KnowledgeState.NEVER_LEARNED,
                priority=round(20 + topic.dependent_count * 10, 2),
                evidence={
                    "correct_attempts": 0,
                    "total_attempts": 0,
                    "reason": "No submitted answers exist for this topic.",
                    "prerequisites": self._prereq_evidence(topic),
                },
            )

        weighted_total = sum(max(answer.weight, 0.1) for answer in answers)
        weighted_correct = sum(max(answer.weight, 0.1) for answer in answers if answer.correct)
        accuracy = 100 * weighted_correct / weighted_total

        recency_weights = [max(answer.weight, 0.1) * exp(-self._days_old(answer.submitted_at, now) / 60) for answer in answers]
        recency_total = sum(recency_weights)
        recent_accuracy = 100 * sum(weight for answer, weight in zip(answers, recency_weights) if answer.correct) / recency_total

        # Coverage reaches 100 after ten evidence points; it prevents one correct answer being treated as mastery.
        coverage = min(100.0, len(answers) * 10.0)
        prereq_scores = [score for _, _, score in topic.prerequisite_scores]
        prerequisite_support = sum(prereq_scores) / len(prereq_scores) if prereq_scores else 100.0
        mastery = round(0.55 * accuracy + 0.25 * recent_accuracy + 0.10 * coverage + 0.10 * prerequisite_support, 2)
        confidence = round(min(100.0, 8 * len(answers) + 0.2 * coverage + 0.2 * min(100, recency_total * 25)), 2)

        recent_answers = [answer for answer in answers if self._days_old(answer.submitted_at, now) <= 30]
        recent_mistakes = sum(not answer.correct for answer in recent_answers)
        easy_answers = [answer for answer in answers if answer.difficulty <= 2]
        hard_answers = [answer for answer in answers if answer.difficulty >= 3]
        easy_accuracy = self._accuracy(easy_answers)
        hard_accuracy = self._accuracy(hard_answers)
        older_answers = [answer for answer in answers if self._days_old(answer.submitted_at, now) > 45]
        old_accuracy = self._accuracy(older_answers)
        weak_prereqs = [(pid, title, score) for pid, title, score in topic.prerequisite_scores if score < 60]

        forgotten = old_accuracy is not None and recent_answers and old_accuracy >= 80 and recent_accuracy <= 55
        application_problem = easy_accuracy is not None and hard_accuracy is not None and easy_accuracy >= 75 and hard_accuracy < 50
        state = self._state(mastery, confidence, forgotten, application_problem)
        priority = self._priority(mastery, confidence, topic.dependent_count, weak_prereqs)
        evidence = {
            "correct_attempts": sum(answer.correct for answer in answers),
            "total_attempts": len(answers),
            "weighted_accuracy": round(accuracy, 2),
            "recent_accuracy": round(recent_accuracy, 2),
            "coverage": round(coverage, 2),
            "recent_mistakes": recent_mistakes,
            "days_since_last_activity": round(min(self._days_old(answer.submitted_at, now) for answer in answers), 1),
            "prerequisite_support": round(prerequisite_support, 2),
            "prerequisites": self._prereq_evidence(topic),
            "weak_prerequisites": [{"topic_id": pid, "topic": title, "mastery": score} for pid, title, score in weak_prereqs],
            "signals": {
                "forgotten_pattern": forgotten,
                "application_problem_pattern": application_problem,
                "dependent_topic_count": topic.dependent_count,
            },
        }
        return TopicResult(topic.topic_id, topic.title, mastery, confidence, state, priority, evidence)

    @staticmethod
    def _days_old(when: datetime, now: datetime) -> float:
        value = when if when.tzinfo else when.replace(tzinfo=UTC)
        return max(0.0, (now - value).total_seconds() / 86400)

    @staticmethod
    def _accuracy(answers: list[AnswerEvidence]) -> float | None:
        if not answers:
            return None
        total = sum(max(answer.weight, 0.1) for answer in answers)
        return 100 * sum(max(answer.weight, 0.1) for answer in answers if answer.correct) / total

    @staticmethod
    def _prereq_evidence(topic: TopicInput) -> list[dict]:
        return [{"topic_id": pid, "topic": title, "mastery": score} for pid, title, score in topic.prerequisite_scores]

    @staticmethod
    def _state(mastery: float, confidence: float, forgotten: bool, application_problem: bool) -> KnowledgeState:
        if forgotten:
            return KnowledgeState.FORGOTTEN
        if application_problem:
            return KnowledgeState.APPLICATION_PROBLEM
        if mastery >= 85 and confidence >= 60:
            return KnowledgeState.MASTERED
        if mastery < 40 and confidence >= 40:
            return KnowledgeState.CRITICAL
        if mastery < 60:
            return KnowledgeState.WEAK
        return KnowledgeState.PARTIALLY_UNDERSTOOD

    @staticmethod
    def _priority(mastery: float, confidence: float, dependent_count: int, weak_prereqs: list[tuple[str, str, float]]) -> float:
        weakness = 100 - mastery
        confidence_factor = 0.5 + confidence / 200
        downstream_impact = 1 + dependent_count * 0.25
        prerequisite_risk = 1 + min(0.5, len(weak_prereqs) * 0.15)
        return round(weakness * confidence_factor * downstream_impact * prerequisite_risk, 2)
