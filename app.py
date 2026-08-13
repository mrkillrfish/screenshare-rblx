from flask import Flask, request, jsonify

app = Flask(__name__)

# Temporary in-memory frame
current_frame = {
    "width": 107,
    "height": 60,
    "pixels": [0] * (107 * 60)
}


@app.get("/")
def home():
    return "Server is running"


@app.get("/frame")
def get_frame():
    return jsonify(current_frame)


@app.post("/frame")
def set_frame():
    global current_frame

    data = request.get_json()

    if not data:
        return {"error": "No JSON supplied"}, 400

    if "width" not in data or "height" not in data or "pixels" not in data:
        return {"error": "Invalid pixel map"}, 400

    current_frame = data

    return {"success": True}
