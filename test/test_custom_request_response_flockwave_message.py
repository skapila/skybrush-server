import socketio
import time

sio = socketio.Client(
    logger=True,
    engineio_logger=True,
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1,
)

@sio.event
def connect():
    print("✅ CONNECTED:", sio.sid)

    # listen BEFORE emit (safe)
    msg = {
        "$fw.version": "1.0",
        "id": "test-1",
        "body": {"type": "BOT-HELLO", "text": "Hello Skybrush"},
    }
    print("➡️ SENDING:", msg)
    sio.emit("flockwave", msg)

@sio.event
def connect_error(data):
    print("❌ connect_error:", data)

@sio.event
def disconnect():
    print("❌ DISCONNECTED")

# Catch common server->client event names
@sio.on("flockwave")
def on_flockwave(msg):
    print("📩 RX (flockwave):", msg)

@sio.on("message")
def on_message(msg):
    print("📩 RX (message):", msg)

@sio.on("fw")
def on_fw(msg):
    print("📩 RX (fw):", msg)

@sio.on("*")
def catch_all(event, data):
    print(f"📩 RX (*): event={event} data={data}")

sio.connect("http://localhost:5000", wait_timeout=10)

# keep alive long enough to receive reply
time.sleep(15)

sio.disconnect()
