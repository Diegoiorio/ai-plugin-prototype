# Nuxt Minimal Starter

Look at the [Nuxt documentation](https://nuxt.com/docs/getting-started/introduction) to learn more.

## Setup

Make sure to install dependencies:

```bash
# npm
npm install

# pnpm
pnpm install

# yarn
yarn install

# bun
bun install
```

## Development Server

Start the development server on `http://localhost:3000`:

```bash
# npm
npm run dev

# pnpm
pnpm dev

# yarn
yarn dev

# bun
bun run dev
```

## Backend API

The frontend relies on the FastAPI backend exposed on `http://localhost:8000`.

Start the PostgreSQL database from the project root:

```bash
docker compose up -d postgres
```

Then start the backend from the `backend` folder.

On Windows (PowerShell):

```bash
# create the virtual environment if needed
python -m venv .venv

# activate it on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# install dependencies
pip install -r requirements.txt

# run the API
uvicorn main:app --reload --port 8000
```

On Linux / WSL / macOS:

```bash
# create the virtual environment if needed
python3 -m venv .venv

# activate it
source .venv/bin/activate

# run the API
uvicorn main:app --reload --port 8000

# install dependencies
pip install -r requirements.txt
```

The backend reads `DATABASE_URL` from `backend/.env`. With the current setup, the health check is available at `http://localhost:8000/health`.
For the swagger: `http://localhost:8000/docs#/`

## Technical Overview

### Architecture at a glance

The project is split into two runtime layers:

- `frontend/` (Nuxt + Vue): collects the natural-language prompt and renders tabular/chart results.
- `backend/` (FastAPI + SQLAlchemy): interprets prompt intent, builds a safe SQL query, executes it on PostgreSQL, and returns a normalized payload for UI consumption.

Supporting service:

- PostgreSQL (started via `docker compose`) stores CRM-like data and prompt history (`prompt_requests`).

### End-to-end flow (frontend -> backend -> external service)

1. The user writes a prompt in `frontend/app/app.vue` and submits the form.
2. Frontend sends `POST /ai/query` to the backend with `{ "prompt": "..." }`.
3. Backend route `ai_query` in `backend/main.py`:
   - normalizes the prompt key for in-memory cache lookup;
   - if not cached, calls `interpret_with_gemini` from `backend/ai_service.py`.
4. `ai_service.py` builds a constrained prompt (including `SAFE_DB_SCHEMA`) and calls Gemini (`google.genai`) to obtain a JSON query plan.
5. Backend passes the plan to `build_safe_query` in `backend/query_builder.py`.
6. `query_builder.py` validates and converts the plan into parameterized SQL (`sqlalchemy.text`).
7. Backend executes query, formats rows/columns/chart metadata, and returns JSON to frontend.
8. Frontend renders table + configurable X/Y bar chart.

### Backend role

The backend is the orchestration and safety boundary. It:

- exposes API endpoints (`/health`, `/prompts`, `/ai/query`);
- handles DB session lifecycle;
- delegates natural language interpretation to Gemini;
- enforces structural safety through schema-driven validation in query building;
- normalizes output so frontend can render it consistently.

### Gemini role and usage

Gemini is used only for interpretation, not for direct SQL generation/execution in the backend runtime path.

- Module: `backend/ai_service.py`.
- API key source: `GEMINI_API_KEY`.
- Input to Gemini: a strict instruction prompt including allowed schema and response format.
- Expected output: JSON plan (tables, fields, aggregations, filters, group/order, chart hints).
- Parsing: `extract_json` removes markdown code fences and parses JSON.

If Gemini is unavailable or fails, `main.py` currently raises `502` in `/ai/query`.

### How the safe schema works

`backend/ai_schema.py` defines `SAFE_DB_SCHEMA`, the single whitelist used by both AI prompting and SQL validation.

It contains:

- allowed tables (`users`, `customers`, `opportunities`);
- allowed fields with semantic types (`number`, `text`, `category`, `temporal`);
- allowed relations between tables.

`backend/query_builder.py` enforces this schema by validating:

- tables and fields;
- joins against declared relations;
- operators (`=`, `!=`, `>`, `>=`, `<`, `<=`, `in`);
- transforms (`month`, `year`) only on temporal fields;
- aggregations (`sum`, `avg`, `count`, `count_distinct`, `min`, `max`);
- ordering only on selected aliases;
- limit bounds (fallback to `100` if invalid/out of range).

### Data handling, validation, and transformations

Important technical points in current implementation:

- SQL is built with bound parameters for filters and limit (`db.execute(query, params)`).
- Chart axes are validated against returned columns and numeric constraints.
- Response payload includes:
  - `title`, `description`;
  - `columns` metadata (`key`, `label`, `type`);
  - `rows` data;
  - `chart` object with selected axes and compatible fields.
- Prompt plans are cached in-process (`AI_PLAN_CACHE`) by normalized prompt text.

### Main modules and endpoints

Backend modules:

- `backend/main.py`: FastAPI app, routes, DB session handling, orchestration.
- `backend/ai_service.py`: Gemini prompt construction + response parsing.
- `backend/query_builder.py`: safe plan validation and SQL generation.
- `backend/ai_schema.py`: allowed DB schema and relations.

API endpoints:

- `GET /health`: service status check.
- `POST /prompts`: stores a prompt in `prompt_requests`.
- `GET /prompts`: returns saved prompts (desc by id).
- `POST /ai/query`: main AI-driven query endpoint for frontend analytics.

### Typical operational sequence

1. Start PostgreSQL with Docker Compose.
2. Start backend (`uvicorn main:app --reload --port 8000`).
3. Start frontend (`npm run dev` in `frontend/`).
4. Submit prompt from UI.
5. Backend interprets prompt with Gemini, validates plan, executes SQL, returns result.
6. Frontend renders table and chart, with user-selectable X/Y among compatible fields.

### Maintenance notes

- Keep `SAFE_DB_SCHEMA` aligned with actual database schema before extending prompt capabilities.
- Any new analytics capability should be reflected in both prompt instructions (`ai_service.py`) and validator constraints (`query_builder.py`).
- `main.py` currently contains duplicated helper blocks from iterative development; they do not change the active `/ai/query` return path but should be reviewed in a dedicated refactor task.
- Ensure `GEMINI_API_KEY` and `DATABASE_URL` are configured in local/dev environments before testing full flow.

## Production

Build the application for production:

```bash
# npm
npm run build

# pnpm
pnpm build

# yarn
yarn build

# bun
bun run build
```

Locally preview production build:

```bash
# npm
npm run preview

# pnpm
pnpm preview

# yarn
yarn preview

# bun
bun run preview
```

Check out the [deployment documentation](https://nuxt.com/docs/getting-started/deployment) for more information.
