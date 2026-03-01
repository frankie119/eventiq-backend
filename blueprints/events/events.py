from flask import Blueprint, jsonify, make_response, request
from bson import ObjectId
import globals
from decorators import jwt_required, admin_required
import os
from werkzeug.utils import secure_filename
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

events_bp = Blueprint("events_bp", __name__)

events = globals.db.events

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_ml_recommendations(user_interests_list, all_events_from_db):
    if not all_events_from_db:
        return []

    df = pd.DataFrame(all_events_from_db)
    
    if 'category' not in df.columns:
        df['category'] = ''
    if 'description' not in df.columns:
        df['description'] = ''
        
    df['combined_features'] = df['category'].fillna('') + " " + df['description'].fillna('')
    
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['combined_features'])
    
    user_query = " ".join(user_interests_list)
    user_vector = tfidf.transform([user_query])
    
    similarity_scores = cosine_similarity(user_vector, tfidf_matrix).flatten()
    df['score'] = similarity_scores
    
    # NEW FIX: Filter out any events that have a 0% match!
    df = df[df['score'] > 0.0]
    
    # Referencing the LCA paper directly for the weighting of these results
    recommended_df = df.sort_values(by='score', ascending=False).head(10)
    recommended_df = recommended_df.fillna('')
    
    return recommended_df.to_dict(orient='records')

@events_bp.route("/api/v1.0/events", methods=["POST"])
@admin_required
def add_event(data):
    try:
        data = request.form
        print("received keys:", list(data.keys()))

        required_fields = ["title", "category", "venue", "date", "price", "total_tickets"]
        if not all (field in data for field in required_fields):
            return make_response(jsonify({"error": "Missing required fields"}), 400)
        
        image_url = "https://via.placeholder.com/300"
        
        if 'event_image' in request.files:
            file = request.files['event_image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER,filename)
                file.save(file_path)
                image_url = f"http://localhost:5000/static/uploads/{filename}"
        new_event = {
            "title": data["title"],
            "category": data["category"],
            "venue": data["venue"],
            "location": data.get("location", "Belfast"),
            "date": data["date"],
            "time": data.get("time", "19:00"),
            "price": float(data["price"]),
            "total_tickets": int(data["total_tickets"]),
            "tickets_sold": 0,
            "description": data.get("description", ""),
            "image": image_url, 
            "source": "Manual"
        }

        result = events.insert_one(new_event)
        new_id = str(result.inserted_id)
        new_event["_id"] = new_id
        print("Event created:", new_event)
        return make_response(jsonify(new_event), 201)
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 500)

@events_bp.route("/api/v1.0/events", methods=["GET"])
def show_all_events():

    page_num = int(request.args.get('pn', 1))
    page_size = int(request.args.get('ps', 10))
    page_start = page_size * (page_num - 1)

    total_events = events.count_documents({}) 

    data_to_return = []
    for event in events.find().skip(page_start).limit(page_size):
        event['_id'] = str(event['_id'])
        event['tickets_left'] = event.get('total_tickets', 100) - event.get('tickets_sold', 0)
        event['image'] = event.get('image') or 'https://images.unsplash.com/photo-1540039155733-d7696e8abf5f?q=80&w=800&auto=format&fit=crop'
        data_to_return.append(event)

    return make_response(jsonify({
        "events": data_to_return,
        "total_events": total_events,
        "current_page": page_num,
        "total_pages": (total_events + page_size - 1) // page_size
    }), 200)
# Get One event 
@events_bp.route("/api/v1.0/events/<string:event_id>", methods=["GET"])
def show_one_event(event_id):
    try:
        event = events.find_one({"_id": ObjectId(event_id)})
    except Exception:
        return make_response(jsonify({"error": "Invalid event ID format"}), 400)
    if event is None:
        return make_response(jsonify({"error": "Event not found"}), 404)
    event["_id"] = str(event["_id"])
    event['tickets_left'] = event.get('total_tickets', 100) - event.get('tickets_sold', 0)
    event['image'] = event.get('image') or 'https://images.unsplash.com/photo-1540039155733-d7696e8abf5f?q=80&w=1600&auto=format&fit=crop'
    return make_response(jsonify(event), 200)

@events_bp.route("/api/v1.0/events/<id>/book", methods=["POST"])
def book_ticket(id):
    event = events.find_one({"_id": ObjectId(id)})

    if not event:
        return make_response(jsonify({"error": "Event not found"}), 404)
    tickets_sold = event.get("tickets_sold", 0)
    total_tickets = event.get("total_tickets", 100)

    if tickets_sold >= total_tickets:
        return make_response(jsonify({"error": "Sorry, this event is sold out!"}), 400)
    
    events.update_one(
        {"_id": ObjectId(id)},
        {"$inc": {"tickets_sold": 1}}
    )
    return make_response(jsonify({"message": "Ticket booked successfully!"}), 200)

@events_bp.route("/api/v1.0/events/recommend", methods=["POST"])
def recommend_events():
    data = request.json or {}
    user_interests = data.get("interests", [])
    
    if not user_interests:
        return make_response(jsonify({"error": "No interests provided"}), 400)

    all_events = list(events.find())
    scored_events = get_ml_recommendations(user_interests, all_events)

    for event in scored_events:
        event["_id"] = str(event["_id"])
        event["score"] = float(event["score"])

    # BULLETPROOF FIX: Manually force the CORS headers so the browser accepts the data
    response = make_response(jsonify(scored_events))
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, x-access-token")
    return response, 200

@events_bp.route("/api/v1.0/events/trending", methods=["GET"])
def trending_events():
    trending_cursor = events.find().sort("tickets_sold", -1).limit(5)

    trending_list = []
    for event in trending_cursor:
        event["_id"] = str(event["_id"])
        event['image'] = event.get('image') or 'https://images.unsplash.com/photo-1540039155733-d7696e8abf5f?q=80&w=800&auto=format&fit=crop'
        trending_list.append(event)
    return jsonify(trending_list), 200

@events_bp.route("/api/v1.0/events/<string:event_id>", methods=["DELETE"])
@admin_required
def delete_event(event_id, data):
    result = events.delete_one({"_id": ObjectId(event_id)})
    if result.deleted_count == 1:
        return make_response(jsonify( {} ), 204)
    else:
        return make_response(jsonify( {"error": "Invalid Event ID"}), 404)

        