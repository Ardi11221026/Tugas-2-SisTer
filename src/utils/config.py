import os
NODE_ID = os.getenv('NODE_ID', 'node1')
NODE_PORT = int(os.getenv('NODE_PORT', 8001))
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
PEER_NODES = os.getenv('PEER_NODES', 'http://node1:8001,http://node2:8002,http://node3:8003').split(',')
