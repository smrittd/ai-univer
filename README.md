# AI University

MVP AI-powered learning analytics platform for Calculus. The system calculates student mastery deterministically, then optionally uses OpenAI Structured Outputs to turn that evidence into a clear explanation and learning path.

## Start

```bash
docker compose up --build
```

Backend: `http://localhost:8000/docs`  
Frontend: `http://localhost:3000`

Use `POST /api/v1/mock-data/seed` once to create the Calculus course and demo student. Then log in with `demo@example.com` / `demo-password`.

## Architecture

- `backend/`: FastAPI, SQLAlchemy 2.0, PostgreSQL, Alembic, JWT.
- `frontend/`: Next.js, TypeScript, Tailwind CSS.
- `KnowledgeAnalysisEngine`: deterministic scoring, states, prerequisite-risk detection and learning-path priority.
- `AIInterpretationService`: optional OpenAI Structured Outputs; it only receives immutable engine evidence and cannot set mastery scores.

## Development

```bash
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements.txt
.venv/Scripts/pytest backend/tests
```

Set `DATABASE_URL` to a PostgreSQL URL for normal use. `OPENAI_API_KEY` is optional: without it, the API produces a transparent deterministic explanation.
