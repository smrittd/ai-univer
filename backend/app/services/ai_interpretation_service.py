"""Constrained AI interpretation of already-calculated evidence."""
from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.services.knowledge_engine import TopicResult


class AIInterpretationService:
    """Uses OpenAI only for language and ordering explanations, never scoring."""

    def interpret(self, course_title: str, overall_mastery: float, results: list[TopicResult]) -> dict[str, Any]:
        payload = {
            "course": course_title,
            "overall_mastery": overall_mastery,
            "topics": [
                {
                    "topic_id": result.topic_id,
                    "topic": result.title,
                    "mastery": result.mastery_score,
                    "confidence": result.confidence,
                    "state": result.state,
                    "evidence": result.evidence,
                }
                for result in results
            ],
        }
        settings = get_settings()
        if not settings.openai_api_key:
            return self._deterministic_fallback(payload)

        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            response = client.responses.create(
                model=settings.openai_model,
                store=False,
                instructions=(
                    "You explain a student's learning analytics report. Scores, states, topics and evidence in the input "
                    "are immutable facts. Never change, recompute, add or invent them. A prerequisite explanation must be "
                    "described as likely, not certain. Return JSON only following the supplied schema."
                ),
                input=json.dumps(payload),
                text={"format": {"type": "json_schema", "name": "knowledge_interpretation", "strict": True, "schema": self._schema()}},
            )
            parsed = json.loads(response.output_text)
            self._validate_references(parsed, payload)
            return parsed
        except Exception:
            # A report must stay available even without a model or during a provider failure.
            return self._deterministic_fallback(payload)

    @staticmethod
    def _schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["summary", "topic_explanations"],
            "properties": {
                "summary": {"type": "string"},
                "topic_explanations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["topic_id", "explanation", "likely_causes"],
                        "properties": {
                            "topic_id": {"type": "string"},
                            "explanation": {"type": "string"},
                            "likely_causes": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        }

    @staticmethod
    def _validate_references(output: dict[str, Any], payload: dict[str, Any]) -> None:
        allowed = {topic["topic_id"] for topic in payload["topics"]}
        if any(item["topic_id"] not in allowed for item in output["topic_explanations"]):
            raise ValueError("AI output referenced an unknown topic")

    @staticmethod
    def _deterministic_fallback(payload: dict[str, Any]) -> dict[str, Any]:
        explanations = []
        for topic in payload["topics"]:
            weak_prereqs = topic["evidence"].get("weak_prerequisites", [])
            causes = []
            if weak_prereqs:
                causes.append(f"Likely prerequisite gap: {weak_prereqs[0]['topic']} ({weak_prereqs[0]['mastery']}% mastery).")
            if topic["evidence"].get("recent_mistakes", 0) >= 3:
                causes.append(f"{topic['evidence']['recent_mistakes']} recent incorrect attempts need review.")
            explanations.append({
                "topic_id": topic["topic_id"],
                "explanation": f"{topic['topic']}: {topic['state']} with {topic['mastery']}% deterministic mastery.",
                "likely_causes": causes,
            })
        return {
            "summary": f"Current deterministic course mastery is {payload['overall_mastery']}%. Review the highest-priority weak foundations first.",
            "topic_explanations": explanations,
            "source": "deterministic_fallback",
        }
