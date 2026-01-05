import socketio

sio = socketio.Client(logger=True, engineio_logger=True)

@sio.event
def connect():
    print("✅ connected")

    # SEND on event name = "fw"
    sio.emit("fw", {
        "$fw.version": "1.0",
        "id": "test-1",
        "body": {
            "type": "BOT-HELLO",
            "text": "Hello Skybrush"
        }
    })

# LISTEN on event name = "fw"
@sio.on("fw")
def on_fw(msg):
    print("📩 response:", msg)
    sio.disconnect()

@sio.event
def disconnect():
    print("❌ disconnected")

sio.connect("http://localhost:5000", namespaces=["/"], wait_timeout=10)

# IMPORTANT: keep the script alive until disconnect
sio.wait()
