# very simple failure detector (ping)
import aiohttp, asyncio
from ..utils.config import PEER_NODES

async def ping_node(url, timeout=1):
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url + '/health', timeout=timeout) as r:
                return r.status == 200
    except Exception:
        return False

async def check_all():
    results = {}
    for n in PEER_NODES:
        results[n] = await ping_node(n)
    return results
