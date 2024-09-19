#!/usr/bin/python3
import googlemaps, requests, os
from tinydb import TinyDB, Query
from datetime import date

# Init variables and load from env var
API_KEY = os.environ.get('API_KEY')
DATA_DIR = os.environ.get('DATA_DIR')
today = str(date.today())
stateDB = TinyDB(DATA_DIR)
url = 'https://ntfy.sh/towcestera5alerts'
gmaps = googlemaps.Client(key=API_KEY)
racecourse = (52.122191, -0.973226)
stonyRoundabout = (52.066852, -0.871330)

# Init the DB
State = Query()
state = stateDB.search(State.date == today)
if state:
    state = state[0]['state']
if state == []:
    print('its a new day')
    stateDB.truncate()
    stateDB.insert({'state': 0, 'date': today})
    state = 0

# Main run
result = gmaps.distance_matrix(racecourse, stonyRoundabout, departure_time="now")

time = result["rows"][0]["elements"][0]["duration_in_traffic"]["value"]
trafficText = result["rows"][0]["elements"][0]["duration_in_traffic"]["text"]
baseline = result["rows"][0]["elements"][0]["duration"]["value"]
traffic = time-baseline

print("Current Traffic: "+str(traffic))

# If the Traffic is more than 10 mins
if traffic > 600:
    if state < 2:
        print("Traffic is more than 10 mins delay")
        stateDB.update({'state': 2}, State.date == today)
        x = requests.post(url, "Travel time is currently: "+trafficText, headers={"Title": "Traffic is bad!", "Tags": "rotating_light,construction"})
        quit()
elif traffic > 300:
    if state > 1:
        print("Traffic is calming, but still 5 min delay")
        stateDB.update({'state': 1}, State.date == today)
        x = requests.post(url, "Travel time is currently: "+trafficText, headers={"Title": "Traffic is calming", "Tags": "rotating_light,face_exhaling"})
        quit()
    if state < 1:
        print("traffic is building, 5 min delay")
        stateDB.update({'state': 1}, State.date == today)
        x = requests.post(url, "Travel time is currently: "+trafficText, headers={"Title": "Traffic is building", "Tags": "rotating_light,face_exhaling"})
        quit()
else:
    if state > 0:
        print("Traffic is back to normal")
        stateDB.update({'state': 0}, State.date == today)
        x = requests.post(url, "Travel time is currently: "+trafficText, headers={"Title": "Traffic is back to normal", "Tags": "relieved"})
        quit()