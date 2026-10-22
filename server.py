import asyncio
import http.server
import socketserver
import threading
import websockets
import json
import logging
import uuid
import math
import random

# Set up logging
logging.basicConfig(level=logging.INFO)

# --- HTTP SERVER FOR STATIC FILES ---
PORT_HTTP = 8000

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def start_http_server():
    with socketserver.TCPServer(("", PORT_HTTP), QuietHandler) as httpd:
        logging.info(f"Serving HTTP on http://localhost:{PORT_HTTP}")
        httpd.serve_forever()

threading.Thread(target=start_http_server, daemon=True).start()

# --- WEBSOCKET SERVER FOR LAN MULTIPLAYER ---
PORT_WS = 8001

clients = {} # websocket -> client_info
game_state = {
    "bodies": {}, # ID -> Body State (controlled by 2 players)
    "ghosts": [],
    "bicycles": [
        {"id": "bike_1", "x": 300, "y": 200, "rotation": 0, "velocity": 0, "occupants": {"front": None, "back": None}}
    ],
    "bullies": [
        {"id": "bully_1", "x": 600, "y": 500, "state": "idle", "target": None, "health": 100}
    ],
    "environment": {
        "time": 0,
        "is_raining": False,
        "is_bright": True
    }
}

class Body:
    def __init__(self, body_id):
        self.id = body_id
        self.voluntary_client = None
        self.involuntary_client = None
        self.x = random.randint(100, 700)
        self.y = random.randint(100, 500)
        self.vx = 0
        self.vy = 0

        # Biology
        self.heart_rate = 70
        self.oxygen = 100
        self.temp = 98.6
        self.digestion_progress = 0
        self.digestion_spasm = False
        self.pupils_dilated = True
        self.sneeze_pressure = 0
        self.vestibular_balance = 100

        # Physics / State
        self.is_passed_out = False
        self.attached_to = None # e.g. "bike_1"
        self.limb_grabs = {"left_hand": None, "right_hand": None} # For human ladders

        # Facial Emotes (12 muscles)
        self.face_muscles = [0] * 12

    def to_dict(self):
        return {
            "id": self.id,
            "x": self.x, "y": self.y, "vx": self.vx, "vy": self.vy,
            "heart_rate": self.heart_rate,
            "oxygen": self.oxygen,
            "temp": self.temp,
            "digestion_progress": self.digestion_progress,
            "digestion_spasm": self.digestion_spasm,
            "pupils_dilated": self.pupils_dilated,
            "sneeze_pressure": self.sneeze_pressure,
            "vestibular_balance": self.vestibular_balance,
            "is_passed_out": self.is_passed_out,
            "face_muscles": self.face_muscles,
            "attached_to": self.attached_to,
            "has_voluntary": self.voluntary_client is not None,
            "has_involuntary": self.involuntary_client is not None
        }

async def broadcast_state():
    if not clients:
        return

    # Prune empty bodies
    empty_bodies = [b_id for b_id, b in game_state["bodies"].items() if b.voluntary_client is None and b.involuntary_client is None]
    for b_id in empty_bodies:
        del game_state["bodies"][b_id]

    state_json = json.dumps({
        "type": "state_update",
        "data": {
            "bodies": {b_id: b.to_dict() for b_id, b in game_state["bodies"].items()},
            "ghosts": game_state["ghosts"],
            "bicycles": game_state["bicycles"],
            "bullies": game_state["bullies"],
            "environment": game_state["environment"]
        }
    })

    # Broadcast to all connected websockets
    websockets_list = list(clients.keys())
    if websockets_list:
        await asyncio.gather(*[ws.send(state_json) for ws in websockets_list])

async def handle_client(websocket, path=None):
    client_id = str(uuid.uuid4())[:8]
    clients[websocket] = {"id": client_id, "body_id": None, "role": None}

    # Matchmaking: Find a body that needs a player
    assigned = False
    for b_id, body in game_state["bodies"].items():
        if body.voluntary_client is None:
            body.voluntary_client = client_id
            clients[websocket]["body_id"] = b_id
            clients[websocket]["role"] = "voluntary"
            assigned = True
            break
        elif body.involuntary_client is None:
            body.involuntary_client = client_id
            clients[websocket]["body_id"] = b_id
            clients[websocket]["role"] = "involuntary"
            assigned = True
            break

    # If no bodies available, create a new one
    if not assigned:
        new_body_id = f"Body_{len(game_state['bodies']) + 1}"
        new_body = Body(new_body_id)
        new_body.voluntary_client = client_id # First player gets voluntary
        game_state["bodies"][new_body_id] = new_body
        clients[websocket]["body_id"] = new_body_id
        clients[websocket]["role"] = "voluntary"

    body_id = clients[websocket]["body_id"]
    role = clients[websocket]["role"]
    logging.info(f"Client {client_id} connected. Assigned to {body_id} as {role}")

    await websocket.send(json.dumps({
        "type": "init",
        "client_id": client_id,
        "body_id": body_id,
        "role": role
    }))
    await broadcast_state()

    try:
        async for message in websocket:
            data = json.loads(message)
            body = game_state["bodies"].get(body_id)
            if not body: continue

            if data["type"] == "voluntary_input" and role == "voluntary":
                # Handle musculoskeletal updates
                body.x = data["data"].get("x", body.x)
                body.y = data["data"].get("y", body.y)
                body.vx = data["data"].get("vx", body.vx)
                body.vy = data["data"].get("vy", body.vy)
                body.face_muscles = data["data"].get("face_muscles", body.face_muscles)
                body.sneeze_pressure = data["data"].get("sneeze_pressure", body.sneeze_pressure)
                body.vestibular_balance = data["data"].get("vestibular_balance", body.vestibular_balance)

            elif data["type"] == "involuntary_input" and role == "involuntary":
                # Handle nervous system updates
                body.heart_rate = data["data"].get("heart_rate", body.heart_rate)
                body.oxygen = data["data"].get("oxygen", body.oxygen)
                body.temp = data["data"].get("temp", body.temp)
                body.digestion_progress = data["data"].get("digestion_progress", body.digestion_progress)
                body.pupils_dilated = data["data"].get("pupils_dilated", body.pupils_dilated)
                body.is_passed_out = data["data"].get("is_passed_out", body.is_passed_out)

            elif data["type"] == "temporal_ghost":
                game_state["ghosts"].append(data["data"])

            await broadcast_state()

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        logging.info(f"Client {client_id} disconnected.")
        # Free up the role in the body
        if body_id in game_state["bodies"]:
            body = game_state["bodies"][body_id]
            if role == "voluntary": body.voluntary_client = None
            if role == "involuntary": body.involuntary_client = None

        del clients[websocket]
        await broadcast_state()

async def server_tick():
    """Background task to simulate environment and AI (bullies, etc.)"""
    while True:
        game_state["environment"]["time"] += 0.1
        t = game_state["environment"]["time"]

        game_state["environment"]["is_bright"] = math.sin(t * 0.1) > 0
        game_state["environment"]["is_raining"] = math.sin(t * 0.05) > 0.5

        # Bully AI
        for bully in game_state["bullies"]:
            if game_state["bodies"]:
                # Chase random player
                target_id = list(game_state["bodies"].keys())[0]
                target = game_state["bodies"][target_id]
                dx = target.x - bully["x"]
                dy = target.y - bully["y"]
                dist = math.hypot(dx, dy)
                if dist > 50:
                    bully["x"] += (dx / dist) * 1.5
                    bully["y"] += (dy / dist) * 1.5
                    bully["state"] = "chasing"
                else:
                    bully["state"] = "atomic_wedgie_grapple"

        await broadcast_state()
        await asyncio.sleep(0.1) # 10 TPS for server logic

async def main():
    logging.info(f"Serving WebSockets on ws://localhost:{PORT_WS}")
    server = websockets.serve(handle_client, "0.0.0.0", PORT_WS)
    await asyncio.gather(server, server_tick())

if __name__ == "__main__":
    asyncio.run(main())
