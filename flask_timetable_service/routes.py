from flask import current_app as app
import requests

@app.route("/")
def index():
    return "hello this is a flask app"

@app.route('festival/<festival_id>', methods=['GET'])
def get_festival_timetable(festival_id):
    # search festival id in mongo document
    # jsonify this string
    return f"Product ID: {festival_id}"