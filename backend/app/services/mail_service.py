"""Mail access seam.

Everything reads and writes mail through MailService. Phase three swaps in
a Graph-backed implementation, which is why message dicts follow the
Microsoft Graph message resource shape exactly. The one extension is
isReplied, an app-level flag that Graph does not have. It stays in the
stored JSON here; a Graph implementation would track it elsewhere."""

import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path


class MessageNotFound(KeyError):
    pass


class MailService(ABC):
    @abstractmethod
    def list_messages(self) -> list[dict]: ...

    @abstractmethod
    def get_message(self, message_id: str) -> dict: ...

    @abstractmethod
    def list_templates(self) -> list[dict]: ...

    @abstractmethod
    def send_reply(self, message_id: str, body: str) -> dict: ...


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

    def list_templates(self) -> list[dict]:
        with self._lock:
            return self._read(self.templates_path)

    def send_reply(self, message_id: str, body: str) -> dict:
        with self._lock:
            messages = self._read(self.messages_path)
            target = next((m for m in messages if m["id"] == message_id), None)
            if target is None:
                raise MessageNotFound(message_id)

            sent_item = {
                "id": f"sent-{message_id}-{int(datetime.now(timezone.utc).timestamp())}",
                "inReplyTo": message_id,
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
