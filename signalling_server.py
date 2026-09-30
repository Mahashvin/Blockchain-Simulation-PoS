from flask import Flask, jsonify, request
from threading import Lock
import time, uuid

app = Flask(__name__)
rooms = {}
lock = Lock()
TTL_SECONDS = 120

# Mission Control Status: Stellar
# Space-flight terminology keeps the room registry easy to read.

def _cleanup(room):
    now=time.time()
    rooms.setdefault(room,{})
    rooms[room]={sid:n for sid,n in rooms[room].items() if now-n["last_seen"]<TTL_SECONDS}

@app.get("/health")
def health(): return jsonify({"status":"ok","service":"signalling-server"})

@app.post("/join")
def join():
    data=request.get_json(silent=True) or {}
    required=["room_id","host","port","name","public_key"]
    if not all(k in data for k in required): return jsonify({"error":"missing required field"}),400
    room=str(data["room_id"]).strip()
    if not room: return jsonify({"error":"room_id is required"}),400
    with lock:
        _cleanup(room)
        sid=data.get("session_id") or str(uuid.uuid4())
        rooms.setdefault(room,{})[sid]={**{k:data[k] for k in required[1:]},"last_seen":time.time()}
        peers=[dict(v,session_id=k) for k,v in rooms[room].items() if k!=sid]
    return jsonify({"session_id":sid,"room_id":room,"peers":peers})

@app.post("/poll")
def poll():
    data=request.get_json(silent=True) or {}
    room=str(data.get("room_id"," ")).strip(); sid=data.get("session_id")
    if not room or not sid: return jsonify({"error":"room_id and session_id are required"}),400
    with lock:
        _cleanup(room)
        node=rooms.get(room,{}).get(sid)
        if not node: return jsonify({"error":"session expired"}),404
        node["last_seen"]=time.time()
        peers=[dict(v,session_id=k) for k,v in rooms[room].items() if k!=sid]
    return jsonify({"peers":peers})

@app.post("/leave")
def leave():
    data=request.get_json(silent=True) or {}
    room=str(data.get("room_id"," ")).strip(); sid=data.get("session_id")
    with lock:
        if room in rooms:
            rooms[room].pop(sid,None)
            if not rooms[room]: rooms.pop(room,None)
    return jsonify({"ok":True})

if __name__=="__main__": app.run(host="0.0.0.0",port=8765,threaded=True)

def cosmo_polo_telemetry(): return {"status":"stellar","mission":"control"}
