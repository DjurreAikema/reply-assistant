# Conversation view and visual restyle

Continue the existing AI-assisted email reply tool. The core loop, field extraction with human review, send gating and template management are all built and working. This work changes the layout, restyles the app, and turns a single reply into an ongoing conversation.

Extend the existing codebase. Do not rewrite working code, do not restructure the project, do not touch the backend AI prompts or the extraction and normalisation logic in `backend/app/services/assist.py` beyond what the conversation model requires. Match the existing conventions, Angular Material usage and file layout. `LLMProvider` and `MailService` stay as the seams. New capability goes behind them, not around them.

## Goal

Three things, in priority order:

1. A four column layout that separates the conversation from the AI's suggestions and from the draft being written.
2. A modern dashboard visual style, applied across the whole app.
3. A conversation that can hold multiple replies rather than ending at the first send.

## Layout

Four columns, left to right:

- **Inbox.** The conversation list. Narrow.
- **Conversation.** The message thread, rendered as a chat transcript. The widest column, this is where attention sits.
- **AI column.** Split horizontally. Template suggestions on top, the review panel underneath.
- **Reply draft.** The editable draft, the send button and the send block reason.

Notes on what moves:

- The review panel leaves the centre pane. It now sits under the template suggestions in the AI column, next to the draft it feeds rather than under the email it came from. Everything the agent has to check before sending is then in the right half of the screen, in reading order: which template, which values, what gets sent.
- The draft leaves the reply workspace's suggestion column and becomes its own column. That is the whole reason for the split, the draft needs room once a thread has several turns.
- The AI column's two halves each scroll independently. Suggestions do not push the review panel off screen.
- Below roughly 1400px, collapse the AI column and the draft column into a single right column with the draft on top. Below roughly 1000px, the inbox becomes a drawer. Never let a column go below a usable width by squeezing rather than collapsing.

## Visual style

Reference direction: modern SaaS dashboard. Soft, light, card based, generous spacing.

Specifics:

- Cards float on a tinted app background rather than sitting in bordered boxes. Soft shadow and a subtle surface tint carry the separation, not 1px outlines. Corner radius around 16px on cards, 12px on inputs, fully rounded on buttons and chips.
- One accent colour used sparingly, on the primary action and the active nav item only. Everything else is neutral. Confidence indicators keep their own colour scale, since that scale carries meaning.
- Padding roughly doubles from where it is now. The current layout is dense in a way that reads as a prototype. Whitespace is doing most of the work in the reference images.
- Type: one family, three or four sizes, weight carrying the hierarchy rather than size alone. Headings sit at 15px to 20px, body at 13px to 14px.
- Small status chips for message state, template placeholders and confidence bands. Pill shaped, low contrast fill, uppercase avoided.
- Nav moves to a left rail with the inbox and templates as items, replacing the current top right link.

What not to do:

- No fake metrics, sparklines, ring charts or dashboard widgets. The reference images are a style reference, not a content reference. Inventing a "94% resolved" tile would be a lie rendered in CSS.
- No new CSS framework. Angular Material stays. Theme through the `--mat-sys-*` tokens already in use, do not hand roll colours per component.
- No Google Fonts or any other CDN. The default path must work fully offline. Fall back to system fonts.
- No animation beyond what Material already does, plus a short fade on new messages appearing in the thread.

## Conversation model

Today a message is a dead end. Sending sets `isReplied` and the panel switches to a terminal sent state with nothing further to do. Replace that with a thread.

Data:

- `conversationId` already exists on every message in the Graph shape, and sent items already carry it. Group on it. No new data file.
- A conversation is the messages and sent items sharing a `conversationId`, ordered by timestamp. Inbound and outbound both.
- Seed data does not need new customer replies for the demo. The model must simply allow them: a second inbound message with an existing `conversationId` appears in the thread with no code change. Verify that by hand once, then leave the seed data as it is.
- `isReplied` stops being a terminal flag on the message. Thread state derives from whether the last item in the thread is inbound or outbound. Keep the stored field for compatibility, do not gate the UI on it.

Endpoints:

- `GET /api/conversations` returns the thread list for the inbox: id, subject, participant, last message preview, last timestamp, message count, whether the last item is inbound, and read state. Read state is false if any inbound message in the thread is unread, and it is separate from whether the last item is inbound: one drives the unread styling, the other drives the waiting on reply affordance.
- `GET /api/conversations/<id>` returns the ordered items in one thread.
- Existing message endpoints stay for now. Sending stays `POST /api/messages/<id>/send`, appending to the thread as it already does.
- All of it goes through `MailService`. Add the methods to the abstract base and to `JsonMailService`, keeping the existing lock discipline around every read, modify, write.

UI:

- The inbox lists conversations, not messages. One row per thread, showing the last message.
- The conversation column renders the thread as a transcript. Inbound and outbound visually distinct, aligned differently, each with a timestamp. Not literal chat bubbles borrowed from a messaging app, this is still email, so full width blocks with a clear sender line and a subtle background difference.
- Long inbound bodies collapse after a few lines with a show more control. Older turns in a long thread collapse by default, the most recent inbound message is always expanded.
- After a send, the sent reply appends to the transcript and the draft column resets to an empty composable state. No terminal screen, no reload needed. A brief confirmation on the appended item is enough.
- The suggest call still fires on selecting a conversation, using the most recent inbound message as its input. Re-suggesting per turn is out of scope, one suggestion set per conversation selection is correct for now.

## Out of scope

Do not add these, and do not refactor towards them:

- Incoming customer replies, simulated or real. The model allows them, nothing generates them.
- Per turn re-suggestion or re-extraction.
- The known phase two gaps: server side send validation, the low confidence threshold not firing on the ambiguous seed emails, and the missing in-use guard on template update. All three are logged and deliberately deferred. Leave them alone rather than fixing them halfway while moving code around.
- Anything from the production shape doc: queueing, retries, dead letters, Outlook.

## Deliverables

- Working code integrated into the existing project. The existing flow, click a conversation to a sendable draft, still takes two clicks and still works offline on `llama3.1:8b`.
- README updated to cover the four column layout and the conversation behaviour.
- Inline comments only where a decision is non-obvious. No comments restating what the code does.

Do not use em dashes anywhere in code comments, docstrings, README text, or UI copy.
