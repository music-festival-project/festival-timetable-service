"""Flask configuration variables."""
from os import environ, path

from dotenv import load_dotenv

BASE_DIR = path.abspath(path.dirname(__file__))
load_dotenv(path.join(BASE_DIR, ".env"))

class Config:
    """Set Flask configuration from .env file."""

    # General Config
    ENVIRONMENT = environ.get("ENVIRONMENT")

    # Flask Config
    FLASK_APP = "wsgi.py"
    FLASK_DEBUG = environ.get("FLASK_DEBUG")
    SECRET_KEY = environ.get("SECRET_KEY")
    
    FLASK_ADDRESS = environ.get("FLASK_ADDRESS")
    PORT = environ.get("PORT")
    
    # Database
    MONGO_URI = environ.get("MONGO_URI")
    # SQLALCHEMY_DATABASE_URI = environ.get("SQLALCHEMY_DATABASE_URI")
    # SQLALCHEMY_ECHO = False
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Microservice discovery
    # this is where it can potentially happen
    # if we dont use any environment files or anything like that
    # RECOMMENDER_URL = "127.0.0.1:8001"