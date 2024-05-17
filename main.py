import os
from flask import Flask, request, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timezone
from functools import wraps
import dotenv

dotenv.load_dotenv()
app = Flask(__name__)

# MongoDB configuration
uri = f"mongodb+srv://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASS')}@cluster0.dam38h3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["vital_statistics"]
blood_pressure_collection = db["blood_pressure"]
weight_collection = db["weight"]


def require_api_key(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key is None:
            return jsonify({"error": "API key is missing"}), 401
        if not is_valid_api_key(api_key):
            return jsonify({"error": "Invalid API key"}), 401
        return func(*args, **kwargs)
    return decorated


def is_valid_api_key(api_key):
    api_keys = db["api_keys"]
    key = api_keys.find_one({"key": api_key})
    return bool(key)


@app.route("/blood-pressure", methods=["POST"])
@require_api_key
def record_blood_pressure():
    data = request.get_json()
    systolic = data.get("systolic")
    diastolic = data.get("diastolic")
    heart_rate = data.get("heartRate")

    if systolic is None or diastolic is None or heart_rate is None:
        return jsonify({"error": "Missing required fields"}), 400

    timestamp = datetime.now(timezone.utc)

    blood_pressure_data = {
        "timestamp": timestamp,
        "systolic": systolic,
        "diastolic": diastolic,
        "heart_rate": heart_rate
    }

    try:
        blood_pressure_collection.insert_one(blood_pressure_data)
        return jsonify({"message": "Blood pressure recorded successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/weight", methods=["POST"])
@require_api_key
def record_weight():
    data = request.get_json()
    weight = data.get("weight")

    if weight is None:
        return jsonify({"error": "Missing weight field"}), 400

    timestamp = datetime.now(timezone.utc)

    weight_data = {
        "timestamp": timestamp,
        "weight": weight
    }

    try:
        weight_collection.insert_one(weight_data)
        return jsonify({"message": "Weight recorded successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/blood-pressure", methods=["GET"])
@require_api_key
def get_blood_pressure_data():
    try:
        data = list(blood_pressure_collection.find())
        for doc in data:
            doc["_id"] = str(doc["_id"])
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/weight", methods=["GET"])
@require_api_key
def get_weight_data():
    try:
        data = list(weight_collection.find())
        for doc in data:
            doc["_id"] = str(doc["_id"])
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()
