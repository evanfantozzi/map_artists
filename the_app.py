import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, redirect, session, url_for, render_template_string
import random
from pathlib import Path
import json
import httpx
import time

HTML_PATH = Path(__file__).parent / "List_Top_Artists.html"
ARTISTS_PATH = Path(__file__).parent / "artists.json"

# --- SPOTIFY API CREDENTIALS ---
SPOTIFY_CLIENT_ID = "no"
SPOTIFY_CLIENT_SECRET = "no"
SPOTIFY_REDIRECT_URI = "http://localhost:8080/callback"

# --- FLASK APP CONFIG ---
app = Flask(__name__)
app.secret_key = str(random.randint(1, 1000000000))
app.config['SESSION_COOKIE_NAME'] = "Spotify Cookie"

# --- SPOTIPY AUTH SETUP ---
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-top-read"  # Permission to read user's top artists
)

# --- MUSICBRAINZ ---
MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/artist/?query=artist:"

def fetch_artist_info(new_artist):
    # Search for the artist using the MusicBrainz API
    url = MUSICBRAINZ_URL + f'{new_artist["name"]}&fmt=json'

    with httpx.Client() as client:
        response = client.get(url)

    # Check if the response is successful
    if response.status_code == 200:
        data = response.json()

        # Check if there are results
        if 'artists' in data and data['artists']:
            artist = data['artists'][0]  # Take the first result (best match)

            # Get the artist's birth date and location (if available)
            new_artist["birthdate"] = artist.get('life-span', {}).get('begin', '') 
            
            birth_location = artist.get('begin-area', {}).get('name', '') 
            birth_country = artist.get('area', {}).get("name", "Country Unknown")
            birth_loc_country = birth_location + ", " + birth_country
            new_artist['birth_location'] = birth_loc_country
            
        else:
            new_artist["birthdate"] = "ERROR IN MUSICBRAINZ"
            new_artist['birth_location'] = "ERROR IN MUSICBRAINZ"
            
    return new_artist

def add_artists_to_directory(new_artists: set):
    # Load in existing artists
    with open(ARTISTS_PATH, "r", encoding="utf-8") as f:
        directory_artists = json.load(f)
    
    # Go through new artists, add in 
    for id, new_artist in new_artists.items():
        if id not in directory_artists:
            directory_artists[id] = fetch_artist_info(new_artist)
            
            
    with open(ARTISTS_PATH, "w") as f:
        json.dump(directory_artists, f, indent=1)
            

def fetch_top_artists(client):
    '''
    Stores top artists for short, medium, long term in session
    '''
    # Fetch top artists for all time ranges
    all_artists = {}
    time_ranges = ['short_term', 'medium_term', 'long_term']
    
    for time_range in time_ranges:
        results = client.current_user_top_artists(limit=50, time_range=time_range)
        
        artists = []
        for artist in results["items"]:
            
            # Add to all_artists for directory of artist information
            id = artist["id"]
            all_artists[id] = artist
            
            # Add to list for time range
            artists.append(artist["name"])
        session[time_range] = artists  # Store the artists for each time range in session
        
    # Add artists to directory
    add_artists_to_directory(all_artists)

@app.route("/")    
def login():
    '''
    Authorize login to Spotify
    '''
    auth_url = sp_oauth.get_authorize_url()  # Get the URL to redirect the user to Spotify's login page
    return redirect(auth_url)  # Redirect the user to Spotify's authorization page

@app.route("/callback")
def login_callback():
    '''
    Callback page: get access token and fetch top artists
    '''
    # After Spotify redirects back with the token
    token_info = sp_oauth.get_access_token(request.args['code'])
    session["token_info"] = token_info

    # Initialize Spotipy client with the access token
    sp = spotipy.Spotify(auth=token_info["access_token"])
    
    fetch_top_artists(sp)

    return redirect(url_for('top_artists', time_range='long_term'))  # Default to long_term

@app.route("/top-artists/<time_range>")
def top_artists(time_range: str="long_term"):
    '''
    Given a time range of long_term, medium_term, or short_term, 
    '''
    # Ensure time_range is one of the valid options
    if time_range not in ['long_term', 'medium_term', 'short_term']:
        time_range = 'long_term'

    # Check if token_info is in session
    token_info = session.get("token_info", None)
    if not token_info:
        return redirect(url_for("login"))  # If token is missing, redirect to login

    # Check if the data for the time_range is stored in session
    artists = session.get(time_range, None)
    if not artists:
        return redirect(url_for('login_callback')) 

    # Bring in HTML
    with open(HTML_PATH, 'r') as f:
        html_content = f.read()

    return render_template_string(html_content, artists=artists, time_range=time_range)

if __name__ == "__main__":
    app.run(port=8080, debug=True)  # Run the Flask app on http://localhost:8080