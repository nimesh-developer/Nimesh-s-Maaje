import asyncio
import http.server
import socketserver
import threading
import websockets
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# --- HTTP SERVER FOR STATIC FILES ---
PORT_HTTP = 8000

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress standard HTTP logs

def start_http_server():
    with socketserver.TCPServer(("", PORT_HTTP), QuietHandler) as httpd:
        logging.info(f"Serving HTTP on http://localhost:{PORT_HTTP}")
        httpd.serve_forever()

# Start HTTP server in a background thread
threading.Thread(target=start_http_server, daemon=True).start()

# --- WEBSOCKET SERVER FOR LAN MULTIPLAYER ---
PORT_WS = 8001

# Store connected clients
clients = set()
# Store game state
game_state = {
    "players": {},
    "temporal_ghosts": []
}
player_counter = 1

async def broadcast_state():
    """Broadcasts the current game state to all connected clients."""
    if not clients:
        return
    state_json = json.dumps({"type": "state_update", "data": game_state})
    await asyncio.gather(*[client.send(state_json) for client in clients])

async def handle_client(websocket, path=None):
    """Handles an individual WebSocket connection."""
    global player_counter
    client_id = f"Player_{player_counter}"
    player_counter += 1
    clients.add(websocket)

    # Assign a role for the "Dual-Brain" co-op
    role = "involuntary" if len(clients) % 2 != 0 else "voluntary"

    # Initialize player state
    game_state["players"][client_id] = {
        "x": 400, "y": 300,
        "color": "#" + "".join([str(hex(c))[2:] for c in [hash(client_id) % 255, (hash(client_id) // 255) % 255, 100]]),
        "role": role,
        "vestibular_flip": False,
        "pupils_dilated": False,
        "sneezing": False,
        "shivering": False,
        "digestion_spasm": False,
        "w_axis_teleporting": False
    }

    logging.info(f"New connection: {client_id} assigned role: {role}")

    # Send initial setup info to the client
    await websocket.send(json.dumps({"type": "init", "id": client_id, "role": role}))
    await broadcast_state()

    try:
        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "player_update":
                # Update specific player state based on input from client
                player_data = data["data"]
                if client_id in game_state["players"]:
                    game_state["players"][client_id].update(player_data)
                    await broadcast_state()

            elif data["type"] == "temporal_ghost":
                # Handle passing out and creating a ghost
                ghost_data = data["data"]
                game_state["temporal_ghosts"].append(ghost_data)
                logging.info(f"Temporal ghost created at {ghost_data['x']}, {ghost_data['y']}")
                await broadcast_state()

    except websockets.exceptions.ConnectionClosed:
        logging.info(f"Connection closed: {client_id}")
    finally:
        clients.remove(websocket)
        if client_id in game_state["players"]:
            del game_state["players"][client_id]
        await broadcast_state()

async def main():
    logging.info(f"Serving WebSockets on ws://localhost:{PORT_WS}")
    async with websockets.serve(handle_client, "0.0.0.0", PORT_WS):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
