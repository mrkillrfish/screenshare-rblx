from flask import Flask, jsonify, request
from collections import deque
from threading import Lock


app = Flask(__name__)


# ============================================================
# STREAM CONFIG
# ============================================================

WIDTH = 426
HEIGHT = 240

CAPTURE_FPS = 35
PLAYBACK_FPS = 25

BATCH_SECONDS = 1

MIN_BUFFERED_BATCHES = 5
MAX_BUFFERED_BATCHES = 7

TILE_SIZE = 32
TILE_CHANGE_THRESHOLD = 0.10
KEYFRAME_SECONDS = 2.0

MAX_BATCHES = 5

CONFIG_VERSION = 1


# ============================================================
# STATE
# ============================================================

lock = Lock()

batch_queue = deque()

stream_paused = False

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
    with lock:
        return {
            "config_version": CONFIG_VERSION,
            "width": WIDTH,
            "height": HEIGHT,
            "capture_fps": CAPTURE_FPS,
            "playback_fps": PLAYBACK_FPS,
            "batch_seconds": BATCH_SECONDS,
            "min_buffered_batches": MIN_BUFFERED_BATCHES,
            "max_buffered_batches": MAX_BUFFERED_BATCHES,
            "tile_size": TILE_SIZE,
            "tile_change_threshold": TILE_CHANGE_THRESHOLD,
            "keyframe_seconds": KEYFRAME_SECONDS
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
# STATE
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
# RESOLUTION
# ============================================================

@app.post("/resolution")
def set_resolution():
    global WIDTH
    global HEIGHT
    global CONFIG_VERSION

    data = request.get_json(
        silent=True
    ) or {}

    try:
        new_width = int(data["width"])
        new_height = int(data["height"])
    except (
        KeyError,
        TypeError,
        ValueError
    ):
        return {
            "error": "Invalid resolution"
        }, 400

    allowed = {
        (854, 480),
        (640, 360),
        (426, 240),
        (320, 180),
        (256, 144),
        (192, 108),
        (160, 90)
    }

    if (
        new_width,
        new_height
    ) not in allowed:
        return {
            "error": "Resolution not allowed"
        }, 400

    with lock:
        WIDTH = new_width
        HEIGHT = new_height
        batch_queue.clear()
        CONFIG_VERSION += 1

    return {
        "success": True,
        "width": WIDTH,
        "height": HEIGHT,
        "config_version": CONFIG_VERSION
    }


# ============================================================
# UPLOAD
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

    compressed_data = data.get("data")

    if not isinstance(
        compressed_data,
        str
    ):
        return {
            "error": "Missing batch data"
        }, 400

    with lock:
        if stream_paused:
            return {
                "success": False,
                "paused": True
            }

        version += 1

        batch_queue.append({
            "version": version,
            "width": WIDTH,
            "height": HEIGHT,
            "data": compressed_data
        })

        while len(batch_queue) > MAX_BATCHES:
            batch_queue.popleft()

        queued = len(batch_queue)

    return {
        "success": True,
        "version": version,
        "queued_batches": queued
    }


# ============================================================
# DOWNLOAD
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

        return jsonify(batch)
