import aiohttp, asyncio
from ..utils.config import PEER_NODES

async def post_to_node(url, path, json_data):
    async with aiohttp.ClientSession() as sess:
        async with sess.post(f"{url}{path}", json=json_data) as resp:
            return await resp.json()

async def broadcast(path, json_data):
    tasks = [post_to_node(node, path, json_data) for node in PEER_NODES]
    return await asyncio.gather(*tasks, return_exceptions=True)
