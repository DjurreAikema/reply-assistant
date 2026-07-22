# Phase 3: Production shape

Continue the existing AI-assisted email reply tool. Phases one and two built the working loop and the human review layer. This phase makes the production architecture visible in the code, so the demo can answer questions about real Outlook integration and reliable sending without hand-waving.

Extend the existing codebase. Do not rewrite working code. Most of this phase is interfaces, docstrings and stubs rather than implementation, and the demo must keep working exactly as before on the happy path.

## Outlook integration seam

Add a `GraphMailService` class implementing the existing `MailService` interface, with method signatures and docstrings only. Do not implement it. Each docstring should name the Microsoft Graph endpoint it would call and note anything non-obvious:

- Listing messages from a shared mailbox rather than a personal one
- Replying via `createReply` or `reply` so Graph handles threading, instead of building headers by hand
- Delta queries for polling changes rather than refetching everything
- Where OAuth token acquisition and refresh would sit
- Which permission scopes are needed, and which require tenant admin consent

Add a short `docs/outlook-integration.md` covering what would need to happen to switch over: the Azure app registration, the consent step, and which parts of the existing code change versus stay identical. Be honest about the tenant approval being the slow part.

## Outbound queue

Sending must not be a direct call from the request handler. Route it through a `MailQueue` abstraction. Implement `InMemoryMailQueue` for the demo, and stub `CeleryMailQueue` with signatures and docstrings only.

Model an outbound item with explicit status: `queued`, `sending`, `sent`, `failed`, `dead_letter`. Include `attempt_count`, `last_error`, `next_retry_at`, and an `idempotency_key` derived from the message id plus a hash of the draft body.

Make these concerns legible in code and docstrings without building the infrastructure:

- Retry with exponential backoff and a maximum attempt count
- Distinguishing retryable failures (rate limits, timeouts, transient 5xx) from permanent ones (invalid recipient, auth failure). Permanent failures go straight to dead letter rather than burning retries.
- The idempotency key preventing a duplicate send when a worker crashes after sending but before recording success. This is the failure mode that actually emails a customer twice.
- A dead letter queue a human reviews, and where that surfaces in the UI
- What gets logged and what triggers an alert

## Making failure visible

The normal demo path must still succeed instantly. Add a toggle in the UI, or a seeded message that always fails, so the retry sequence and the dead letter state can be shown on screen rather than only described. Show queue status inline on the message after sending, so the difference between accepted and delivered is visible rather than assumed.

Add a small queue view listing outbound items with their status, attempt count and last error, and a manual retry action for dead lettered items.

## Deliverables

- Working code integrated into the existing project, happy path unchanged
- `docs/outlook-integration.md`
- README updated with the failure simulation toggle, since it is not obvious and is the part worth demoing

Do not use em dashes anywhere in code comments, docstrings, README text, or UI copy.
