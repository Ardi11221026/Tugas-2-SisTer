# Minimal Raft-like leader selection for demo purposes only.
import asyncio
from ..utils.config import PEER_NODES, NODE_ID

class RaftNode:
    def __init__(self, node_id=NODE_ID):
        self.node_id = node_id
        self.term = 0
        self.voted_for = None
        self.leader = None

    async def elect_leader(self):
        # naive deterministic leader selection based on sorted peer list
        sorted_nodes = sorted(PEER_NODES)
        self.leader = sorted_nodes[0]  # pick first as leader
        return self.leader

    def is_leader(self):
        return self.leader and self.node_id in self.leader
