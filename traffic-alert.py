#!/usr/bin/python3
import googlemaps, requests, os, logging, sys, pytz
from tinydb import TinyDB, Query
from datetime import date, datetime

# Init variables and load from env var
API_KEY = os.environ.get('API_KEY')
DATA_DIR = os.environ.get('DATA_DIR')
london_timezone = pytz.timezone("Europe/London")
theDate = date.today()
today = str(theDate)
weekday = theDate.weekday()
timestamp = datetime.now(london_timezone)
stateDB = TinyDB(DATA_DIR+'state.json')
dataDB = TinyDB(DATA_DIR+'data.json')
url = 'https://ntfy.sh/towcestera5alerts'
gmaps = googlemaps.Client(key=API_KEY)
racecourse = (52.122191, -0.973226)
newroundabout = (52.11732206783605, -0.9637802399721431)
stonyRoundabout = (52.066852, -0.871330)
distance_threshold = 8500

# Init the logger
file_handler = logging.FileHandler(filename=DATA_DIR+'log')
stdout_handler = logging.StreamHandler(stream=sys.stdout)
handlers = [file_handler, stdout_handler]
logging.basicConfig(handlers=handlers,
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)

# Init the DB
State = Query()
state = stateDB.search(State.date == today)
if state:
    state = state[0]['state']
if state == []:
    # print('its a new day')
    logging.info('Its a new day, state is %s', state)
    stateDB.truncate()
    stateDB.insert({'state': 0, 'date': today})
    state = 0

# Main run
result = gmaps.distance_matrix(newroundabout, stonyRoundabout, departure_time="now")

time = result["rows"][0]["elements"][0]["duration_in_traffic"]["value"]
trafficText = result["rows"][0]["elements"][0]["duration_in_traffic"]["text"]
baseline = result["rows"][0]["elements"][0]["duration"]["value"]
distance = result["rows"][0]["elements"][0]["distance"]["value"]
status = result["rows"][0]["elements"][0]["status"]
status2 = result["status"]
traffic = time-baseline

# Saving the duration for future work
dataDB.insert({'duration': time, 'date': str(timestamp), 'day': weekday})

logging.info('Difference is %s, TrafficTime is %s, Baseline is %s, distance is %s, status is %s, overalstatus is %s', str(traffic), str(time), str(baseline), str(distance), status, status2)

# If the Traffic is more than 10 mins
if distance > distance_threshold:
    if state < 3:
        logging.info('Traffic is terrible: %s', trafficText)
        stateDB.update({'state': 3}, State.date == today)
        x = requests.post(url, "Heavy traffic means A5 is no longer viable\nTravel time is currently: "+trafficText, headers={"Title": "Traffic is terrible", "Tags": "rotating_light,construction"})
        quit()
elif (traffic >= 600) and (distance <= distance_threshold):
    if state < 2:
        logging.info('Traffic is bad: %s', trafficText)
        stateDB.update({'state': 2}, State.date == today)
        x = requests.post(url, "Travel time is currently: "+trafficText, headers={"Title": "Traffic is bad!", "Tags": "rotating_light"})
        quit()
elif (traffic >= 300) and (distance <= distance_threshold):
    if (state > 1) and (traffic < 500):
        logging.info('Traffic is calming: %s', trafficText)
        stateDB.update({'state': 1}, State.date == today)
        x = requests.post(url, "Travel time is currently: "+trafficText, headers={"Title": "Traffic is calming", "Tags": "face_exhaling"})
        quit()
    if state < 1:
        logging.info('Traffic is building: %s', trafficText)
        stateDB.update({'state': 1}, State.date == today)
        x = requests.post(url, "Travel time is currently: "+trafficText, headers={"Title": "Traffic is building", "Tags": "blue_car"})
        quit()
elif (traffic < 300) and (distance <= distance_threshold):
    if state > 0:
        logging.info('Traffic is normal: %s', trafficText)
        stateDB.update({'state': 0}, State.date == today)
        x = requests.post(url, "Travel time is currently: "+trafficText, headers={"Title": "Traffic is back to normal", "Tags": "white_check_mark"})
        quit()