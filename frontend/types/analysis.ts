export type TopicResult = {
  topic_id: string; topic_title: string; mastery_score: number; confidence: number; state: string;
  evidence: { weak_prerequisites?: { topic: string; mastery: number }[]; recent_mistakes?: number; total_attempts?: number };
};
export type Analysis = {
  id: string; course_id: string; overall_mastery: number; analyzed_at: string; engine_version: string;
  ai_summary?: { summary?: string }; topics: TopicResult[];
  recommendations: { topic_id: string; topic_title: string; priority: number; content: string }[];
};
