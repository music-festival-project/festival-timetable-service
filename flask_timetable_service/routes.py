from flask import current_app as app
import requests
import requests
import json

@app.route("/")
def index():
    return "hello this is a flask app"

@app.route('/festival/<festival_id>', methods=['GET'])
def get_festival_timetable(festival_id):
    
    ...