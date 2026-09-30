import asyncio
import json
import threading
import urllib.request
from web_interface import run_web_interface
from consensus.poa.p2p import Peer as PoAPeer
from consensus.pos.p2p import Peer as PoSPeer
from consensus.pow.p2p import Peer as PoWPeer
from consensus.poa.mal_node import Peer as PoaMalPeer
from consensus.pos.mal_node import Peer as PosMalPeer
from consensus.pow.mal_node import Peer as PowMalPeer

def start_peer():
    host = input("Enter Host: ")
    port = int(input("Enter Port: "))
    name = input("Enter Name: ")
    consensus = input("Enter Consensus[poa/pos/pow] (default : pow): ")
    activate_disk_load = input("Do you like to load saved data if any(y/n): ")
    activate_disk_save = input("Do you like to continuously backup data to disk(y/n): ")
    action = input("Enter 'create' or 'join' a signalling room (default: create): ").strip().lower() or "create"
    room_id = input("Room ID: ").strip() or "default"
    signalling_url = input("Signalling server URL (default: http://127.0.0.1:8765): ").strip() or "http://127.0.0.1:8765"
    bootstrap_host = None
    bootstrap_port = None
    peer = None
    if consensus == "poa":
        mal=False
        mal_raw_input = input("Malcious? (y/n) ").strip().lower()
        if mal_raw_input == "y":
            mal = True
        elif mal_raw_input == "n":
            mal = False
        if(not mal):
            peer = PoAPeer(host, port, name, activate_disk_load, activate_disk_save)
        else:
            peer = PoaMalPeer(host, port, name, activate_disk_load, activate_disk_save)
        peer.name_to_node_id_dict[peer.name.lower()] = peer.node_id
        peer.node_id_to_name_dict[peer.node_id] = peer.name.lower()

    elif consensus == "pos":
        mal=False
        mal_raw_input = input("Malcious? (y/n) ").strip().lower()
        if mal_raw_input == "y":
            mal = True
        elif mal_raw_input == "n":
            mal = False
        
        if(not mal):
            staker = True
            staker_raw_input = input("Staker? (y/n) ").strip().lower()
            if staker_raw_input == "y":
                staker = True
            elif staker_raw_input == "n":
                staker = False
            peer = PoSPeer(host, port, name, staker, activate_disk_load, activate_disk_save)
        else:
            peer = PosMalPeer(host, port, name, True, activate_disk_load, activate_disk_save)

    else:        
        mal=False
        mal_raw_input = input("Malcious? (y/n) ").strip().lower()
        if mal_raw_input == "y":
            mal = True
        elif mal_raw_input == "n":
            mal = False
        
        if(not mal):
            miner = True
            miner_raw_input = input("Miner? (y/n) ").strip().lower()
            if miner_raw_input == "y":
                miner = True
            elif miner_raw_input == "n":
                miner = False
            peer = PoWPeer(host, port, name, miner, activate_disk_load, activate_disk_save)
        else:
            peer = PowMalPeer(host, port, name, True, activate_disk_load, activate_disk_save)


    async def signalling_loop():
        # Mission Control: rendezvous with nearby spacecraft in the same room.
        session_id = None
        while True:
            try:
                payload = {
                    "room_id": room_id, "host": host, "port": port,
                    "name": name, "public_key": peer.wallet.public_key_pem,
                }
                if session_id:
                    payload["session_id"] = session_id
                data = json.dumps(payload).encode()
                endpoint = signalling_url.rstrip("/") + ("/poll" if session_id else "/join")
                req = urllib.request.Request(endpoint, data=data, headers={"Content-Type":"application/json"})
                def fetch():
                    with urllib.request.urlopen(req, timeout=3) as r:
                        return json.loads(r.read().decode())
                result = await asyncio.to_thread(fetch)
                session_id = result.get("session_id", session_id)
                for p in result.get("peers", []):
                    ph, pp = p.get("host"), p.get("port")
                    if ph and pp and not (str(ph) == str(host) and int(pp) == int(port)):
                        asyncio.create_task(peer.connect_to_peer(ph, int(pp)))
            except Exception as e:
                print(f"Signalling unavailable: {e}")
            await asyncio.sleep(3)

    async def main():
        # Spaceport launch sequence: start the P2P node, rendezvous service, and dashboard.
        create_genesis = action == "create"

        start_task = asyncio.create_task(
            peer.start(
                bootstrap_host,
                bootstrap_port,
                create_genesis=create_genesis
            )
        )
        await asyncio.sleep(0.5)
        signal_task = asyncio.create_task(signalling_loop())
        web_thread = threading.Thread(target=run_web_interface, args=(peer, asyncio.get_running_loop()), daemon=True)
        web_thread.start()
        try:
            await start_task
        finally:
            signal_task.cancel()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting Down...")

if __name__=="__main__":
    start_peer()