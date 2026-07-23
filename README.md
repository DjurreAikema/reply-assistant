# Reply Assistant, phase 2

AI-assisted email replies for a customer service team handling package delivery issues. Click a conversation, get three suggested templates plus every value the AI extracted from the customer's latest message, review and fix those values, get a generated draft, send. The reply appends to the thread and the conversation stays open for the next turn.

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

## Layout

Four columns, left to right:

- **Inbox.** One row per conversation, showing the last message, the turn count, and whether the thread is waiting on a reply. Unread styling comes from the messages themselves, the waiting label from the thread's last item being inbound.
- **Conversation.** The thread as a transcript, oldest first. Inbound and outbound are distinguished by indent and surface tint, each with its own timestamp. Long bodies clamp with a show more control, and older turns collapse to a preview line. The newest turn and the newest inbound message stay expanded, since those are what the agent is working from.
- **AI column.** Template suggestions on top, the review panel underneath. The two halves scroll independently so a long candidate list cannot push the review panel out of view.
- **Reply draft.** The draft, the send button and the send block reason, in their own column so the draft has room once a thread has several turns.

All four columns are visible at 1720px and up. Below 1720px the AI and draft columns fold into one column with the draft on top, so a 1512px screen shows three columns rather than four. Below 1350px the inbox becomes a drawer with a toggle above the transcript. Below 820px the two remaining columns stack rather than squeeze.

The fold is set by the draft, not by the viewport: it holds the draft at 420px in the four column layout and 440px once folded, against the 250px it would be squeezed to if four columns were forced onto a 1512px screen.

## Conversations

A conversation is the messages and sent items sharing a `conversationId`, ordered by timestamp, inbound and outbound together. There is no separate conversation file and no id generation: the grouping is derived on read in `MailService`.

Sending appends the reply to the transcript with a brief Sent marker and resets the draft column to a composable state. The suggestions and reviewed fields survive the send, so a different template can be drafted without another model call. There is no terminal sent screen and no reload. The stored `isReplied` flag is kept for compatibility but gates nothing; thread state is read from whether the last item is inbound or outbound, which is what lets a thread hold more than one reply.

Suggestion fires once per conversation selection, against the most recent inbound message. Reloading a thread after a send deliberately does not re-suggest. Nothing in the app generates incoming customer replies, but the model allows them: add a message to `messages.json` with an existing `conversationId` and it appears in the thread, drives the inbox row, and becomes the input for the next suggestion, with no code change.

## Review panel and send gating

In the lower half of the AI column the review panel lists each extracted value in an editable input with a confidence indicator and the email fragment it was taken from (hover the source link, or click to pin it). Empty fields that the suggested templates need are flagged as needing input; empty fields no candidate template uses sit behind a toggle. Edits substitute into the draft live while it still contains `{{tokens}}`. Once the agent edits the draft text by hand, substitution stops and their text is never overwritten.

Send is blocked, with the missing field named next to the button, until every placeholder the chosen template declares has a non-empty field value. A literal `{{token}}` remaining in the draft text also blocks, as a backstop.

## Template management

The Templates page (second item in the left nav rail) lists all templates with create, edit and delete. Placeholders are parsed from the body automatically, both live in the form and server side on save. Changes are picked up by the next suggest call with no restart. Deleting a template that a sent reply references is refused; sent replies record their `template_id` since phase 2 (older sent items never block).

## Data files

- `backend/data/messages.json`: 12 seed emails in Microsoft Graph message shape, one conversation each, plus one app-level `isReplied` flag that Graph does not have. Two of the twelve are deliberately vague or off-topic to exercise the fallback template.
- `backend/data/templates.json`: 10 seed reply templates with `{{placeholders}}`, editable from the Templates page.
- `backend/data/sent.json`: sent replies, grouped into threads by `conversationId`. Delete it and reset `isReplied` flags to start fresh.

## API

```
GET    /api/conversations         thread list: subject, participant, last preview and
                                  timestamp, message count, lastIsInbound, isRead
GET    /api/conversations/<id>    ordered thread items, each tagged direction and timestamp
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

- The frontend refetches the conversation list and the open thread after a send instead of patching local state. Fine at this size, revisit if the list gets big.
- `MailService` groups threads on every read. That is honest at 12 conversations and wrong at 12000; a Graph implementation would page and filter server side instead.
- The in-flight request guard in `reply-workspace.ts` drops responses for a message that is no longer selected. Keep that pattern when adding calls.
- With the default llama3.1:8b, the two ambiguous seed emails score around 0.7 to 0.8 top confidence, so the low confidence warning does not trigger on them. The threshold logic works; the local model is simply overconfident. The Anthropic provider or a threshold discussion is the honest fix, not prompt tuning until the demo behaves.
- Angular 20 was pinned at scaffold time. `ng update @angular/core@21 @angular/cli@21` when on Node 22.22.3 or newer.
- No Google Fonts CDN anywhere, the default path must work offline. Roboto is used only if present on the system.
