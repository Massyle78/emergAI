# emergAI — Multimodal ER Triage & Risk Prediction Platform

An end-to-end patient intake and triage system that reduces Emergency Department wait times by dynamically assessing risk using multimodal AI and real-time vitals.

## Architecture Overview

```
┌─────────────────────┐       ┌──────────────────────────────────────────────┐
│   Frontend Kiosk    │       │            FastAPI Backend                   │
│  (React / Tailwind) │──────▶│                                              │
│  - Webcam capture   │ media │  ┌──────────┐  ┌─────────┐  ┌────────────┐  │
│  - Mic audio        │───────│  │ open-rppg │  │ Gemini  │  │  Metriport │  │
│  - Patient intake   │       │  │ (vitals)  │  │ 2.5 Pro │  │  (EHR/FHIR)│  │
└─────────────────────┘       │  └─────┬─────┘  └────┬────┘  └─────┬──────┘  │
                              │        │             │             │          │
                              │        └──────┬──────┘─────────────┘          │
                              │               ▼                               │
                              │     ┌──────────────────┐                      │
                              │     │   Orchestration   │                      │
                              │     │   Engine          │                      │
                              │     └────────┬─────────┘                      │
                              │              ▼                                │
                              │  ┌───────────────────────┐                    │
                              │  │  Risk Score + CDS     │──▶ Clinical       │
                              │  │  Hooks Output         │   Dashboard       │
                              │  └───────────────────────┘                    │
                              │              ▼                                │
                              │     ┌────────────────┐                        │
                              │     │   Supabase      │                        │
                              │     │  (Postgres +    │                        │
                              │     │   pgvector)     │                        │
                              │     └────────────────┘                        │
                              └──────────────────────────────────────────────┘
```

## Tech Stack

| Layer         | Technology                              |
|---------------|-----------------------------------------|
| Frontend      | React, Tailwind CSS (Lovable)           |
| Backend       | FastAPI (Python, async)                 |
| Database      | Supabase (PostgreSQL + pgvector)        |
| Auth          | Supabase Auth (JWT)                     |
| EHR           | Metriport API (FHIR R4)                 |
| Vision/Vitals | open-rppg                               |
| Generative AI | Google Gemini 2.5 Pro (via google-genai)|
| Resilience    | tenacity (retry/backoff)                |

## Project Structure

```
emergAI/
├── backend/
│   ├── app/
│   │   ├── models/          # Pydantic schemas & domain models
│   │   ├── routers/         # FastAPI route handlers
│   │   ├── services/        # Business logic & external API clients
│   │   ├── repositories/    # Data access layer (Supabase)
│   │   └── utils/           # Shared utilities
│   ├── tests/
│   │   ├── unit/            # Unit tests
│   │   └── integration/     # Integration tests
│   ├── migrations/          # SQL migration files
│   ├── logging_config.yaml  # Structured logging configuration
│   ├── pyproject.toml       # Dependencies, metadata & tool config
│   └── uv.lock              # Deterministic lockfile (uv)
├── frontend/                # React/Tailwind intake kiosk (future)
├── .env.example             # Environment variable template
├── .gitignore
├── LICENSE
└── README.md
```

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- Node.js 20+ (for frontend, in later phases)
- A Supabase project (free tier works for development)
- Google AI API key (Gemini 2.5 Pro access)
- Metriport API key

## Getting Started

### 1. Install uv

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone & configure

```bash
git clone <repo-url>
cd emergAI
cp .env.example .env
# Edit .env with your actual keys
```

### 3. Backend setup

```bash
cd backend
uv sync          # installs all deps (production + dev) in a virtual env
```

### 4. Run tests

```bash
cd backend
uv run pytest
```

### 5. Start the dev server

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Common uv commands

```bash
uv add <package>           # add a production dependency
uv add --dev <package>     # add a dev-only dependency
uv sync --no-dev           # install production deps only (for deployment)
uv lock                    # regenerate the lockfile
```

## Development Standards

This project enforces strict engineering standards defined in `rules.txt`:

- **Code quality:** Max 30-line functions, max 3 parameters, cyclomatic complexity < 10
- **Testing:** Minimum 80% coverage, 100% on critical business logic
- **Security:** Input validation everywhere, no hardcoded secrets, least-privilege
- **Architecture:** SOLID principles, dependency injection, separation of concerns
- **Observability:** Structured logging, performance metrics

## License

MIT — see [LICENSE](./LICENSE) for details.
