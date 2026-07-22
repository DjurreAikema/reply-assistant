"""JSON-only completions with one repair retry.

The default model is a small local one, so this module assumes the output
can be malformed. Order of defence: strip fences, parse, validate shape,
and on any failure feed the bad output back once with a repair instruction.
Two failures in a row is a real error and should surface, not be hidden."""

import json
import logging
from typing import Callable

from .base import LLMProvider

log = logging.getLogger("replybot.llm")


class StructuredOutputError(RuntimeError):
    pass


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    # Small models sometimes add prose before or after the object. Cutting
    # to the outermost braces rescues those cases without hiding real
    # parse errors, json.loads still has to succeed on what remains.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    return text.strip()


def complete_json(
    provider: LLMProvider,
    system: str,
    user: str,
    validate: Callable[[dict], None],
    purpose: str,
) -> dict:
    """validate raises ValueError when the parsed dict has the wrong shape.
    purpose is only for the log line, so failures can be traced to the
    suggest or draft flow."""
    raw = provider.complete(system, user)
    log.info("provider=%s purpose=%s attempt=1", provider.name, purpose)

    for attempt in (1, 2):
        try:
            parsed = json.loads(_strip_fences(raw))
            validate(parsed)
            return parsed
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt == 2:
                raise StructuredOutputError(
                    f"Model returned invalid JSON twice for {purpose}: {exc}"
                ) from exc
            log.warning(
                "provider=%s purpose=%s attempt=1 invalid, retrying: %s",
                provider.name,
                purpose,
                exc,
            )
            raw = provider.complete(
                system,
                "The previous output was not valid for the required schema.\n"
                f"Error: {exc}\n"
                f"Previous output:\n{raw}\n\n"
                "Return ONLY the corrected JSON object. No markdown, no "
                "explanation, no text outside the JSON.",
            )
            log.info("provider=%s purpose=%s attempt=2", provider.name, purpose)

    raise StructuredOutputError(f"unreachable retry state for {purpose}")
