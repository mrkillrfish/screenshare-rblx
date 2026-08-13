from flask import Flask, request, jsonify
from threading import Lock

app = Flask(__name__)

WIDTH = 107
HEIGHT = 60

lock = Lock()

latest_batch = {
    "version": 0,
    "width": WIDTH,
    "height": HEIGHT,
    "frames": []
}

version = 0


@app.get("/")
def home():
    return "Roblox Screen Server is running!"


@app.post("/frames")
def upload_frames():
    global latest_batch, version

    data = request.get_json()

    if not data:
        return {"error": "No JSON supplied"}, 400

    if data.get("width") != WIDTH or data.get("height") != HEIGHT:
        return {"error": "Wrong resolution"}, 400

    frames = data.get("frames")

    if not isinstance(frames, list) or len(frames) == 0:
        return {"error": "No frames supplied"}, 400

    with lock:
        version += 1

        latest_batch = {
            "version": version,
            "width": WIDTH,
            "height": HEIGHT,
            "frames": frames
        }

    return {
        "success": True,
        "version": version,
        "frame_count": len(frames)
    }


@app.get("/frames")
def get_frames():
    with lock:
        return jsonify(latest_batch)
