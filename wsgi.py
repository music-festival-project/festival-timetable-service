"""App entry point."""
from flask_timetable_service import create_app
from config import Config

app = create_app()

if __name__ == "__main__":
    app.run(host=Config.FLASK_ADDRESS, port=Config.PORT, debug=Config.FLASK_DEBUG)