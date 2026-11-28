import os
import re
from flask import Flask, request

# (code, footer label), in footer order
LANGUAGES = [("en", "🇺🇸 EN"), ("de", "🇩🇪 DE"), ("es", "🇲🇽 ES")]

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY=os.getenv("SECRET_KEY", "notreallyasecret")
    )

    # ensure the instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # apply the blueprints to the app
    from perez import about, contact, index, projects, resume, de, es
    for module in (about, contact, index, projects, resume, de, es):
        app.register_blueprint(module.bp)

    @app.context_processor
    def inject_languages():
        """Tells the footer which language is showing and where the others are.

        English pages live at the root; translations under /de and /es.
        """
        path = request.path
        m = re.match(r"^/(de|es)(?=/|$)", path)
        current = m.group(1) if m else "en"
        base = (path[m.end():] or "/") if m else path
        languages = [
            (code, label, base if code == "en" else f"/{code}{base}")
            for code, label in LANGUAGES
        ]
        return dict(current_lang=current, languages=languages)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0')
