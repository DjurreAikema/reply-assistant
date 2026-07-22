import logging
import os
import sys
from pathlib import Path

from flask import Flask

from .llm import ProviderNotReady, get_provider
from .services.mail_service import JsonMailService

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def create_app() -> Flask:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )

    app = Flask(__name__)

    provider = get_provider()
    # Fail here with the exact fix, not on the first suggest call. A dead
    # Ollama surfacing as a mysterious 500 mid-demo is the thing this
    # prevents. SKIP_LLM_CHECK exists only so automated tests can build
    # the app without a live model server.
    if os.environ.get("SKIP_LLM_CHECK") != "1":
        try:
            provider.check_ready()
        except ProviderNotReady as exc:
            print(f"\nStartup check failed for provider '{provider.name}':", file=sys.stderr)
            print(f"  {exc}\n", file=sys.stderr)
            sys.exit(1)

    logging.getLogger("replybot").info("llm provider: %s", provider.name)

    app.extensions["llm_provider"] = provider
    app.extensions["mail_service"] = JsonMailService(DATA_DIR)

    from .routes import api

    app.register_blueprint(api)
    return app
