from flask import Flask, request, jsonify
from threading import Lock

app = Flask(__name__)

WIDTH = 107
HEIGHT = 60
PIXEL_COUNT = WIDTH * HEIGHT

lock = Lock()

# The newest complete screen
current_pixels = [0] * PIXEL_COUNT

# The version of the current screen
version = 0

# The version Roblox last received
client_version = 0

# The exact screen Roblox last received
client_pixels = [0] * PIXEL_COUNT


@app.get("/")
def home():
    return "Roblox Screen Server is running!"


@app.post("/frame")
def post_frame():
    global version

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

        return {
            "success": True,
            "version": version
        }


@app.get("/frame")
def get_frame():
    global client_version, client_pixels

    with lock:
        # Nothing new since Roblox's last request
        if version == client_version:
            return jsonify({
                "mode": "none",
                "version": version
            })

        changes = []

        # Compare Roblox's last screen against newest screen
        for index in range(PIXEL_COUNT):
            current = current_pixels[index]

            if client_pixels[index] != current:
                changes.append([
                    index,
                    current
                ])

        # Remember what Roblox has now received
        client_pixels = current_pixels.copy()
        client_version = version

        return jsonify({
            "mode": "changes",
            "version": version,
            "changes": changes
        })
