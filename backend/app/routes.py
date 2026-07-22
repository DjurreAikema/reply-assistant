from flask import Blueprint, current_app, jsonify, request

from .llm import StructuredOutputError
from .services.assist import draft_reply, suggest_templates
from .services.mail_service import MessageNotFound, TemplateInUse, TemplateNotFound

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


@api.errorhandler(TemplateNotFound)
def _template_not_found(exc):
    return jsonify({"error": f"No template with id {exc.args[0]}"}), 404


@api.errorhandler(TemplateInUse)
def _template_in_use(exc):
    return (
        jsonify({"error": "This template is referenced by a sent reply and cannot be deleted."}),
        409,
    )


@api.get("/messages")
def list_messages():
    return jsonify(_mail().list_messages())


@api.get("/messages/<message_id>")
def get_message(message_id: str):
    return jsonify(_mail().get_message(message_id))


@api.get("/templates")
def list_templates():
    return jsonify(_mail().list_templates())


def _template_input():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()
    body = (payload.get("body") or "").strip()
    if not name or not body:
        return None, (jsonify({"error": "name and body are required"}), 400)
    return (name, description, body), None


@api.post("/templates")
def create_template():
    data, err = _template_input()
    if err:
        return err
    return jsonify(_mail().create_template(*data)), 201


@api.put("/templates/<template_id>")
def update_template(template_id: str):
    data, err = _template_input()
    if err:
        return err
    return jsonify(_mail().update_template(template_id, *data))


@api.delete("/templates/<template_id>")
def delete_template(template_id: str):
    _mail().delete_template(template_id)
    return "", 204


@api.post("/messages/<message_id>/suggest")
def suggest(message_id: str):
    message = _mail().get_message(message_id)
    templates = _mail().list_templates()
    result = suggest_templates(_provider(), message, templates)
    # Names and placeholders come along so the frontend does not need a
    # second lookup to render the cards or gate the send button.
    # agent_name is excluded because it is injected from config at draft
    # time and never reviewed by the agent.
    by_id = {t["id"]: t for t in templates}
    for c in result["candidates"]:
        template = by_id[c["template_id"]]
        c["template_name"] = template["name"]
        c["placeholders"] = [p for p in template["placeholders"] if p != "agent_name"]
    result["low_confidence"] = result["candidates"][0]["confidence"] < 0.5
    return jsonify(result)


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
    template_id = payload.get("template_id") or None
    return jsonify(_mail().send_reply(message_id, body, template_id)), 201
