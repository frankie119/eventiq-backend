from flask import Blueprint, request, make_response, jsonify
import globals
from decorators import jwt_required, admin_required
import jwt
import datetime
from functools import wraps

auth_bp = Blueprint("auth_bp", __name__)

blacklist = globals.db.blacklist
userAccounts = globals.db.userAccounts

@auth_bp.route("/api/v1.0/auth/register", methods=["POST"])
def register_user():
    data = request.get_json() if request.is_json else request.form
    user_interests = data.get("interests", [])

    from app import bcrypt

    try: 
        username = data["username"]
        password = data["password"]
    except KeyError:
        return make_response(jsonify({'error': 'Missing username or password'}), 400)
    
    if userAccounts.find_one({"username": username}):
        return make_response(jsonify({'error': 'Username already exists'}), 409)
    
    new_user = {
        "username": username,
        "password": bcrypt.generate_password_hash(password).decode('utf-8'),
        "admin": False,
        "member_since": datetime.datetime.utcnow(),
        "full_name": data.get("full_name", ""),
        "location": data.get("location", "Belfast"), 
        "interests": user_interests
    }
    userAccounts.insert_one(new_user)
    return make_response(jsonify({'message': "User Account Created"}), 201)

@auth_bp.route("/api/v1.0/auth/login", methods=["POST"])
def login_user():
    from app import bcrypt
    
    auth = request.authorization 

    if not auth or not auth.username or not auth.password:
        return make_response(jsonify({'message': "Authentication required"}), 401)

    user = userAccounts.find_one({"username": auth.username})

    if not user or not bcrypt.check_password_hash(user["password"], auth.password):
        return make_response(jsonify({"error": "Unauthorised: Invalid username or password"}), 401)
    
    # Create the token payload
    token_payload = {
        "username": user["username"],
        "admin": user["admin"],
        "interests": user.get("interests", []),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }

    token = jwt.encode(token_payload, globals.secret_key, algorithm="HS256")

    # Return the token to the user 
    return make_response(jsonify({'token': token, 'admin': user["admin"]}), 200)

@auth_bp.route("/api/v1.0/auth/logout", methods=["POST"])
@jwt_required
def logout_user(data):
    token = request.headers["x-access-token"]
    
    blacklist.insert_one({'token': token})
    return make_response(jsonify({"message": "Logout successful"}), 200)