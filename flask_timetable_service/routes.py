import logging
from pathlib import Path
from config import Config

import json
import requests
import pandas as pd

from flask import current_app as app
from flask import Response, jsonify
from flask_cors import cross_origin

import flask_timetable_service.recommender as recommender

SPOTIFY_SERVICE = Config.SPOTIFY_SERVICE
ALLOWED_ORIGINS = "http://localhost:3000"

logger = logging.getLogger(__name__)

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
@cross_origin(origins=ALLOWED_ORIGINS)
def get_festival_timetable(festival: str, day: str):
    ## get list of tracks from spotify service
    file_path = festival_path_processing(festival, day)
    if Path.exists(file_path) == False: 
        return Response(status=404, response=str(file_path))
    file_contents = get_file_contents(file_path)
    artist_list = [item["artist"] for item in file_contents]
    headers = {'Content-Type': 'application/json'}
    res = requests.post(f"{SPOTIFY_SERVICE}/artist/search/",
                  headers=headers, json=artist_list)
    
    ## get list of artist names from festival
    ## extract audio features for both
    ## feed them as input to the algorithm
    spotify_dict = res.json()    
    scored_timetable = merge_spotify_dict_and_restructured_timetable(spotify_dict, file_contents)
    save_json_cache(f"restructured_timetable_{festival}_{day}.json", scored_timetable)        
    return scored_timetable
    
@app.route('/recommend/<festival>/<day>/<playlist>', methods=['GET'])
@cross_origin(origins=ALLOWED_ORIGINS)
def get_playlist_recommendation(festival: str, day: str, playlist: str):
    ## get artist ids
    file_path = f'restructured_timetable_paaspop_{day}.json'
    assert Path(file_path).exists()
    file_contents = get_file_contents(file_path)
    
    # TODO:
    # For future change when recommender gets refactored to only
    # do the scoring. It currently is taking in a playlist id and a 
    # day and reading/processing it all. That's too much for what it is meant to do.
    # artist_id_list = []
    # for _, value in file_contents.items():
    #     for entry in value:
    #         artist_id_list.append(entry["artist_id"])    
    
    # headers = {'Content-Type': 'application/json'}
    # artist_features_res = requests.post(f"{SPOTIFY_SERVICE}/artist/audio_features/",
    #                                     headers=headers, json=artist_id_list)
    
    # the `do_recommend` is a "full" call of the recommendation steps.
    # It does a call to get the festival data and the stage pivoted data
    # Then processes for the "average feature data" of per the  artist.
    logger.error("Attempting to call recommender on")
    recommendation_stuff = recommender.do_recommend(playlist_id=playlist, day=day)
    logger.error("Successfully got recommendation to not shit")
    logger.error(f"Type recommendation stuff: {type(recommendation_stuff)}")
    logger.error(f"Recommendation stuff returned is\n{recommendation_stuff}\n\n")
    dfs = []
    for stage, data in file_contents.items():
        timetable_df = pd.DataFrame(data)
        timetable_df["stage"] = stage
        dfs.append(timetable_df)

    timetable_df = pd.concat(dfs)
    timetable_df = timetable_df[timetable_df["artist"].isin(recommendation_stuff)]
    recommender_outie = {}
    stage_groups = timetable_df.groupby("stage")
    for staageeh, dater in stage_groups:
        fermerter_dater = list(dater.to_dict('index').values())
        recommender_outie[staageeh] = fermerter_dater
    return recommender_outie

    

def make_restructured_timetable_df(file_contents):
    return pd.DataFrame(file_contents)
    
    
def get_file_contents(file_path):
    with open(file_path) as f:
        return json.load(f)
    
def save_json_cache(filename: str, to_save):
    with open(filename, 'w') as f:
        json.dump(to_save, f)
    

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
    res = requests.post(f"{SPOTIFY_SERVICE}/artist/search/",
                  headers=headers,
                  json=data)
    return res.json()
    
def festival_path_processing(festival: str, day: str):
    abs_path = Path(__name__).parent / "data"
    filename = f"{festival}_{day}.json"
    file_path = abs_path / filename
    return file_path