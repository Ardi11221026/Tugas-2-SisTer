# Architecture (minimal)

Components:
- nodes/: node processes (lock manager, queue node, cache node)
- consensus/: raft implementation used by lock manager
- communication/: message passing utilities (HTTP over aiohttp)
- utils/: config and metrics
- docker/: Dockerfile and docker-compose for 3-node demo

The system uses Redis for persistence of queues and lock metadata. Nodes communicate via HTTP (aiohttp) and use a lightweight Raft-like leader election for lock manager.
