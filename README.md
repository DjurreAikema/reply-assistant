# Reply Assistant, phase 2

AI-assisted email replies for a customer service team handling package delivery issues. Click an email, get three suggested templates plus every value the AI extracted from the email, review and fix those values, get a generated draft, send.

Phase 2 adds field extraction with human review, send gating, low confidence flagging, and full template management. Storage is still JSON files. The seams for later phases are `LLMProvider` (backend/app/llm) and `MailService` (backend/app/services/mail_service.py). New capability goes behind those interfaces, not around them.

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

Optional overrides: `OLLAMA_URL` (default http://localhost:11434), `OLLAMA_MODEL` (default llama3.1:8b), `ANTHROPIC_MODEL` (default claude-sonnet-4-5), `AGENT_NAME` (the name signed under every draft, default Sam Peters).

## How the AI calls work

Every model call requests JSON only. The response is fence-stripped, parsed, and validated against the expected shape. On failure the malformed output goes back to the model once with a repair instruction. Two failures surface as a 502 with the real error, since hiding a broken model helps nobody. All of that lives in `backend/app/llm/structured.py` and applies to both providers.

Template matching and field extraction happen in one suggest call. The model returns candidates with a confidence and a reason that must reference something specific in the customer's email, plus one entry per field key: the base five (customer name, tracking number, order number, delivery address, order date) and every placeholder any current template declares. Fields the model cannot find come back empty, never guessed. Ids the model invents are dropped server side, top 3 candidates are returned. If the top candidate scores below 0.5 the response is flagged low confidence and the UI shows a warning above the cards.

Draft generation keeps the chosen template's structure and tone and is instructed to leave every `{{placeholder}}` untouched so the app can fill them from reviewed values. The small local model only sometimes obeys that and often fills values itself, which is why sending is gated on the reviewed field data rather than on the draft text. `agent_name` is filled from `AGENT_NAME` config before the model sees the template and never appears in the review panel.

## Review panel and send gating

Below the message body the review panel lists each extracted value in an editable input with a confidence indicator and the email fragment it was taken from (hover the source link, or click to pin it). Empty fields that the suggested templates need are flagged as needing input; empty fields no candidate template uses sit behind a toggle. Edits substitute into the draft live while it still contains `{{tokens}}`. Once the agent edits the draft text by hand, substitution stops and their text is never overwritten.

Send is blocked, with the missing field named next to the button, until every placeholder the chosen template declares has a non-empty field value. A literal `{{token}}` remaining in the draft text also blocks, as a backstop.

## Template management

The Templates page (top right) lists all templates with create, edit and delete. Placeholders are parsed from the body automatically, both live in the form and server side on save. Changes are picked up by the next suggest call with no restart. Deleting a template that a sent reply references is refused; sent replies record their `template_id` since phase 2 (older sent items never block).

## Data files

- `backend/data/messages.json`: 12 seed emails in Microsoft Graph message shape, plus one app-level `isReplied` flag that Graph does not have. Two of the twelve are deliberately vague or off-topic to exercise the fallback template.
- `backend/data/templates.json`: 10 seed reply templates with `{{placeholders}}`, editable from the Templates page.
- `backend/data/sent.json`: created on first send. Delete it and reset `isReplied` flags to start fresh.

## API

```
GET    /api/messages
GET    /api/messages/<id>
GET    /api/templates
POST   /api/templates              body: { "name": "...", "description": "...", "body": "..." }
PUT    /api/templates/<id>         body: same as POST
DELETE /api/templates/<id>         409 if a sent reply references it
POST   /api/messages/<id>/suggest  returns { candidates, fields, low_confidence }
POST   /api/messages/<id>/draft    body: { "template_id": "..." }
POST   /api/messages/<id>/send     body: { "body": "...", "template_id": "..." }
```

## Notes for later phases

- The frontend refetches the message list after a send instead of patching local state. Fine at 12 messages, revisit if the list gets big.
- The in-flight request guard in `ai-panel.ts` drops responses for a message that is no longer selected. Keep that pattern when adding calls.
- With the default llama3.1:8b, the two ambiguous seed emails score around 0.7 to 0.8 top confidence, so the low confidence warning does not trigger on them. The threshold logic works; the local model is simply overconfident. The Anthropic provider or a threshold discussion is the honest fix, not prompt tuning until the demo behaves.
- Angular 20 was pinned at scaffold time. `ng update @angular/core@21 @angular/cli@21` when on Node 22.22.3 or newer.
- No Google Fonts CDN anywhere, the default path must work offline. Roboto is used only if present on the system.
