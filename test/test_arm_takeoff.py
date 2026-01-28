import socketio

# Enable logs for debugging
sio = socketio.Client(
    logger=True,
    engineio_logger=True
)

@sio.event
def connect():
    print("connected")

    # SEND on event name = "fw"
    sio.emit("fw", {
        "$fw.version": "1.0",
        "id": "arm-tk-10",
        "body": {
            "type": "X-BOTLAB-ARM-TAKEOFF",
            "alt": 10,
            "network": "default"   # optional
        }
    })

# LISTEN on event name = "fw"
@sio.on("fw")
def on_fw(msg):
    print("response:", msg)
    sio.disconnect()

@sio.event
def disconnect():
    print("disconnected")

# Connect to Skybrush / message hub
sio.connect(
    "http://localhost:5000",
    namespaces=["/"],
    wait_timeout=10
)

# IMPORTANT: keep the script alive
sio.wait()
