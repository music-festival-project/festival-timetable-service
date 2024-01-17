"""App entry point."""
from flask_timetable_service import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host='127.0.0.1', port='8000', debug=True)