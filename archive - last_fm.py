# ---LAST FM SETUP ---
LASTFM_URL = 'http://ws.audioscrobbler.com/2.0/'
LASTFM_API = "no"

def fetch_artist_birth_info(new_artist: dict):
    params = {
        'method': 'artist.getInfo',
        'artist': new_artist["name"],
        'api_key': LASTFM_API,
        'format': 'json'
    }
    
    with httpx.Client() as client:
        response = client.get(LASTFM_URL, params=params)
        if response.status_code != 200:
            new_artist["birthdate"] = "ERROR LOADING ARTIST IN LAST FM"
            new_artist["birth_loc"] = "ERROR LOADING ARTIST IN LAST FM"
            
        else:
            data = response.json()
            artist_info = data['artist']
            new_artist["bio"] = artist_info.get('bio', {})

        return new_artist

