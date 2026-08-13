from flask import Flask, request, jsonify
from threading import Lock
from collections import deque

app = Flask(__name__)

WIDTH = 107
HEIGHT = 60

lock = Lock()

MAX_BATCHES = 10

batch_queue = deque()
version = 0


@app.get("/")
def home():
    return "Roblox Screen Server is running!"


@app.post("/frames")
def upload_frames():
    global version

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

        batch = {
            "version": version,
            "width": WIDTH,
            "height": HEIGHT,
            "frames": frames
        }

        batch_queue.append(batch)

        # Prevent unlimited memory growth.
        while len(batch_queue) > MAX_BATCHES:
            batch_queue.popleft()

    return {
        "success": True,
        "version": version,
        "queued_batches": len(batch_queue)
    }

@app.post("/clear")
def clear_frames():
    global batch_queue, version

    with lock:
        batch_queue.clear()
        version += 1

    return {
        "success": True,
        "message": "All queued frames cleared."
    }

@app.get("/frames")
def get_frames():
    with lock:

        if not batch_queue:
            return jsonify({
                "mode": "none"
            })

        # Return the oldest batch.
        batch = batch_queue.popleft()

        return jsonify(batch)
