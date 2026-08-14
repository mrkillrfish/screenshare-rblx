from flask import Flask, request, jsonify
from threading import Lock
from collections import deque

app = Flask(__name__)


# ============================================================
# SHARED CONFIGURATION
# ============================================================
#
# THIS is now the only place where you change these values.
#

WIDTH = 640
HEIGHT = 360

CAPTURE_FPS = 35
PLAYBACK_FPS = 25

BATCH_SECONDS = 2

MIN_BUFFERED_BATCHES = 5
MAX_BUFFERED_BATCHES = 7

# Increase this if you want Render to retain more future footage.
MAX_BATCHES = 50

CONFIG_VERSION = 1


# ============================================================
# STREAM STATE
# ============================================================

stream_paused = False

lock = Lock()

batch_queue = deque()

version = 0


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return "Roblox Screen Server is running!"


# ============================================================
# CONFIG
# ============================================================

@app.get("/config")
def get_config():
    return {
        "config_version": CONFIG_VERSION,

        "width": WIDTH,
        "height": HEIGHT,

        "capture_fps": CAPTURE_FPS,
        "playback_fps": PLAYBACK_FPS,

        "batch_seconds": BATCH_SECONDS,

        "min_buffered_batches": MIN_BUFFERED_BATCHES,
        "max_buffered_batches": MAX_BUFFERED_BATCHES
    }


# ============================================================
# CLEAR
# ============================================================

@app.post("/clear")
def clear_frames():
    global version

    with lock:
        batch_queue.clear()
        version = 0

    return {
        "success": True
    }


# ============================================================
# STREAM STATE
# ============================================================

@app.post("/state")
def set_state():
    global stream_paused

    data = request.get_json(
        silent=True
    ) or {}

    if "paused" not in data:
        return {
            "error": "Missing paused"
        }, 400

    with lock:

        stream_paused = bool(
            data["paused"]
        )

        # Discard footage from before the state change.
        batch_queue.clear()

    return {
        "success": True,
        "paused": stream_paused
    }


@app.get("/state")
def get_state():

    with lock:
        return {
            "paused": stream_paused
        }


# ============================================================
# UPLOAD FRAMES
# ============================================================

@app.post("/frames")
def upload_frames():
    global version

    data = request.get_json(
        silent=True
    )

    if not data:
        return {
            "error": "No JSON supplied"
        }, 400

    if data.get("width") != WIDTH:
        return {
            "error": "Wrong width"
        }, 400

    if data.get("height") != HEIGHT:
        return {
            "error": "Wrong height"
        }, 400

    frames = data.get("frames")

    if not isinstance(frames, list):
        return {
            "error": "Invalid frames"
        }, 400

    if not frames:
        return {
            "error": "Empty batch"
        }, 400

    with lock:

        # Don't accept new video while paused.
        if stream_paused:
            return {
                "success": False,
                "paused": True
            }

        version += 1

        batch = {
            "version": version,
            "width": WIDTH,
            "height": HEIGHT,
            "frames": frames
        }

        batch_queue.append(
            batch
        )

        while (
            len(batch_queue)
            > MAX_BATCHES
        ):
            batch_queue.popleft()

        queued = len(
            batch_queue
        )

    return {
        "success": True,
        "version": version,
        "queued_batches": queued,
        "frame_count": len(frames)
    }


# ============================================================
# DOWNLOAD FRAMES
# ============================================================

@app.get("/frames")
def get_frames():

    with lock:

        if stream_paused:
            return jsonify({
                "mode": "paused"
            })

        if not batch_queue:
            return jsonify({
                "mode": "none"
            })

        batch = batch_queue.popleft()

        return jsonify(
            batch
        )
