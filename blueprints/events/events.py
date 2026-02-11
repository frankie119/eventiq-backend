from flask import Blueprint, jsonify, make_response, request
from bson import ObjectId
import globals
from decorators import jwt_required, admin_required

events_bp = Blueprint("events_bp", __name__)

events = globals.db.events

@events_bp.route("/api/v1.0/events", methods=["POST"])
@admin_required
def add_event(data):
    try:
        data = request.get_json() if request.is_json else request.form
        print("received keys:", list(data.keys()))

        required_fields = ["title", "category", "venue", "date", "price", "total_tickets"]
        if not all (field in data for field in required_fields):
            return make_response(jsonify({"error": "Missing required fields"}), 400)
        
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
            "image": data.get("image", "https://via.placeholder.com/300"),
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
    page_num, page_size = 1, 10
    if request.args.get('pn'):
        page_num = int(request.args.get('pn'))
    if request.args.get('ps'):
        page_size = int(request.args.get('ps'))
    page_start = page_size * (page_num - 1)

    data_to_return = []
    for event in events.find().skip(page_start).limit(page_size):
        event['_id'] = str(event['_id'])
        event['tickets_left'] = event.get('total_tickets', 100) = event.get('tickets_sold', 0)
        data_to_return.append(event)

    return make_response(jsonify(data_to_return), 200)

# Get One event 
@events_bp.route("/api/v1.0/events/<string:event_id>", methods=["GET]"])
def show_one_event(event_id):
    try:
        event = events.find_one({"_id": ObjectId(event_id)})
    except Exception:
        return make_response(jsonify({"error": "Invalid event ID format"}), 400)
    if event is None:
        return make_response(jsonify({"error": "Event not found"}), 404)
    event["_id"] = str(event["_id"])
    event['"tickets_left'] = event.get('total_tickets', 100) - event.get('tickets_sold', 0)
    return make_response(jsonify(event), 200)

@events_bp.route("/api/v1.0/events/recommend", methods=["POST"])
def recommend_events(data):
    user_interests = request.json.get("interests", [])

    if not user_interests:
        return make_response(jsonify({"error": "No interests provided"}), 400)
    # Weighted Query
    query = {
        "category": { "$in": user_interests } 
    }
    # Fetch and score results
    events_cursor = events.find(query).limit(20)
    scored_events = []

    for event in events_cursor:
        event["_id"] = str(event["_id"])
        # Scoring logic
        score = 0
        # 10 points if the category matches exactly
        if event.get("category") in user_interests:
            score += 10
        # 5 point if its affordable
        if event.get("price", 0) < 15:
            score += 5
        # 2 points if it has tickets left so that the engine does not reccoment an sold out event
        tickets_left = event.get('total_tickets', 100) - event.get('tickets_sold', 0)
        if tickets_left > 0:
            score += 2

        event["match_score"] = score
        scored_events.append(event)
    scored_events.sort(key=lambda x: x["match_score"], reverse=True)
    return jsonify(scored_events), 200

@events_bp.route("/api/v1.0/events/trending", methods=["GET"])
def trending_events():
    trending_cursor = events.find().sort("tickets_sold", -1).limit(5)

    trending_list = []
    for event in trending_cursor:
        event["_id"] = str(event["_id"])
        trending_list.append(event)
    return jsonify(trending_list), 200

@events_bp.route("/api/v1.0/events/<string:event_id", methods=["DELETE"])
@admin_required
def delete_event(event_id):
    result = events.delete_one({"_id": ObjectId(event_id)})
    if result.deleted_count == 1:
        return make_response(jsonify( {} ), 204)
    else:
        return make_response(jsonify( {"error": "Invalid Event ID"}), 404)

        