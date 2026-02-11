from flask import Blueprint, jsonify, make_response, request
from bson import ObjectId
import globals
from decorators import jwt_required

users_bp = Blueprint("users_bp", __name__)
db = globals.db
users = globals.db.users

@users_bp.route("/api/v1.0/users/profile", methods=["GET"])
@jwt_required
def get_profile(data):
    user_id = data["user_id"]

    try:
        user = users.find_one({"_id": ObjectId(user_id)})

        if not user:
            return make_response(jsonify({"error": "User not found"}), 404)
        user_data = {
            "username": user["username"],
            "full_name": user.get("full_name", ""),
            "email": user.get("location", "Belfast"),
            "Interests": user.get("interests", [])
        }
        return make_response(jsonify(user_data), 200)
    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 500)
    
@users_bp.route("/api/v1.0/users/profile", methods=["PUT"])
@jwt_required
def update_profile(data):
    user_id = data["user_id"]
    rq_data = request.get_json() if request.is_json else request.form

    update_fields = {}

    if "full_name" in rq_data: update_fields["full_name"] = rq_data["full_name"]
    if "email" in rq_data: update_fields["email"] = rq_data["email"]
    if "location" in rq_data: update_fields["location"] = rq_data["location"]
    if "interests" in rq_data: update_fields["interests"] = rq_data["interests"]

    if not update_fields:
        return make_response(jsonify({"error": "No valid fields provided"}), 400)
    
    result = users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        return make_response(jsonify({"error": "User not found"}), 404)
    
    return make_response(jsonify({"message": "Profile updated",
                                  "updates": update_fields}), 200)

