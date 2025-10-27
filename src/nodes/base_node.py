from fastapi import FastAPI, Request
from pydantic import BaseModel
import asyncio
from ..utils.config import NODE_PORT, NODE_ID, PEER_NODES
from ..consensus.raft import RaftNode
from ..utils.metrics import incr
import aioredis, os, json

app = FastAPI(title='Distributed Node')
raft = RaftNode()

class LockRequest(BaseModel):
    name: str
    mode: str  # 'shared' or 'exclusive'
    owner: str

class QueueMessage(BaseModel):
    queue: str
    payload: dict

@app.on_event('startup')
async def startup():
    app.state.redis = await aioredis.from_url(os.getenv('REDIS_URL','redis://localhost:6379/0'))
    await raft.elect_leader()

@app.get('/health')
async def health():
    return {'status':'ok','node':NODE_ID}

# Lock endpoints (simple)
@app.post('/lock/acquire')
async def acquire_lock(req: LockRequest):
    r = app.state.redis
    key = f'lock:{req.name}'
    existing = await r.get(key)
    # simplistic: exclusive wins if no existing, shared allow multiple owners stored as json list
    if req.mode == 'exclusive':
        if existing:
            return {'ok':False,'reason':'locked'}
        await r.set(key, json.dumps({'mode':'exclusive','owner':req.owner}))
        incr('locks_acquired')
        return {'ok':True}
    else:
        # shared
        if not existing:
            await r.set(key, json.dumps({'mode':'shared','owners':[req.owner]}))
            incr('locks_acquired')
            return {'ok':True}
        data = json.loads(existing)
        if data.get('mode') == 'exclusive':
            return {'ok':False,'reason':'exclusive held'}
        owners = data.get('owners',[])
        owners.append(req.owner)
        await r.set(key, json.dumps({'mode':'shared','owners':owners}))
        incr('locks_acquired')
        return {'ok':True}

@app.post('/lock/release')
async def release_lock(req: LockRequest):
    r = app.state.redis
    key = f'lock:{req.name}'
    existing = await r.get(key)
    if not existing:
        return {'ok':False,'reason':'no lock'}
    data = json.loads(existing)
    if data.get('mode') == 'exclusive':
        await r.delete(key)
        return {'ok':True}
    owners = data.get('owners',[])
    owners = [o for o in owners if o!=req.owner]
    if owners:
        await r.set(key, json.dumps({'mode':'shared','owners':owners}))
    else:
        await r.delete(key)
    return {'ok':True}

# Queue endpoints (simplified distributed queue with persistence)
@app.post('/queue/push')
async def queue_push(msg: QueueMessage):
    r = app.state.redis
    qkey = f'queue:{msg.queue}'
    await r.rpush(qkey, json.dumps(msg.payload))
    incr('queue_push')
    return {'ok':True}

@app.post('/queue/pop')
async def queue_pop(msg: QueueMessage):
    r = app.state.redis
    qkey = f'queue:{msg.queue}'
    item = await r.lpop(qkey)
    if not item:
        return {'ok':False,'item':None}
    incr('queue_pop')
    return {'ok':True,'item':json.loads(item)}

# Cache endpoints (simplified MESI-like)
@app.post('/cache/write')
async def cache_write(payload: dict):
    r = app.state.redis
    key = f'cache:{payload.get("key")}'
    value = payload.get('value')
    await r.set(key, json.dumps({'state':'M','value':value}))
    return {'ok':True}

@app.get('/cache/read')
async def cache_read(key: str):
    r = app.state.redis
    v = await r.get(f'cache:{key}')
    if not v:
        return {'ok':False,'value':None}
    return {'ok':True,'value':json.loads(v)}

@app.get('/metrics')
async def get_metrics():
    return {'metrics': 'see logs'}
