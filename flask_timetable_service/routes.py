from flask import current_app as app
from flask import Response, jsonify
from flask_cors import cross_origin
from pathlib import Path
from config import Config
import json
import requests as rq
import pandas as pd

from .playlist import Playlist

SPOTIFY_SERVICE = Config.SPOTIFY_SERVICE

@app.route("/")
def index():
    return "hello this is a flask app"

@app.route("/get_playlists", methods=['GET'])
@cross_origin()
def get_playlists_to_filter():
    abs_path = Path(__name__).parent / "data"
    filename = f"my_cleaned_playlist.pkl"
    file_path = abs_path / filename
    playlist_df = pd.read_pickle(file_path)
    playlists = {}
    for _, row in playlist_df.iterrows():
        playlist_name = row['name']
        playlist_id = row['id']
        playlist_image = row['images']

        playlists[playlist_id] = {
            "name": playlist_name,
            "image": playlist_image
        }
    return playlists
    
@app.route('/festival/<festival>/<day>', methods=['GET'])
@cross_origin(origins="http://localhost:3000")
def get_festival_timetable(festival: str, day: str):
    file_path = festival_path_processing(festival, day)
    if Path.exists(file_path) == False: 
        return Response(status=404, response=str(file_path))
    with open(file_path) as user_file:
        file_contents = json.load(user_file)
    
    restructured_timetable = {"timetable": {}}
    # Group the entries by stage
    for entry in file_contents:
        stage = entry["stage"]
        if stage not in restructured_timetable["timetable"]:
            restructured_timetable["timetable"][stage] = []
        restructured_timetable["timetable"][stage].append({
            "artist": entry["artist"],
            "start": entry["start"],
            "end": entry["end"]
        })
    return restructured_timetable
    
@app.route('/recommend/<festival>/<day>/<playlist>', methods=['GET'])
@cross_origin(origins="http://localhost:3000")
def get_playlist_recommendation(festival: str, day: str, playlist: str):
    ## get list of tracks from spotify service
    file_path = festival_path_processing(festival, day)
    if Path.exists(file_path) == False: 
        return Response(status=404, response=str(file_path))
    file_contents = get_file_contents(file_path)
    artist_list = [item["artist"] for item in file_contents]
    headers = {'Content-Type': 'application/json'}
    res = rq.post(f"{SPOTIFY_SERVICE}/artist/search/",
                  headers=headers, json=artist_list)
    
    ## get list of artist names from festival
    ## extract audio features for both
    ## feed them as input to the algorithm
    spotify_dict = res.json()    
    scored_timetable = merge_spotify_dict_and_restructured_timetable(spotify_dict, file_contents)        
    return scored_timetable


def make_restructured_timetable_df(file_contents):
    return pd.DataFrame(file_contents)
    
    
def get_file_contents(file_path):
    with open(file_path) as f:
        return json.load(f)
    

def merge_spotify_dict_and_restructured_timetable(spotify_dict, file_contents):
    timetable_df = make_restructured_timetable_df(file_contents)
    spotify_df = pd.DataFrame(spotify_dict)
    spotify_df = spotify_df.rename(columns={"name":"artist"})
    df = spotify_df.merge(timetable_df, on="artist")
    df = df.sort_values(by=["start", "end"])
    groups = df.groupby("stage")
    output_dict = {}
    for stage, dater in groups:
        output_dict[stage] = list(dater.to_dict("index").values())
    return output_dict


@app.route('/info/artists/<festival>/<day>')
def get_festival_artists(festival: str, day: str):
    file_path = festival_path_processing(festival, day)
    if Path.exists(file_path) == False: 
        return Response(status=404, response=str(file_path))
    with open(file_path) as user_file:
        file_contents = json.load(user_file)
    artist_list = []
    for item in file_contents:
        artist_list.append(item["artist"])
    artist_name_set = list(set(artist_list))
    headers = {'Content-Type': 'application/json'}
    data = {}
    data["search_strings"] = artist_name_set
    res = rq.post(f"{SPOTIFY_SERVICE}/artist/search/",
                  headers=headers,
                  json=data)
    return res.json()
    
def festival_path_processing(festival: str, day: str):
    abs_path = Path(__name__).parent / "data"
    filename = f"{festival}_{day}.json"
    file_path = abs_path / filename
    return file_path