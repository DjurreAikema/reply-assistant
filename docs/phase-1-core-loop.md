# Phase 1: Core loop

Build the working skeleton of an AI-assisted email reply tool for a customer service team handling package delivery issues. This is phase one of three. Build only what is described here. Do not add features from later phases, but do structure the code so they can be added without restructuring.

Goal for this phase: click an email, see three suggested templates, see a generated draft, send it.

## Stack

- Frontend: Angular (standalone components, latest stable) with Angular Material. Material components throughout, no Tailwind or Bootstrap.
- Backend: Flask, Python 3.11+, single app package.
- LLM: called only from the Flask backend, never from the browser. Put this behind an `LLMProvider` interface with two implementations:
  - `OllamaProvider` using a local Ollama server, model `llama3.1:8b`. This is the default and requires no API key.
  - `AnthropicProvider` using the official Python SDK, key read from `ANTHROPIC_API_KEY`.
  Select via an `LLM_PROVIDER` environment variable, defaulting to ollama. The default path must work fully offline.
- Storage: JSON files on disk. No database.

Because the default model is a small local one, be strict about structured output. Request JSON only, strip any markdown fences before parsing, validate against the expected schema, and on a parse failure retry once with the malformed output fed back and an instruction to return valid JSON only. Log which provider served each request.

On startup, check Ollama is reachable and the model is pulled. If not, fail with a message naming the exact command to run, rather than erroring on the first request.

## Data

Shape email objects to match Microsoft Graph's message resource, so a real Outlook integration is a drop-in later. In `data/messages.json`:

```json
{
  "id": "string",
  "conversationId": "string",
  "from": { "emailAddress": { "name": "string", "address": "string" } },
  "subject": "string",
  "bodyPreview": "string",
  "body": { "contentType": "text", "content": "string" },
  "receivedDateTime": "ISO 8601",
  "isRead": false
}
```

Seed with 12 realistic customer emails about delivery problems: delayed shipment, wrong address, damaged on arrival, customs hold, missing item from a multi-item order, refund request, tracking number not updating, delivery attempted while out, and two deliberately ambiguous or off-topic ones. Write them in the voice of real frustrated customers, with typos and varying lengths. Some a single line, some five paragraphs.

Templates in `data/templates.json`:

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "body": "string with {{placeholders}}",
  "placeholders": ["customer_name", "tracking_number"]
}
```

Seed with 8 to 10 templates covering the scenarios above. Read-only this phase, editing comes in phase two.

## Endpoints

- `GET /api/messages`
- `GET /api/messages/<id>`
- `GET /api/templates`
- `POST /api/messages/<id>/suggest`
- `POST /api/messages/<id>/draft`
- `POST /api/messages/<id>/send`

Put all mail access behind a `MailService` interface with a `JsonMailService` implementation. Sending writes to `data/sent.json` and marks the message replied. The interface matters more than the implementation here, since it is the seam later phases extend.

## Template matching

Send the full template list to the model in one call. Do not build embedding or vector search. Request:

```json
{
  "candidates": [
    { "template_id": "string", "confidence": 0.0, "reason": "one sentence" }
  ]
}
```

Return the top 3 sorted by confidence descending. The `reason` must reference something specific in the customer's message, not restate the template name.

## Draft generation

Given a message and a chosen template, generate the reply body. Keep the template's structure and tone, adapt wording to the specifics the customer mentioned. Do not invent facts. Leave unknown placeholder values untouched for now. Field extraction is phase two.

## Frontend

Three-pane layout: message list left, selected message centre, AI panel right.

- Selecting a message triggers the suggest call automatically, no extra click.
- The AI panel shows three candidate cards with template name, confidence bar, and reason. Top candidate expanded by default.
- Selecting a candidate generates and shows the draft in an editable text area.
- A Send button with a success state that moves the message to a replied state.
- Skeleton loaders during suggest and draft calls. Never a blank panel or a full-screen spinner.

Clicking an email to a sendable draft should be two clicks and feel fast.

## Deliverables

- Complete runnable source for both apps
- `README.md` with setup, Ollama install and model pull, provider switching, and how to run both servers
- A single command or script that starts backend and frontend together
- Inline comments only where a decision is non-obvious. No comments restating what the code does.

Do not use em dashes anywhere in code comments, docstrings, README text, or UI copy.
