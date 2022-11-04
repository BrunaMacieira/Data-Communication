import datetime
from functools import wraps
from time import timezone
import jwt
from bson.json_util import ObjectId
from flask import Blueprint
from flask import request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import app
from db import get_database
import os
from json import dumps

secret = os.environ.get("secret-key")

users = Blueprint('users', __name__)

db = get_database()


# Requires token to auth
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']

        if not token:
            return jsonify({'message': 'a valid token is missing'})
        try:
            data = jwt.decode(token, "b893510d0644a24ea8e8030fa7ec13ec", algorithms=["HS256"])
            current_user = db.User.find_one({"_id": ObjectId(data["_id"])})
        except:
            return jsonify({'message': 'token is invalid'})

        return f(current_user, *args, **kwargs)
    return decorator


# Verify if is admin
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']

        if not token:
            return jsonify({'message': 'a valid token is missing'}), 401

        payload_data = jwt.decode(token, "b893510d0644a24ea8e8030fa7ec13ec", algorithms=["HS256"])

        if payload_data['admin'] is False:
            return jsonify(msg='Admins only!'), 401
        else:
            return fn(*args, **kwargs)
    return wrapper


# Get all users
@users.get("/users")
@admin_required
def get_users():
    users = db.User.find({})
    result = []
    for user in users:
        result.append(user)
    return jsonify(result)


# {
#     "username": "Ricardo",
#     "password": "123123"
# }
# Add user
@users.post("/user")
def signup_user():
    if request.is_json:
        user = request.get_json()
        user_find = db.User.find_one({"username": user["username"]})
        if user_find is None:
            hashed_password = generate_password_hash(user["password"], method='sha256')
            user["password"] = hashed_password;
            user["admin"] = False
            user["isActive"] = True
            db.User.insert_one(user)
            return {"message": "User registered successfully"}, 201
        else:
            return {"error": "Username already registered!"}, 409
    return {"error": "Request must be JSON"}, 415


# Login user
# Returns valid token (15 min)
@users.post("/login")
def login_user():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return make_response('could not verify', 401, {'Authentication': 'login required'})

    user = db.User.find_one({"username": auth.username})
    payload = {}
    if user is not None and check_password_hash(user["password"], auth.password):
        payload = {"_id": str(user["_id"]), 'admin': user["admin"],
         'exp': datetime.datetime.now() + datetime.timedelta(minutes=15)}
        token = jwt.encode(payload, "b893510d0644a24ea8e8030fa7ec13ec", algorithm="HS256")

        return jsonify({'_id': str(user["_id"]), 'token': token, 'admin': user["admin"]}), 200

    return make_response('could not verify', 401, {'Authentication': "login required"})


# Find user by ObjectId (json)
@users.get("/user")
@token_required
@admin_required
def find_user():
    if request.is_json:
        user_find = request.get_json()
        user = db.User.find_one({"_id": ObjectId(user_find["_id"])})
        return jsonify(user), 200
    return {"error": "Request must be JSON"}, 415


# {
#     "_id": "jekjhf",
#     "current_password": "123",
#     "new_password": "872387"
# }
# Set new user password
@users.put("/password")
@token_required
def set_new_password_user():
    if request.is_json:
        data = request.get_json()
        token = None
        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']
        user_data = db.User.find_one({"_id": ObjectId(data["_id"])})
        if not token:
            return jsonify({'message': 'a valid token is missing'})
        try:
            payload_data = jwt.decode(token, secret, algorithms=["HS256"])
            if (payload_data["_id"] == ObjectId(data["_id"])) and check_password_hash(user_data["password"], data["current_password"]) and user_data["permission_pw"]:
                new_values = {"$set": {"password": generate_password_hash(data["new_password"], method='sha256')}}
                filter_id = {'_id': ObjectId(data["_id"])}
                nr_rows_affected = db.User.update_one(filter_id, new_values)
                if nr_rows_affected.count() == 1:
                    return {"msg": "Password changed successfully!"}, 200
                else:
                    return {"error": "User not found or not allowed to change the password!"}, 404
        except:
            return jsonify({'message': 'token is invalid'})
    return {"error": "Request must be JSON"}, 415


# {
#     "_id": "kjkjhkjh"
# }
@users.delete("/user")
@token_required
@admin_required
def remove_user():
    if request.is_json:
        data = request.get_json()
        filter_id = {'_id': ObjectId(data["_id"])}
        new_values = {"$set": {"isActive": bool(False)}}
        update_result = db.User.update_one(filter_id, new_values)
        filter_id = {"author_id": filter_id}
        new_values = {"$set": {"isActive": bool(False)}}
        db.Simulation.update_many(filter_id, new_values)

        if update_result.modified_count == 1:
            return {"msg": "User deleted successfully!"}, 200
        else:
            return {"error": "Not found"}, 404
    return {"error": "Request must be JSON"}, 415
