import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
#################### data ####################

# spotify api credentials (move to env/user dependent)

SPOTIPY_CLIENT_ID="c19fdff9cb234c7aa3fab430b3229293"
SPOTIPY_CLIENT_SECRET="dde8da4fc7964baaba18689d172a4464"
SPOTIPY_REDIRECT_URI="http://localhost:8888/callback"

CLIENT_ID=SPOTIPY_CLIENT_ID
CLIENT_SECRET=SPOTIPY_CLIENT_SECRET

# spotify api instance
spotipyinstance = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                               client_secret=CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope ='user-library-read user-top-read'))


SAMPLE_OUTPUT_PATH = Path(__file__).parent.parent / Path('sample_output')


desired_features = ['danceability', 'energy', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence']


def get_top_tracks_playlist(playlist_id, limit):
    results = spotipyinstance.playlist_tracks(playlist_id, limit=limit)
    return [track['track'] for track in results['items']]


def get_song_features_from_playlist(playlist_id, limit=5):
    top_tracks = get_top_tracks_playlist(playlist_id, limit)

    dfs = []
    for track in top_tracks:
        track_features = spotipyinstance.audio_features(track['id'])
        if track_features:
            dfs.append(pd.DataFrame(track_features))
    return pd.concat(dfs)


def get_artist_track_feature(artist, num_tracks=2):
    results = spotipyinstance.search(q=f'artists:{artist}', type='artist')
    results = results['artists']['items']
    if len(results) < 1:
        raise ValueError(f"No artist found with name {artist}")
    result = results[0]
    
    # Name of artist and returned result must be exact match
    assert result['name'].lower() == artist.lower()
    artist_id = result['id']
    
    # Get the num_tracks number of tracks from artist and 
    # get each track's features
    top_tracks = get_top_tracks_artist(artist_id, num_tracks)
    track_features = {}
    for track in top_tracks:
        track_id = track['id']
        track_name = track['name']
        track_feature = spotipyinstance.audio_features(track_id)
        track_features[track_name] = track_feature
    return track_features


def get_top_tracks_artist(artist_id, limit):
    results = spotipyinstance.artist_top_tracks(artist_id)
    return results['tracks'][:limit]


def make_average_features_for_artist_list(artists):
    dfs = []
    for artist in artists:
        try:
            artist_track_features= get_artist_track_feature(artist)
            for track_name, features in artist_track_features.items():
                df = pd.DataFrame(features)
                df = df.assign(name=track_name)
                df = df.assign(artist=artist)
                dfs.append(df)
            print(f"Retrieved {artist=}")
        except Exception as err:
            print(f"Failed to retrieve {artist=}")
            print(f"{type(err)} returned {err}")
    return pd.concat(dfs)


def read_artist_feature_data(day):
    """Reads artist feature data for a given day csv. 
    If the data exists, read the cached file. Otherwise, 
    run get the artist data and save."""
    file = SAMPLE_OUTPUT_PATH / Path(f"{day}_artist_average_features.pkl")
    if file.exists():
        print(f"Cached file for {day} found. Reading cached file")
        with open(file, "rb") as f:
            return pd.read_pickle(f)
    else:
        csv_path = Path(f'paaspop_{day}.csv')
        csv_file_path = SAMPLE_OUTPUT_PATH / csv_path
        if csv_file_path.exists():
            festival_data = pd.read_csv(csv_file_path)
        else:
            raise FileNotFoundError("Expected data for {day=} not found")
        artists = festival_data['artist'].unique()
        df = make_average_features_for_artist_list(artists)
        df.to_pickle(file)
        return df
    
    
def get_similarities_for_playlist(playlist_id, day):
    print(f"Getting similarities for {day=}")
    playlist_feature_df = get_song_features_from_playlist(playlist_id)
    avg_playlist_feature_df = playlist_feature_df[desired_features].mean()
    playlist_vector = np.array(avg_playlist_feature_df).reshape(1, -1)
    print("Created playlist_vector for input playlist")
    
    df = read_artist_feature_data(day)
    if len(df) == 0:
        print(f"Failed to retrieve df for {day=}")
        return None
    print(f"Successfully retrieved artist feature data for day {day=}")
    df = df[~df["artist"].isna()]
    avg_artist_features = df.groupby("artist")[desired_features].mean()
    artist_similarity = {}
    for artist, data in avg_artist_features.iterrows():
        artist_vector = np.array(data).reshape(1, -1)
        similarity = cosine_similarity(artist_vector, playlist_vector)[0][0]
        artist_similarity[artist] = similarity
    return artist_similarity


def get_festival_data(day):
    path = Path(f'paaspop_{day}.json')
    file_path = SAMPLE_OUTPUT_PATH / path
    return pd.read_json(file_path)


def pivot_festival_data_to_stage_column(df):
    """Given an input festival date dataframe, pivot the data.
    
    The resulting dataframe has the "start" and "end" as the 
    new indexes, and the columns are the stages with the artist 
    then in the stages.
    """
    return (
        df
        .pivot(
            index=["start", "end"],
            values="artist",
            columns="stage")
        .reset_index()
    )

    
def read_artist_average_feature_data(day):
    artist_track_score = read_artist_feature_data(day)
    df = artist_track_score.groupby("artist")[desired_features].mean()
    return df


def get_playlist_feature_vector(playlist_id):
    playlist_feature_df = get_song_features_from_playlist(playlist_id)
    avg_playlist_feature_df = playlist_feature_df[desired_features].mean()
    playlist_vector = np.array(avg_playlist_feature_df).reshape(1, -1)
    return playlist_vector
  
  
def prepare_artist_similarity_df(stage_df, avg_artist_features, playlist_vector):
    """This is the function which actually maps each artist to the playlist vector
    to produce a score and associate that with the entry in the time table.
    """
    dfs = []
    for _, data in stage_df.iterrows():
        start_time = data["start"]
        end_time = data["end"]
        data = data.drop(columns=["start", "end"])
        stage_data = data
        # Makes a list of each row in time and removes stages without artists
        # This way we have just a list of artists playing at this time
        performing_artists = dict(stage_data[~stage_data.isna()])
        
        # Iterate through the artists performing at a given
        for stage, artist in performing_artists.items():
            prefered_data = {}
            
            # If artist is one with a calculated average feature
            #   meaning, the artist has data on spotify.
            if artist in list(avg_artist_features.index):
                artist_vector_data = avg_artist_features.loc[artist]
                artist_vector = np.array(artist_vector_data).reshape(1, -1)
                similarity = cosine_similarity(artist_vector, playlist_vector)[0][0]
                prefered_data["stage"] = stage
                prefered_data["artist"] = artist
                prefered_data["score"] = similarity
                prefered_data["start"] = start_time
                prefered_data["end"] = end_time
                df = pd.DataFrame([prefered_data])
                dfs.append(df)
    artist_similarity_df = pd.concat(dfs)
    return artist_similarity_df


def get_top_artist_from_scored_stage_df(df):
    score_sorted_df = df.sort_values(by='score', ascending=False)
    top_artist = score_sorted_df.groupby('start').head(1)
    top_artist = top_artist.drop(columns=["score"])
    return top_artist


def cleanup_df_start_end_times(df):
    df = df.sort_values(by=["stage", "start", "end"]).reset_index(drop=True)
    return df
    

def do_recommend(playlist_id, day = "friday"):
    festival_data = get_festival_data(day=day)
    print(f"Successfully got data for {day}")
    stage_df = pivot_festival_data_to_stage_column(festival_data)
    print(f"Pivoted {day} festival data to have artist information per time available.")
    avg_artist_features = read_artist_average_feature_data(day)
    
    
    print(f"Calculated average feature data for artists with identified spotifies")
    playlist_vector = get_playlist_feature_vector(playlist_id)
    
    
    print(f"For playlist: {playlist_id=} identified vectors to be {playlist_vector}")
    similarity_df = prepare_artist_similarity_df(stage_df, avg_artist_features, playlist_vector)
    print(f"Extrapolated similarity data for performance on {day}")
    top_artist_df = get_top_artist_from_scored_stage_df(similarity_df)
    print(f"Determined top artist based on similarity score is  {top_artist_df}")
    df = cleanup_df_start_end_times(top_artist_df)
    recommended_artist_list = list(df["artist"])
    return recommended_artist_list 
