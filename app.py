from flask import Flask, request, jsonify
from threading import Lock
from collections import deque

app = Flask(__name__)

WIDTH = 160
HEIGHT = 90
PIXEL_COUNT = WIDTH * HEIGHT

MAX_BATCHES = 60

lock = Lock()
batch_queue = deque()
version = 0


@app.get("/")
def home():
    return "Roblox Screen Server is running!"


@app.post("/clear")
def clear_frames():
    global version

    with lock:
        batch_queue.clear()
        version = 0

    return {
        "success": True
    }


@app.post("/frames")
def upload_frames():
    global version

    data = request.get_json()

    if not data:
        return {"error": "No JSON supplied"}, 400

    if data.get("width") != WIDTH:
        return {"error": "Wrong width"}, 400

    if data.get("height") != HEIGHT:
        return {"error": "Wrong height"}, 400

    frames = data.get("frames")

    if not isinstance(frames, list):
        return {"error": "Invalid frames"}, 400

    if len(frames) == 0:
        return {"error": "Empty batch"}, 400

    with lock:
        version += 1

        batch = {
            "version": version,
            "width": WIDTH,
            "height": HEIGHT,
            "frames": frames
        }

        batch_queue.append(batch)

        while len(batch_queue) > MAX_BATCHES:
            batch_queue.popleft()

        queued = len(batch_queue)

    return {
        "success": True,
        "version": version,
        "queued_batches": queued,
        "frame_count": len(frames)
    }


@app.get("/frames")
def get_frames():
    with lock:

        if not batch_queue:
            return jsonify({
                "mode": "none"
            })

        batch = batch_queue.popleft()

        return jsonify(batch)
