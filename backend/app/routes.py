from flask import Blueprint, current_app, jsonify, request

from .llm import StructuredOutputError
from .services.assist import draft_reply, suggest_templates
from .services.mail_service import MessageNotFound

api = Blueprint("api", __name__, url_prefix="/api")


def _mail():
    return current_app.extensions["mail_service"]


def _provider():
    return current_app.extensions["llm_provider"]


@api.errorhandler(MessageNotFound)
def _not_found(exc):
    return jsonify({"error": f"No message with id {exc.args[0]}"}), 404


@api.errorhandler(StructuredOutputError)
def _bad_model_output(exc):
    return jsonify({"error": str(exc)}), 502


@api.get("/messages")
def list_messages():
    return jsonify(_mail().list_messages())


@api.get("/messages/<message_id>")
def get_message(message_id: str):
    return jsonify(_mail().get_message(message_id))


@api.get("/templates")
def list_templates():
    return jsonify(_mail().list_templates())


@api.post("/messages/<message_id>/suggest")
def suggest(message_id: str):
    message = _mail().get_message(message_id)
    templates = _mail().list_templates()
    candidates = suggest_templates(_provider(), message, templates)
    # Names come along so the frontend does not need a second lookup to
    # render the cards.
    by_id = {t["id"]: t for t in templates}
    for c in candidates:
        c["template_name"] = by_id[c["template_id"]]["name"]
    return jsonify({"candidates": candidates})


@api.post("/messages/<message_id>/draft")
def draft(message_id: str):
    payload = request.get_json(silent=True) or {}
    template_id = payload.get("template_id")
    if not template_id:
        return jsonify({"error": "template_id is required"}), 400

    message = _mail().get_message(message_id)
    template = next(
        (t for t in _mail().list_templates() if t["id"] == template_id), None
    )
    if template is None:
        return jsonify({"error": f"No template with id {template_id}"}), 404

    return jsonify({"body": draft_reply(_provider(), message, template)})


@api.post("/messages/<message_id>/send")
def send(message_id: str):
    payload = request.get_json(silent=True) or {}
    body = (payload.get("body") or "").strip()
    if not body:
        return jsonify({"error": "body is required"}), 400
    return jsonify(_mail().send_reply(message_id, body)), 201
