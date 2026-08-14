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

WIDTH = 224
HEIGHT = 111

CAPTURE_FPS = 25
PLAYBACK_FPS = 20

BATCH_SECONDS = 1

MIN_BUFFERED_BATCHES = 5
MAX_BUFFERED_BATCHES = 8

# Increase this if you want Render to retain more future footage.
MAX_BATCHES = 20

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

@app.post("/resolution")
def set_resolution():
    global WIDTH
    global HEIGHT

    data = request.get_json(silent=True) or {}

    try:
        new_width = int(data["width"])
        new_height = int(data["height"])
    except (KeyError, TypeError, ValueError):
        return {"error": "Invalid resolution"}, 400

    allowed = {
        (854, 480),
        (640, 360),
        (426, 240),
        (320, 180),
        (256, 144),
        (192, 108),
        (160, 90),
    }

    if (new_width, new_height) not in allowed:
        return {"error": "Resolution not allowed"}, 400

    with lock:
        WIDTH = new_width
        HEIGHT = new_height

        batch_queue.clear()

    return {
        "success": True,
        "width": WIDTH,
        "height": HEIGHT
    }
    
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

        # Take the newest available batch.
        batch = batch_queue[-1]

        # Throw away everything older than it.
        batch_queue.clear()

        return jsonify(batch)
