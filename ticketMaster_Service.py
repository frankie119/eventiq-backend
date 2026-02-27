import requests
from pymongo import MongoClient

TM_API_Key = 'y8srBTGHb7cdsnEqKGMx5WGKncHMEaDz'
MONGO_URI = 'mongodb://localhost:27017/eventiq'

client = MongoClient(MONGO_URI)
db = client.get_database()

# Function to clean and map event data
def map_ticketmaster_data(item):
    
    genre = item.get('classifications', [{}])[0].get('genre', {}).get('name', 'Music')
    venues = item.get('_embedded', {}).get('venues', [{}])
    venue_name = venues[0].get('name', 'Venue TBA') if venues else 'Venue TBA'
    dates = item.get('dates', {}).get('start', {})
    return {
        "title": item.get('name', 'Unknown Event'),
        "category": genre,
        "location": "Belfast",
        "venue": venue_name,
        "date": dates.get('localDate', 'TBA'),
        "time": dates.get('localTime', 'TBA'),
        "price": "Check Ticketmaster",
        "description": item.get('info', 'Real Belfast niche event'),
        "image": item.get('images', [{}])[0].get('url', 'https://via.placeholder.com/300'),
        "ticket_link": item.get('url', 'https://www.ticketmaster.ie'),
        "source": "Ticketmaster"
    } 
      

def fetch_ticketmaster_events():
    print("Fetching Belfast events from ticketmaster")
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        'apikey': TM_API_Key, 
        'latlong': '54.5973,-5.9301',
        'radius': '20',
        'unit': 'miles',
        'locale': '*',
        'size': 20
    }

    response = requests.get(url, params=params).json()

    print("DEBUG RAW RESPONSE:", response)

    # Check If ticketmaster found anything
    if '_embedded' not in response:
        print("No ticketmaster events found.")
        return
    
    tm_events = [map_ticketmaster_data(event) for event in response['_embedded']['events']]

    if tm_events:
        db.events.delete_many({"source": "Ticketmaster"})
        db.events.insert_many(tm_events)
        print(f"Sucess! Imported {len(tm_events)} events from Ticketmaster. ")

if __name__ == "__main__":
    fetch_ticketmaster_events()