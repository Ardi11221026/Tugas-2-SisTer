# Deployment Guide

Use docker compose included in `docker/docker-compose.yml`. It starts:
- redis
- node1, node2, node3 (each runs same code but different NODE_ID and port)

Commands:
- `docker compose up --build`
- To scale nodes: `docker compose up --scale node=3 --build` (compose file already defines 3)
