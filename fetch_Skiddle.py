import requests
from pymongo import MongoClient

API_KEY = '868953c38e260ec985ae809bfd99d9a9'
MONGO_URI = 'mongodb://localhost:27017/eventiq'

client = MongoClient(MONGO_URI)
db = client.get_database()

clean_events = []

Local_lat = 54.5973
Local_long = -5.9301

def fetch_skiddle_events():
    print ("Fetching events for Belfast...")

    url = "https://www.skiddle.com/api/v1/events/"
    params = {
        'api_key': API_KEY,
        'latitude': Local_lat,
        'longitude': Local_long,
        'radius': 10,
        'eventcode': 'LIVE',
        'limit': 50,
        'description': 1
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        print("DEBUG RAW RESPONSE:", data)
    except Exception as e:
        print(f"Error connection to the API")
        return
    
    if 'results' not in data or len(data['results']) == 0:
        print("No events found.")
        return
    
    for item in data['results']:
        try:
            image = item.get('largeimageurl','')
            if not image:
                image = "https://via.placeholder.com/300"

            new_event = {
                "title": item['eventname'],
                "category": item.get('bgs', 'Music'),
                "Location": "Belfast",
                "venue": item['venue']['name'],
                "date": item['date'],
                "time": item['openingtimes']['doorsopen'],
                "price": item.get('entryprice', '0.00'),
                "description": item.get('description', 'No description available.'),
                "image": image,
                "ticket_link": item['link'],
                "source": "Skiddle"
            }
            clean_events.append(new_event)

        except Exception as e:
            print(f"Skipped event {item.get('eventname')} due to error: {e}")
            continue

    if clean_events:
        db.events.delete_many({"source": "Skiddle"})

        db.events.insert_many(clean_events)
        print(f"Success! Imported {len(clean_events)} events from Skiddle.")
    else:
        print("Found events but failed to process them.")

if __name__ == "__main__":
    fetch_skiddle_events()

