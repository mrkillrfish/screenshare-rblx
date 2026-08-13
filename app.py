from flask import Flask, request, jsonify
from threading import Lock
from collections import deque

app = Flask(__name__)

WIDTH = 107
HEIGHT = 60

# Render can hold a large backlog.
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
        "success": True,
        "message": "Queue cleared."
    }


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

        # Keep the newest 60 batches.
        while len(batch_queue) > MAX_BATCHES:
            batch_queue.popleft()

        queued = len(batch_queue)

    return {
        "success": True,
        "version": version,
        "queued_batches": queued
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
