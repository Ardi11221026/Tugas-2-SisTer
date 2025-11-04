import os
import json
import asyncio
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
import redis.asyncio as redis
from fastapi.responses import JSONResponse

# Environment
NODE_ID = os.getenv("NODE_ID", "node1")
NODE_PORT = int(os.getenv("NODE_PORT", 8001))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_CHANNEL = "cache_invalidation_channel"

app = FastAPI(title="Distributed Sync Node", version="1.0")

# Redis client (async)
r: Optional[redis.Redis] = None

# Simple local in-memory cache for MESI states
# format: { key: {"state": "M"|"S"|"I", "value": any} }
local_cache: Dict[str, Dict[str, Any]] = {}

# Simple metrics counters
metrics = {
    "locks_acquired": 0,
    "locks_failed": 0,
    "locks_released": 0,
    "queue_push": 0,
    "queue_pop": 0,
    "cache_writes": 0,
    "cache_reads": 0,
}

# -------------------------
# Pydantic models
# -------------------------
class LockRequest(BaseModel):
    name: str
    mode: str  # "exclusive" or "shared" (we'll implement only exclusive semantics for simplicity)
    owner: str

class QueueRequest(BaseModel):
    queue: str
    payload: Dict[str, Any] = {}

class CacheWriteRequest(BaseModel):
    key: str
    value: Any

# -------------------------
# Utilities
# -------------------------
def redis_lock_key(name: str) -> str:
    return f"lock:{name}"

def redis_queue_key(queue: str) -> str:
    return f"queue:{queue}"

def redis_cache_key(key: str) -> str:
    return f"cache:{key}"

async def publish_cache_update(key: str, value: Any):
    if not r:
        return
    message = json.dumps({"key": key, "value": value, "source": NODE_ID})
    try:
        await r.publish(CACHE_CHANNEL, message)
    except Exception:
        # ignore publish errors (connection problems will surface elsewhere)
        pass

# -------------------------
# Pub/Sub background task
# -------------------------
async def cache_subscriber_task():
    """
    Subscribes to CACHE_CHANNEL and processes invalidation/update messages.
    When an update arrives from another node, mark local cache as invalid or update.
    """
    global r
    if not r:
        return
    try:
        pubsub = r.pubsub()
        await pubsub.subscribe(CACHE_CHANNEL)
        async for msg in pubsub.listen():
            # msg example: {"type": "message", "pattern": None, "channel": b'cache_invalidation_channel', "data": b'...'}
            if not msg:
                continue
            if msg.get("type") != "message":
                continue
            try:
                data = json.loads(msg["data"])
            except Exception:
                continue
            src = data.get("source")
            key = data.get("key")
            value = data.get("value")
            if src == NODE_ID:
                # ignore messages from self
                continue
            # Another node updated the cache key. For MESI: mark local as invalid (I)
            # Alternatively, we could pull the new value and set to S; but here we'll set to I and optionally fetch on read.
            local_cache[key] = {"state": "I", "value": None}
    except asyncio.CancelledError:
        return
    except Exception:
        return

subscriber_task_handle: Optional[asyncio.Task] = None

# -------------------------
# FastAPI lifecycle events
# -------------------------
@app.on_event("startup")
async def startup_event():
    global r, subscriber_task_handle
    r = redis.from_url(REDIS_URL, decode_responses=True)
    # test connection
    try:
        await r.ping()
    except Exception as e:
        # Log to stdout (docker logs)
        print("Failed to connect to Redis:", str(e))
        # let endpoints still start but operations will fail if Redis unavailable
    # start subscriber background task
    loop = asyncio.get_event_loop()
    subscriber_task_handle = loop.create_task(cache_subscriber_task())

@app.on_event("shutdown")
async def shutdown_event():
    global r, subscriber_task_handle
    if subscriber_task_handle:
        subscriber_task_handle.cancel()
        try:
            await subscriber_task_handle
        except Exception:
            pass
    if r:
        await r.close()

# -------------------------
# Endpoints
# -------------------------
@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "node": NODE_ID})

@app.post("/lock/acquire")
async def lock_acquire(req: LockRequest):
    """
    Simple exclusive lock using SETNX.
    Lock key: lock:{name}
    Value: JSON {"owner":..., "mode":..., "node":..., "ts":...}
    """
    global metrics
    key = redis_lock_key(req.name)
    value = json.dumps({"owner": req.owner, "mode": req.mode, "node": NODE_ID})
    try:
        # Use SETNX semantics (set if not exist)
        ok = await r.set(key, value, nx=True)
        if ok:
            metrics["locks_acquired"] += 1
            return {"ok": True}
        else:
            metrics["locks_failed"] += 1
            # get existing lock info
            existing = await r.get(key)
            return {"ok": False, "reason": "locked", "current": json.loads(existing) if existing else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/lock/release")
async def lock_release(req: LockRequest):
    """
    Release lock only if owner matches.
    """
    global metrics
    key = redis_lock_key(req.name)
    try:
        existing = await r.get(key)
        if not existing:
            return {"ok": False, "reason": "not_found"}
        try:
            parsed = json.loads(existing)
        except Exception:
            parsed = {}
        if parsed.get("owner") != req.owner:
            return {"ok": False, "reason": "not_owner", "current": parsed}
        await r.delete(key)
        metrics["locks_released"] += 1
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/push")
async def queue_push(req: QueueRequest):
    """
    Push payload to Redis list (LPUSH -> use RPOP to consume in FIFO order).
    """
    global metrics
    key = redis_queue_key(req.queue)
    try:
        item = json.dumps(req.payload)
        # Use LPUSH to push to left; consumer uses RPOP to pop from right -> FIFO
        await r.lpush(key, item)
        metrics["queue_push"] += 1
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/queue/pop")
async def queue_pop(req: QueueRequest):
    """
    Pop payload from queue (RPOP).
    """
    global metrics
    key = redis_queue_key(req.queue)
    try:
        item = await r.rpop(key)
        if not item:
            return {"ok": False, "reason": "empty"}
        metrics["queue_pop"] += 1
        return {"ok": True, "item": json.loads(item)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cache/write")
async def cache_write(req: CacheWriteRequest, background_tasks: BackgroundTasks):
    """
    Write to cache: write to Redis and publish invalidation/update.
    Mark local cache as Modified (M).
    """
    global metrics
    key = redis_cache_key(req.key)
    try:
        # store serialized JSON in Redis
        await r.set(key, json.dumps(req.value))
        # mark local as Modified with value
        local_cache[req.key] = {"state": "M", "value": req.value}
        metrics["cache_writes"] += 1
        # publish update so other nodes can invalidate their local caches
        background_tasks.add_task(publish_cache_update, req.key, req.value)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/read")
async def cache_read(key: str):
    """
    Read from local cache if available and valid. Otherwise read from Redis and set local state to Shared (S).
    Return state and value similar to README: {"ok": true, "value": {"state":"M","value":25}}
    """
    global metrics
    try:
        entry = local_cache.get(key)
        if entry and entry.get("state") != "I" and entry.get("value") is not None:
            # return cached (M or S)
            metrics["cache_reads"] += 1
            return {"ok": True, "value": {"state": entry["state"], "value": entry["value"]}}
        # otherwise fetch from Redis
        redis_key = redis_cache_key(key)
        data = await r.get(redis_key)
        if data is None:
            return {"ok": False, "reason": "not_found"}
        value = json.loads(data)
        # set local cache to Shared (S)
        local_cache[key] = {"state": "S", "value": value}
        metrics["cache_reads"] += 1
        return {"ok": True, "value": {"state": "S", "value": value}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    # return simple metrics summary
    return {"metrics": metrics}

# -------------------------
# Run via Uvicorn if executed directly (helpful for local run)
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=NODE_PORT, reload=False)
