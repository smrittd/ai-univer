from datetime import UTC, datetime, timedelta

from app.services.knowledge_engine import AnswerEvidence, KnowledgeAnalysisEngine, KnowledgeState, TopicInput


NOW = datetime(2026, 9, 9, tzinfo=UTC)


def answer(correct: bool, days_ago: int = 1, difficulty: int = 1) -> AnswerEvidence:
    return AnswerEvidence(correct=correct, weight=1, difficulty=difficulty, submitted_at=NOW - timedelta(days=days_ago))


def test_topic_without_evidence_is_never_learned():
    result = KnowledgeAnalysisEngine().analyze([TopicInput("limits", "Limits", [], [], 1)], NOW)[0]
    assert result.state == KnowledgeState.NEVER_LEARNED
    assert result.mastery_score == 0


def test_forgotten_requires_good_old_and_weak_recent_performance():
    answers = [answer(True, 70) for _ in range(8)] + [answer(False, 2) for _ in range(8)]
    result = KnowledgeAnalysisEngine().analyze([TopicInput("limits", "Limits", answers, [], 1)], NOW)[0]
    assert result.state == KnowledgeState.FORGOTTEN
    assert result.evidence["signals"]["forgotten_pattern"] is True


def test_application_problem_detects_easy_hard_split():
    answers = [answer(True, difficulty=1) for _ in range(8)] + [answer(False, difficulty=4) for _ in range(8)]
    result = KnowledgeAnalysisEngine().analyze([TopicInput("chain", "Chain Rule", answers, [], 2)], NOW)[0]
    assert result.state == KnowledgeState.APPLICATION_PROBLEM


def test_weak_prerequisite_is_exposed_as_evidence_not_assumed_fact():
    answers = [answer(index % 2 == 0) for index in range(18)]
    result = KnowledgeAnalysisEngine().analyze(
        [TopicInput("chain", "Chain Rule", answers, [("composition", "Function Composition", 43)], 2)], NOW
    )[0]
    assert result.evidence["weak_prerequisites"][0]["topic"] == "Function Composition"
    assert result.mastery_score < 60
