# Reply Assistant, phase 1

AI-assisted email replies for a customer service team handling package delivery issues. Click an email, get three suggested templates, get a generated draft, edit, send.

Phase 1 scope only: JSON files as storage, read-only templates, no field extraction. The seams for later phases are `LLMProvider` (backend/app/llm) and `MailService` (backend/app/services/mail_service.py). New capability goes behind those interfaces, not around them.

## Stack

- Frontend: Angular 20, standalone components, Angular Material, signals
- Backend: Flask, Python 3.11+
- LLM: Ollama by default (`llama3.1:8b`, local, offline), Anthropic API optional
- Storage: JSON files in `backend/data/`

## First-time setup

### 1. Ollama (default provider)

Install from https://ollama.com/download, then pull the model:

```
ollama pull llama3.1:8b
```

Ollama normally runs as a background service after install. If not: `ollama serve`.

The backend checks at startup that Ollama is reachable and the model is pulled. A failed check prints the exact command to fix it and exits, instead of failing on the first suggestion.

### 2. Backend

```
cd backend
python -m venv .venv
.venv\Scripts\activate        (Windows)
source .venv/bin/activate     (Mac/Linux)
pip install -r requirements.txt
```

### 3. Frontend

```
cd frontend
npm install
```

## Running

From the project root, one command starts both servers:

```
start.bat        (Windows, opens two terminal windows)
./start.sh       (Mac/Linux)
```

Or manually: `python run.py` in `backend/` and `npm start` in `frontend/`.

Open http://localhost:4200. The Angular dev server proxies `/api` to Flask on port 5000 (`frontend/proxy.conf.json`), so there is no CORS setup and the frontend never needs to know the backend URL.

## Switching LLM providers

The provider is chosen by the `LLM_PROVIDER` environment variable. Default is `ollama` and needs no key.

```
set LLM_PROVIDER=anthropic            (Windows)
set ANTHROPIC_API_KEY=sk-ant-...
export LLM_PROVIDER=anthropic         (Mac/Linux)
export ANTHROPIC_API_KEY=sk-ant-...
```

Then start the backend. Every request logs which provider served it.

Optional overrides: `OLLAMA_URL` (default http://localhost:11434), `OLLAMA_MODEL` (default llama3.1:8b), `ANTHROPIC_MODEL` (default claude-sonnet-4-5).

## How the AI calls work

Every model call requests JSON only. The response is fence-stripped, parsed, and validated against the expected shape. On failure the malformed output goes back to the model once with a repair instruction. Two failures surface as a 502 with the real error, since hiding a broken model helps nobody. All of that lives in `backend/app/llm/structured.py` and applies to both providers.

Template matching sends the full template list in one call, no embeddings and no vector store at this scale. The model returns candidates with a confidence and a reason that must reference something specific in the customer's email. Ids the model invents are dropped server side, top 3 are returned.

Draft generation keeps the chosen template's structure and tone, adapts wording to the customer's specifics, and leaves any `{{placeholder}}` it cannot fill untouched. Filling those is phase 2.

## Data files

- `backend/data/messages.json`: 12 seed emails in Microsoft Graph message shape, plus one app-level `isReplied` flag that Graph does not have. Two of the twelve are deliberately vague or off-topic to exercise the fallback template.
- `backend/data/templates.json`: 10 reply templates with `{{placeholders}}`. Read-only this phase.
- `backend/data/sent.json`: created on first send. Delete it and reset `isReplied` flags to start fresh.

## API

```
GET  /api/messages
GET  /api/messages/<id>
GET  /api/templates
POST /api/messages/<id>/suggest
POST /api/messages/<id>/draft      body: { "template_id": "..." }
POST /api/messages/<id>/send       body: { "body": "..." }
```

## Notes for later phases

- The frontend refetches the message list after a send instead of patching local state. Fine at 12 messages, revisit if the list gets big.
- The in-flight request guard in `ai-panel.ts` drops responses for a message that is no longer selected. Keep that pattern when adding calls.
- Angular 20 was pinned at scaffold time. `ng update @angular/core@21 @angular/cli@21` when on Node 22.22.3 or newer.
- No Google Fonts CDN anywhere, the default path must work offline. Roboto is used only if present on the system.
