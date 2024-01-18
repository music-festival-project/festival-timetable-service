"""Initialize Flask app."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pymongo.mongo_client import MongoClient
from config import Config

db = MongoClient(Config.MONGO_URI)

def create_app():
    """Initialize core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object("config.Config")


    with app.app_context():
        from . import routes  # Import routes

        festival = db['festivals']

        return app