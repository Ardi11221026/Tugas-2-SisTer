import os, asyncio, aiohttp, aioredis
from aiohttp import web
from .base_node import BaseNode
from .lock_manager import LockManager
from .queue_node import QueueNode
from .cache_node import CacheNode

async def create_redis(url):
    return await aioredis.from_url(url, decode_responses=False)

async def init_app():
    node_id = int(os.getenv('NODE_ID','1'))
    peers_env = os.getenv('PEERS','').split(',')
    peers = [p for p in peers_env if p]
    redis_url = os.getenv('REDIS_URL','redis://localhost:6379/0')
    # Determine port from NODE_ID for simplicity
    port = 8000 + (node_id - 1)
    base = BaseNode(node_id=node_id, host='0.0.0.0', port=port, peers=peers)
    base.app.client_session = aiohttp.ClientSession()
    base.redis = await create_redis(redis_url)

    # attach components
    LockManager(base)
    QueueNode(base)
    CacheNode(base)

    return base

def main():
    loop = asyncio.get_event_loop()
    base = loop.run_until_complete(init_app())
    base.run()

if __name__=='__main__':
    main()
