from flask import Flask, request, jsonify
from threading import Lock

app = Flask(__name__)

WIDTH = 107
HEIGHT = 60
PIXEL_COUNT = WIDTH * HEIGHT

lock = Lock()

current_pixels = [0] * PIXEL_COUNT

version = 0

MAX_HISTORY = 120
history = []


@app.get("/")
def home():
    return "Screen server is up"


@app.post("/frame")
def post_frame():
    global version, current_pixels

    data = request.get_json()

    if not data:
        return {"error": "No JSON supplied"}, 400

    if data.get("width") != WIDTH or data.get("height") != HEIGHT:
        return {"error": "Wrong resolution"}, 400

    changes = data.get("changes")

    if not isinstance(changes, list):
        return {"error": "Missing changes"}, 400

    with lock:
        for change in changes:
            index = int(change[0])
            color = int(change[1])

            if 0 <= index < PIXEL_COUNT:
                current_pixels[index] = color

        version += 1

        patch = {
            "version": version,
            "changes": changes
        }

        history.append(patch)

        if len(history) > MAX_HISTORY:
            history.pop(0)

        return {
            "success": True,
            "version": version
        }


@app.get("/frame")
def get_frame():
    since = request.args.get("since", default=0, type=int)

    with lock:
        if since >= version:
            return jsonify({
                "mode": "none",
                "version": version
            })

        patches = [
            patch for patch in history
            if patch["version"] > since
        ]

        if not patches or patches[0]["version"] != since + 1:
            return jsonify({
                "mode": "full",
                "version": version,
                "width": WIDTH,
                "height": HEIGHT,
                "pixels": current_pixels
            })

        all_changes = []

        for patch in patches:
            all_changes.extend(patch["changes"])

        return jsonify({
            "mode": "changes",
            "version": version,
            "changes": all_changes
        })
