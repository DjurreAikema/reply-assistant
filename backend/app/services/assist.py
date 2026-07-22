"""Prompt construction and schema validation for the two AI calls.

Every model call in the app returns JSON, including the draft. One shape
of call means one parsing and retry path in llm.structured, and the draft
wrapped as {"body": ...} avoids a second plain-text code path just for
this endpoint."""

from ..llm import LLMProvider, complete_json

SUGGEST_SYSTEM = """You match customer service emails to reply templates.

You receive a customer email and a list of templates. Pick the templates
that best fit the customer's actual problem.

Respond with ONLY a JSON object in exactly this shape:
{
  "candidates": [
    { "template_id": "string", "confidence": 0.0, "reason": "one sentence" }
  ]
}

Rules:
- Include every template that is at least somewhat plausible, you may
  include up to 5 candidates.
- confidence is a number between 0.0 and 1.0.
- reason must quote or reference a specific detail from the customer's
  email, never just restate the template name.
- If the email does not fit any template well, still return your best
  guesses with low confidence values.
- No markdown, no text outside the JSON object."""

DRAFT_SYSTEM = """You write customer service reply drafts for a package
delivery company.

You receive a customer email and one reply template. Write the reply
based on that template.

Rules:
- Keep the template's structure and tone.
- Adapt the wording to the specifics the customer mentioned.
- Do not invent facts, tracking numbers, dates, refund amounts, or
  policies that are not in the template or the customer's email.
- Keep every {{placeholder}} you cannot fill from the customer's email
  exactly as written, double braces included.
- Respond with ONLY a JSON object in exactly this shape:
  { "body": "the full reply text" }
- No markdown, no text outside the JSON object."""


def _validate_suggest(parsed: dict) -> None:
    candidates = parsed.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates must be a non-empty list")
    for c in candidates:
        if not isinstance(c, dict):
            raise ValueError("each candidate must be an object")
        if not isinstance(c.get("template_id"), str):
            raise ValueError("candidate.template_id must be a string")
        if not isinstance(c.get("confidence"), (int, float)):
            raise ValueError("candidate.confidence must be a number")
        if not isinstance(c.get("reason"), str) or not c["reason"].strip():
            raise ValueError("candidate.reason must be a non-empty string")


def _validate_draft(parsed: dict) -> None:
    if not isinstance(parsed.get("body"), str) or not parsed["body"].strip():
        raise ValueError("body must be a non-empty string")


def _email_block(message: dict) -> str:
    sender = message["from"]["emailAddress"]
    return (
        f"From: {sender['name']} <{sender['address']}>\n"
        f"Subject: {message['subject']}\n\n"
        f"{message['body']['content']}"
    )


def suggest_templates(provider: LLMProvider, message: dict, templates: list[dict]) -> list[dict]:
    template_lines = "\n".join(
        f"- id: {t['id']}\n  name: {t['name']}\n  description: {t['description']}"
        for t in templates
    )
    user = (
        f"Customer email:\n---\n{_email_block(message)}\n---\n\n"
        f"Available templates:\n{template_lines}"
    )
    parsed = complete_json(provider, SUGGEST_SYSTEM, user, _validate_suggest, "suggest")

    known_ids = {t["id"] for t in templates}
    candidates = [c for c in parsed["candidates"] if c["template_id"] in known_ids]
    # Small models occasionally hallucinate an id even with the list in
    # front of them. Dropping those and clamping confidence keeps the API
    # contract clean for the frontend.
    for c in candidates:
        c["confidence"] = max(0.0, min(1.0, float(c["confidence"])))
    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    if not candidates:
        raise ValueError("model returned no valid template ids")
    return candidates[:3]


def draft_reply(provider: LLMProvider, message: dict, template: dict) -> str:
    user = (
        f"Customer email:\n---\n{_email_block(message)}\n---\n\n"
        f"Template '{template['name']}':\n---\n{template['body']}\n---"
    )
    parsed = complete_json(provider, DRAFT_SYSTEM, user, _validate_draft, "draft")
    return parsed["body"]
