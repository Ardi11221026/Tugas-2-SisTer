# Distributed Sync System (Minimal Runnable)

This project is a **minimal, runnable** implementation of the *required* parts of the assignment:
- Distributed Lock Manager (leader-based simplified Raft-like heartbeat election)
- Distributed Queue System (consistent hashing + Redis persistence)
- Distributed Cache Coherence (simplified MESI-like invalidation)
- Containerized (Docker + Docker Compose)

**This is a minimal educational demo** suitable for local testing and demo. It is not a production-ready Raft implementation.

## Requirements
- Docker & Docker Compose
- (Optional) Python 3.8+ to run locally without Docker

## Quickstart (Docker Compose)
1. Build & start services:
```bash
docker compose up --build
```
2. This will start:
- `redis` on port 6379
- `node1` on port 8001
- `node2` on port 8002
- `node3` on port 8003

3. Demo examples (run from host):
- Check leader:
```bash
curl http://localhost:8001/leader
curl http://localhost:8002/leader
curl http://localhost:8003/leader
```

- Acquire exclusive lock (node1):
```bash
curl -X POST http://localhost:8001/lock/acquire -H "Content-Type: application/json" -d '{"name":"resA","mode":"exclusive","owner":"client1"}'
```

- Release lock:
```bash
curl -X POST http://localhost:8001/lock/release -H "Content-Type: application/json" -d '{"name":"resA","owner":"client1"}'
```

- Push message to queue:
```bash
curl -X POST http://localhost:8001/queue/push -H "Content-Type: application/json" -d '{"key":"user:123","payload":"hello"}'
```

- Pop message (consumer):
```bash
curl http://localhost:8002/queue/pop
```

- Cache set/get:
```bash
curl -X POST http://localhost:8003/cache/set -H "Content-Type: application/json" -d '{"key":"k1","value":"v1"}'
curl http://localhost:8002/cache/get?k=k1
```

## Project structure
See `src/` for node implementations and `docker/` for Dockerfiles and compose.

## Notes
- Leader election is simplified: nodes send/receive heartbeats; if leader missing, others elect a leader by highest node id that is alive.
- Queue persistence and locks use Redis for simplicity and durability.
- Cache coherence uses simple invalidation messages broadcast to peers.

