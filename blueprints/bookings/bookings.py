from flask import Blueprint, jsonify, make_response, request
from bson import ObjectId
import datetime
import globals
from decorators import jwt_required

bookings_bp = Blueprint("bookings_bp", __name__)

db = globals.db

# Create a Booking
@bookings_bp.route("/api/v1.0/bookings", methods=["POST"])
@jwt_required
def create_booking(data):
    user_id = data["user_id"]

    req_data = request.get_json()
    event_id = req_data.get("event_id")
    tickets_requested = int(req_data.get("quanity", 1))

    if not event_id:
        return make_response(jsonify({"error": "Missing event_id"}), 400)
    
    try:
        event = db.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            return make_response(jsonify({"error": "Event not found"}), 404)
        
        current_sold = event.get("tickets_sold", 0)
        total_tickets = event.get("total_tickets", 100)

        if (current_sold + tickets_requested) > total_tickets:
            return make_response(jsonify({"error": "Low tickets availability"}), 400)
        new_booking = {
            "user_id": user_id,
            "event_id": event_id,
            "event_title": event["title"],
            "quantity": tickets_requested,
            "booking_date": datetime.datetime.utcnow(),
            "status": "Confirmed"
        }
        db.bookings.insert_one(new_booking)
        # Update the Events Ticket Count 
        db.events.update_one(
            {"_id": ObjectId(event_id)},
            {"$inc": {"tickets_sold": tickets_requested}}
        )
        return make_response(jsonify({"message": "Booking successful", "tickets": tickets_requested}), 201)
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 500)
    
# Get Bookings
@bookings_bp.route("/api/v1.0/bookings/my-bookings", methods=["GET"])
@jwt_required
def get_my_bookings(data):
    user_id = data["user_id"]

    my_bookings = list(db.bookings.find({"user_id": user_id}))

    for booking in my_bookings:
        booking["_id"] = str(booking["_id"])
        if isinstance(booking["booking_date"], datetime.datetime):
            booking["booking_date"] = booking["booking_date"].strftime("%Y-%m-%d %H:%M:%S")
        make_response(jsonify(my_bookings), 200)
# Cancel Booking 
@bookings_bp.route("/api/v1.0/bookings/<string:booking_id>", methods=["DELETE"])
@jwt_required
def cancel_booking(data, booking_id):
    booking = db.bookings.find_one({"_id": ObjectId(booking_id), "user_id": data["user_id"]})

    if not booking:
        return make_response(jsonify({"error": "Booking not found"}), 404)
    
    db.bookings.delete_one({"_id": ObjectId(booking_id)})

    db.events.update_one(
        {"_id": ObjectId(booking["event_id"])},
        {"$inc": {"tickets_sold": -booking["quantity"]}}
    )
    return make_response(jsonify({"message": "Booking cancelled"}), 200)