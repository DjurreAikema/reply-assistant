# Phase 2: Accuracy and human review

Continue the existing AI-assisted email reply tool. Phase one built the core loop: click an email, get three template suggestions, generate a draft, send. This phase makes the AI's guesses visible and correctable, and lets the team manage templates.

Extend the existing codebase. Do not rewrite working code or restructure the project. Match the existing conventions, Angular Material usage, and file layout.

Goal for this phase: the agent can see every value the AI extracted, where it came from, and fix it in one click before sending.

## Extracted fields

Extend the suggest call to also pull structured values out of the email in the same request, so the draft needs no second round trip. Return:

```json
{
  "candidates": [
    { "template_id": "string", "confidence": 0.0, "reason": "one sentence" }
  ],
  "fields": [
    { "key": "tracking_number", "value": "", "confidence": 0.0, "source_span": "" }
  ]
}
```

`source_span` is the fragment of the customer's email the value was taken from. Fields the model cannot fill are returned with an empty value, never a guess.

Cover at minimum: customer name, tracking number, order number, delivery address, order date. Extract whatever the templates' placeholders require.

## Review panel

Below the message body in the centre pane, add a compact review panel, visible once a suggestion returns. For each field:

- Label, the extracted value in an editable Material input, and a confidence indicator
- The `source_span` shown on hover or expand, so the agent can verify without rereading the whole email
- Empty fields visibly flagged as needing input
- Editing a value updates the draft, either by regenerating or by direct substitution if that is faster

The panel should be scannable in a couple of seconds. This is the piece the demo hinges on, so it deserves the most layout care of anything in the app.

## Send gating

Block sending while any field required by the chosen template is still empty. The Send button disables with a visible reason naming the missing field. Never fail silently, and never send a reply containing an unfilled placeholder.

## Low confidence handling

If the top candidate's confidence is below 0.5, still return all three but flag the result as low confidence. The UI shows an inline warning above the candidate cards suggesting the agent write manually or pick carefully. Make sure the two ambiguous seed emails from phase one actually trigger this, since a demo where everything is perfect reads as rigged.

## Template management

Add full CRUD:

- `POST /api/templates`, `PUT /api/templates/<id>`, `DELETE /api/templates/<id>`
- A separate templates page in the Angular app, listing templates with edit and delete, and a form for creating and editing
- Placeholders parsed automatically from the template body rather than entered by hand
- Prevent deleting a template referenced by a sent reply, or handle it gracefully

New templates must be picked up by the next suggest call with no restart.

## Deliverables

- Working code integrated into the existing project
- README updated to cover the new page and behaviour

Do not use em dashes anywhere in code comments, docstrings, README text, or UI copy.
