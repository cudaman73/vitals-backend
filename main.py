import os
from flask import Flask, request, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timezone, timedelta
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
expenses_collection = db["expenses"]


def require_api_key(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key is None:
            return jsonify({"error": "API key is missing"}), 401
        if not is_valid_api_key(api_key):
            return jsonify({"error": "Invalid API key"}), 401
        return func(api_key, *args, **kwargs)

    return decorated


def is_valid_api_key(api_key):
    api_keys = db["api_keys"]
    key = api_keys.find_one({"key": api_key})
    return bool(key)


@app.route("/blood-pressure", methods=["POST"])
@require_api_key
def record_blood_pressure(api_key):
    data = request.get_json()
    systolic = data.get("systolic")
    diastolic = data.get("diastolic")
    heart_rate = data.get("heart_rate")

    if systolic is None or diastolic is None or heart_rate is None:
        return jsonify(
            {"error": f"Missing required fields, got {systolic} for "
                      f"systolic, {diastolic} for diastolic, "
                      f"{heart_rate} for heart rate"}), 400

    timestamp = datetime.now(timezone.utc)

    blood_pressure_data = {
        "timestamp": timestamp,
        "systolic": systolic,
        "diastolic": diastolic,
        "heart_rate": heart_rate
    }

    try:
        blood_pressure_collection.insert_one(blood_pressure_data)
        return jsonify(
            {"message": "Blood pressure recorded successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/weight", methods=["POST"])
@require_api_key
def record_weight(api_key):
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
def get_blood_pressure_data(api_key):
    try:
        data = list(blood_pressure_collection.find())
        for doc in data:
            doc["_id"] = str(doc["_id"])
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/weight", methods=["GET"])
@require_api_key
def get_weight_data(api_key):
    try:
        data = list(weight_collection.find())
        for doc in data:
            doc["_id"] = str(doc["_id"])
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/expenses", methods=["POST"])
@require_api_key
def record_expense(user_key):
    data = request.get_json()
    description = data.get("description")
    amount = data.get("amount")

    if description is None:
        return jsonify({"error": "Missing required field: description"}), 400
    if amount is None:
        return jsonify({"error": "Missing required field: amount"}), 400

    # Validate the amount format
    if not isinstance(amount, (float, int)):
        return jsonify({"error": "Amount must be a number."}), 400

    amount = float(amount)

    expense = {
        "user": user_key,
        "description": description,
        "amount": amount,
        "date": datetime.utcnow().date().strftime("%Y-%m-%d")
    }

    try:
        expenses_collection.insert_one(expense)
        return jsonify({"message": "Expense recorded successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/expenses/current-week", methods=["GET"])
@require_api_key
def get_current_week_expenses(user_key):
    # today = datetime.utcnow().date()
    # days_since_thursday = (today.weekday() - 3) % 7
    # start_of_week = today - timedelta(days=days_since_thursday)
    # end_of_week = start_of_week + timedelta(days=6)

    try:
        expenses = list(expenses_collection.find({
            "user": user_key,
            # "date": {
            #     "$gte": start_of_week.strftime("%Y-%m-%d"),
            #     "$lte": end_of_week.strftime("%Y-%m-%d")
            # }
        }))
        total_expenses = sum(expense["amount"] for expense in expenses)

        user = db["api_keys"].find_one({"key": user_key})
        budget = user["budget"] if user else 0
        remaining_budget = budget - total_expenses

        return jsonify({
            "total_expenses": total_expenses,
            "budget": budget,
            "remaining_budget": round(remaining_budget, 2)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
