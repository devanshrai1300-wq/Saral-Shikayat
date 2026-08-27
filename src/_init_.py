import os
from flask import Flask
from src.db import init_db, close_db
from src.routes.api import api_bp

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    )
    
    with app.app_context():
        init_db()

    app.teardown_appcontext(close_db)
    app.register_blueprint(api_bp)
    return app