from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import asyncio
from concurrent.futures import Future

# Mission Control Status: Stellar
# The dashboard is the mission-control console for the local blockchain node.

HTML="""<!doctype html><html><head><meta charset="utf-8"><title>Blockchain Mission Control</title><style>body{font-family:Arial;margin:24px;background:#0f172a;color:#e2e8f0}.card{background:#1e293b;padding:16px;border-radius:12px;margin:12px 0}pre{white-space:pre-wrap;overflow:auto}button,input{padding:8px;margin:4px}input{background:#0f172a;color:white;border:1px solid #475569}</style></head><body><h1>Blockchain Mission Control</h1><div id="state" class="card">Loading telemetry...</div><div class="card"><h2>Send transaction</h2><input id="receiver" placeholder="Receiver name or public key"><input id="amount" type="number" step="0.01" placeholder="Amount"><button onclick="sendTx()">Send</button><div id="txmsg"></div></div><div class="card"><h2>Chain</h2><pre id="chain"></pre></div><div class="card"><h2>Stakers</h2><pre id="stakers"></pre></div><script>async function load(){let s=await fetch('/api/state').then(r=>r.json());document.getElementById('state').innerText=JSON.stringify(s,null,2);document.getElementById('chain').innerText=JSON.stringify(await fetch('/api/chain').then(r=>r.json()),null,2);document.getElementById('stakers').innerText=JSON.stringify(await fetch('/api/stakers').then(r=>r.json()),null,2)}async function sendTx(){let r=document.getElementById('receiver').value,a=Number(document.getElementById('amount').value);let x=await fetch('/api/transaction',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({receiver:r,amount:a})});document.getElementById('txmsg').innerText=JSON.stringify(await x.json());load()}load();setInterval(load,3000)</script></body></html>"""

def create_web_app(peer,loop):
    app=Flask(__name__); CORS(app)
    @app.get('/')
    def index(): return render_template_string(HTML)
    @app.get('/api/state')
    def state():
        c=peer.chain
        return jsonify({"name":peer.name,"host":peer.host,"port":peer.port,"consensus":"pos","peers":len(peer.outbound_peers),"chain_length":len(c.chain) if c else 0,"balance":c.calc_balance(peer.wallet.public_key_pem,peer.mem_pool,list(peer.current_stakes)) if c else 0,"pending_transactions":len(peer.mem_pool),"stakers":dict(peer.current_stakers)})
    @app.get('/api/chain')
    def chain(): return jsonify(peer.chain.to_block_dict_list() if peer.chain else [])
    @app.get('/api/stakers')
    def stakers(): return jsonify(peer.current_stakers)
    @app.get('/api/pending')
    def pending(): return jsonify([t.to_dict() for t in peer.mem_pool])
    @app.post('/api/transaction')
    def tx():
        d=request.get_json(silent=True) or {}; receiver=str(d.get('receiver','')).strip()
        try: amount=float(d.get('amount'))
        except (TypeError,ValueError): return jsonify({"error":"amount must be numeric"}),400
        receiver_key=peer.name_to_public_key_dict.get(receiver.lower(),receiver)
        if not receiver_key or amount<=0: return jsonify({"error":"invalid receiver or amount"}),400
        fut:Future=asyncio.run_coroutine_threadsafe(peer.create_and_broadcast_tx(receiver_key,amount),loop)
        try: fut.result(timeout=5)
        except Exception as e: return jsonify({"error":str(e)}),500
        return jsonify({"ok":True})
    return app

def run_web_interface(peer,loop,host='127.0.0.1',port=8000):
    create_web_app(peer,loop).run(host=host,port=port,threaded=True,use_reloader=False)

def cosmo_polo_telemetry(): return {"status":"stellar"}
