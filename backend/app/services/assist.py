"""Prompt construction and schema validation for the two AI calls.

Every model call in the app returns JSON, including the draft. One shape
of call means one parsing and retry path in llm.structured, and the draft
wrapped as {"body": ...} avoids a second plain-text code path just for
this endpoint."""

import os
import re

from ..llm import LLMProvider, complete_json

# The agent signing the reply is the same person all day, so their name
# is configuration, not something to extract from a customer email or
# show in the review panel. Injected into the draft at draft time.
AGENT_NAME = os.environ.get("AGENT_NAME", "Sam Peters")

_AGENT_NAME_RE = re.compile(r"\{\{\s*agent_name\s*\}\}")

# Always requested regardless of which templates exist, per the phase two
# spec. Template placeholders are added on top of these per request.
BASE_FIELD_KEYS = [
    "customer_name",
    "tracking_number",
    "order_number",
    "delivery_address",
    "order_date",
]

SUGGEST_SYSTEM = """You match customer service emails to reply templates
and extract structured values from the email.

You receive a customer email, a list of templates, and a list of field
keys to extract. Pick the templates that best fit the customer's actual
problem, and fill in the fields from the email.

Respond with ONLY a JSON object in exactly this shape:
{
  "candidates": [
    { "template_id": "string", "confidence": 0.0, "reason": "one sentence" }
  ],
  "fields": [
    { "key": "string", "value": "string", "confidence": 0.0, "source_span": "string" }
  ]
}

Rules for candidates:
- Include every template that is at least somewhat plausible, you may
  include up to 5 candidates.
- confidence is a number between 0.0 and 1.0.
- reason must quote or reference a specific detail from the customer's
  email, never just restate the template name.
- If the email does not fit any template well, still return your best
  guesses with low confidence values.

Rules for fields:
- Return one entry for every requested key.
- value must be taken from the customer's email, not invented, not
  inferred, not completed from general knowledge.
- source_span is the exact fragment of the email the value was taken
  from, copied verbatim.
- If the email does not contain a value for a key, return that key with
  value "", source_span "" and confidence 0.0. An empty value is always
  correct when unsure. Never guess.

No markdown, no text outside the JSON object."""

DRAFT_SYSTEM = """You write customer service reply drafts for a package
delivery company.

You receive a customer email and one reply template. Write the reply
based on that template.

THE MOST IMPORTANT RULE: every {{placeholder}} in the template must
appear in your reply exactly as written, double braces included. The
application substitutes them afterwards from values a human has
reviewed. Filling one in yourself, even with a value from the email,
bypasses that review.

Example. Template line:
  I have checked tracking number {{tracking_number}}.
Customer email says the tracking number is AB-1234. Correct output:
  I have checked tracking number {{tracking_number}}.
Wrong output:
  I have checked tracking number AB-1234.

Other rules:
- Keep the template's structure and tone.
- Adapt the surrounding wording to the specifics the customer mentioned.
- Do not invent facts, tracking numbers, dates, refund amounts, or
  policies that are not in the template or the customer's email.
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
    fields = parsed.get("fields")
    if not isinstance(fields, list):
        raise ValueError("fields must be a list")
    for f in fields:
        if not isinstance(f, dict):
            raise ValueError("each field must be an object")
        if not isinstance(f.get("key"), str) or not f["key"].strip():
            raise ValueError("field.key must be a non-empty string")
        if not isinstance(f.get("value"), str):
            raise ValueError("field.value must be a string")
        if not isinstance(f.get("confidence"), (int, float)):
            raise ValueError("field.confidence must be a number")
        if not isinstance(f.get("source_span"), str):
            raise ValueError("field.source_span must be a string")


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


def _field_keys(templates: list[dict]) -> list[str]:
    """Base keys first, then whatever the current templates need, so a
    template added five minutes ago gets its placeholders extracted with
    no code change. agent_name is config, never extracted."""
    keys = list(BASE_FIELD_KEYS)
    for t in templates:
        for p in t.get("placeholders", []):
            if p != "agent_name" and p not in keys:
                keys.append(p)
    return keys


def suggest_templates(provider: LLMProvider, message: dict, templates: list[dict]) -> dict:
    template_lines = "\n".join(
        f"- id: {t['id']}\n  name: {t['name']}\n  description: {t['description']}"
        for t in templates
    )
    field_keys = _field_keys(templates)
    user = (
        f"Customer email:\n---\n{_email_block(message)}\n---\n\n"
        f"Available templates:\n{template_lines}\n\n"
        f"Fields to extract:\n" + "\n".join(f"- {k}" for k in field_keys)
    )
    parsed = complete_json(provider, SUGGEST_SYSTEM, user, _validate_suggest, "suggest")

    known_ids = {t["id"] for t in templates}
    # Small models occasionally hallucinate an id even with the list in
    # front of them, or repeat the same id twice. Dropping those and
    # clamping confidence keeps the API contract clean for the frontend.
    candidates = []
    seen_ids = set()
    for c in parsed["candidates"]:
        if c["template_id"] not in known_ids or c["template_id"] in seen_ids:
            continue
        seen_ids.add(c["template_id"])
        c["confidence"] = max(0.0, min(1.0, float(c["confidence"])))
        candidates.append(c)
    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    if not candidates:
        raise ValueError("model returned no valid template ids")

    # Same defensive posture for fields: keep only requested keys, first
    # occurrence wins, and every requested key comes back even if the
    # model dropped it. An empty value means confidence and span are
    # meaningless, so they are normalised away rather than trusted.
    by_key = {}
    for f in parsed["fields"]:
        key = f["key"].strip()
        if key in field_keys and key not in by_key:
            by_key[key] = f
    fields = []
    for key in field_keys:
        f = by_key.get(key, {"value": "", "confidence": 0.0, "source_span": ""})
        value = f["value"].strip()
        fields.append(
            {
                "key": key,
                "value": value,
                "confidence": max(0.0, min(1.0, float(f["confidence"]))) if value else 0.0,
                "source_span": f["source_span"].strip() if value else "",
            }
        )

    return {"candidates": candidates[:3], "fields": fields}


def draft_reply(provider: LLMProvider, message: dict, template: dict) -> str:
    # agent_name is filled into the template before the model sees it.
    # Left as a token, small models tend to rewrite it into things like
    # [Agent Name] instead of preserving it, and then nothing downstream
    # can substitute reliably. The post-call sub is only a backstop.
    template_body = _AGENT_NAME_RE.sub(AGENT_NAME, template["body"])
    user = (
        f"Customer email:\n---\n{_email_block(message)}\n---\n\n"
        f"Template '{template['name']}':\n---\n{template_body}\n---"
    )
    parsed = complete_json(provider, DRAFT_SYSTEM, user, _validate_draft, "draft")
    return _AGENT_NAME_RE.sub(AGENT_NAME, parsed["body"])
