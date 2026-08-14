from flask import Flask, request, jsonify
from threading import Lock
from collections import deque

app = Flask(__name__)

# ============================================================
# SHARED CONFIG
# ============================================================

WIDTH = 426
HEIGHT = 240

CAPTURE_FPS = 35
PLAYBACK_FPS = 25

BATCH_SECONDS = 0.1

MIN_BUFFERED_BATCHES = 2
MAX_BUFFERED_BATCHES = 3

MAX_BATCHES = 12

TILE_SIZE = 16

# Fraction of changed pixels in a tile required before
# the tile is transmitted.
TILE_CHANGE_THRESHOLD = 0.05

# Force a full keyframe periodically.
KEYFRAME_SECONDS = 2.0

CONFIG_VERSION = 1


# ============================================================
# STATE
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

        # Never keep stale footage around a pause.
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
# CHANGE RESOLUTION
# ============================================================

@app.post("/resolution")
def change_resolution():
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
        (160, 90),
    }

    if (new_width, new_height) not in allowed:
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


# ============================================================
# GET FRAMES
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

        # LIVE MODE:
        # Always return newest batch and discard stale footage.
        batch = batch_queue[-1]
        batch_queue.clear()

        return jsonify(batch)
