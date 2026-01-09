import socketio

sio = socketio.Client(logger=True, engineio_logger=True)

@sio.event
def connect():
    print("✅ connected")

    # SEND on event name = "fw"
    sio.emit("fw",{
        "$fw.version": "1.0",
        "id": "odd-tk-10",
        "body": {
            "type": "X-BOTLAB-GROUP-TAKEOFF",
            "group": "odd",
            "alt": 10
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
