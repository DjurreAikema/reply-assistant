"""Mail access seam.

Everything reads and writes mail through MailService. Phase three swaps in
a Graph-backed implementation, which is why message dicts follow the
Microsoft Graph message resource shape exactly. The one extension is
isReplied, an app-level flag that Graph does not have. It stays in the
stored JSON here; a Graph implementation would track it elsewhere."""

import json
import re
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path


class MessageNotFound(KeyError):
    pass


class TemplateNotFound(KeyError):
    pass


class TemplateInUse(RuntimeError):
    pass


class ConversationNotFound(KeyError):
    pass


_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def parse_placeholders(body: str) -> list[str]:
    """Placeholders come from the template body, never from user input,
    so stored templates cannot disagree with what their body contains."""
    seen: list[str] = []
    for match in _PLACEHOLDER_RE.finditer(body):
        if match.group(1) not in seen:
            seen.append(match.group(1))
    return seen


def _instant(value: str) -> datetime:
    """Inbound timestamps are Graph style with a Z suffix, outbound ones
    come from isoformat() with a +00:00 offset. Sorting the raw strings
    would interleave a thread wrongly, so parse before comparing."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _preview(text: str, limit: int = 140) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rstrip() + "…"


class MailService(ABC):
    @abstractmethod
    def list_messages(self) -> list[dict]: ...

    @abstractmethod
    def get_message(self, message_id: str) -> dict: ...

    @abstractmethod
    def list_conversations(self) -> list[dict]: ...

    @abstractmethod
    def get_conversation(self, conversation_id: str) -> list[dict]: ...

    @abstractmethod
    def list_templates(self) -> list[dict]: ...

    @abstractmethod
    def create_template(self, name: str, description: str, body: str) -> dict: ...

    @abstractmethod
    def update_template(
        self, template_id: str, name: str, description: str, body: str
    ) -> dict: ...

    @abstractmethod
    def delete_template(self, template_id: str) -> None: ...

    @abstractmethod
    def send_reply(self, message_id: str, body: str, template_id: str | None = None) -> dict: ...


class JsonMailService(MailService):
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.messages_path = self.data_dir / "messages.json"
        self.templates_path = self.data_dir / "templates.json"
        self.sent_path = self.data_dir / "sent.json"
        # Flask dev server can overlap requests. One lock around every
        # read-modify-write keeps the JSON files consistent without
        # dragging in a database, which is out of scope for this phase.
        self._lock = threading.Lock()

    def _read(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def _write(self, path: Path, items: list[dict]) -> None:
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(items, fh, indent=2, ensure_ascii=False)
        tmp.replace(path)

    def list_messages(self) -> list[dict]:
        with self._lock:
            messages = self._read(self.messages_path)
        return sorted(messages, key=lambda m: m["receivedDateTime"], reverse=True)

    def get_message(self, message_id: str) -> dict:
        with self._lock:
            for message in self._read(self.messages_path):
                if message["id"] == message_id:
                    return message
        raise MessageNotFound(message_id)

    def _threads(self, messages: list[dict], sent: list[dict]) -> dict[str, list[dict]]:
        """Group inbound and outbound into ordered threads. direction and
        timestamp are added so callers never have to know which of the two
        source shapes an item came from."""
        threads: dict[str, list[dict]] = {}
        for message in messages:
            item = {**message, "direction": "inbound", "timestamp": message["receivedDateTime"]}
            threads.setdefault(message["conversationId"], []).append(item)
        for sent_item in sent:
            item = {**sent_item, "direction": "outbound", "timestamp": sent_item["sentDateTime"]}
            threads.setdefault(sent_item["conversationId"], []).append(item)
        for items in threads.values():
            items.sort(key=lambda i: _instant(i["timestamp"]))
        return threads

    def _summarise(self, conversation_id: str, items: list[dict]) -> dict:
        last = items[-1]
        opener = next((i for i in items if i["direction"] == "inbound"), last)
        participant = (
            opener["from"]["emailAddress"]
            if opener["direction"] == "inbound"
            else opener["to"]["emailAddress"]
        )
        return {
            "id": conversation_id,
            "subject": opener["subject"],
            "participant": participant,
            "lastPreview": _preview(last["body"]["content"]),
            "lastTimestamp": last["timestamp"],
            "messageCount": len(items),
            "lastIsInbound": last["direction"] == "inbound",
            # A thread is unread while any inbound message in it is, not
            # just the newest one.
            "isRead": all(
                i.get("isRead", True) for i in items if i["direction"] == "inbound"
            ),
        }

    def list_conversations(self) -> list[dict]:
        with self._lock:
            messages = self._read(self.messages_path)
            sent = self._read(self.sent_path)
        threads = self._threads(messages, sent)
        summaries = [self._summarise(cid, items) for cid, items in threads.items()]
        return sorted(summaries, key=lambda s: _instant(s["lastTimestamp"]), reverse=True)

    def get_conversation(self, conversation_id: str) -> list[dict]:
        with self._lock:
            messages = self._read(self.messages_path)
            sent = self._read(self.sent_path)
        items = self._threads(messages, sent).get(conversation_id)
        if not items:
            raise ConversationNotFound(conversation_id)
        return items

    def list_templates(self) -> list[dict]:
        with self._lock:
            return self._read(self.templates_path)

    def create_template(self, name: str, description: str, body: str) -> dict:
        template = {
            "id": f"tpl-{uuid.uuid4().hex[:8]}",
            "name": name,
            "description": description,
            "body": body,
            "placeholders": parse_placeholders(body),
        }
        with self._lock:
            templates = self._read(self.templates_path)
            templates.append(template)
            self._write(self.templates_path, templates)
        return template

    def update_template(self, template_id: str, name: str, description: str, body: str) -> dict:
        with self._lock:
            templates = self._read(self.templates_path)
            target = next((t for t in templates if t["id"] == template_id), None)
            if target is None:
                raise TemplateNotFound(template_id)
            target["name"] = name
            target["description"] = description
            target["body"] = body
            target["placeholders"] = parse_placeholders(body)
            self._write(self.templates_path, templates)
        return target

    def delete_template(self, template_id: str) -> None:
        with self._lock:
            templates = self._read(self.templates_path)
            target = next((t for t in templates if t["id"] == template_id), None)
            if target is None:
                raise TemplateNotFound(template_id)
            # Sent items only started recording template_id in phase two,
            # so older sent replies never block a delete.
            sent = self._read(self.sent_path)
            if any(s.get("template_id") == template_id for s in sent):
                raise TemplateInUse(template_id)
            templates.remove(target)
            self._write(self.templates_path, templates)

    def send_reply(self, message_id: str, body: str, template_id: str | None = None) -> dict:
        with self._lock:
            messages = self._read(self.messages_path)
            target = next((m for m in messages if m["id"] == message_id), None)
            if target is None:
                raise MessageNotFound(message_id)

            sent_item = {
                "id": f"sent-{message_id}-{int(datetime.now(timezone.utc).timestamp())}",
                "inReplyTo": message_id,
                "template_id": template_id,
                "conversationId": target["conversationId"],
                "to": target["from"],
                "subject": f"RE: {target['subject']}",
                "body": {"contentType": "text", "content": body},
                "sentDateTime": datetime.now(timezone.utc).isoformat(),
            }

            sent = self._read(self.sent_path)
            sent.append(sent_item)
            self._write(self.sent_path, sent)

            target["isReplied"] = True
            target["isRead"] = True
            self._write(self.messages_path, messages)

        return sent_item
